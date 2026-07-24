from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.providers import StructuredModelProvider
from app.domain.evidence import sha256_json
from app.domain.panel_schema import SchemaIssue, validate_panel_payload
from app.models.dashboards import ExtractionRun, PanelVersion
from app.models.evidence import (
    EvidenceFragment,
    MetricObservation,
    SourceSnapshot,
    TrustState,
)


EXTRACTION_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "records": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "data": {"type": "object"},
                    "evidence": {
                        "type": "object",
                        "additionalProperties": {"type": "string"},
                    },
                },
                "required": ["data", "evidence"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["records"],
    "additionalProperties": False,
}


@dataclass(frozen=True)
class ExtractionResult:
    run_id: uuid.UUID
    observation_ids: tuple[uuid.UUID, ...]
    issues: tuple[SchemaIssue, ...]


class ExtractionService:
    def __init__(self, db: AsyncSession, provider: StructuredModelProvider):
        self.db = db
        self.provider = provider

    async def extract(
        self,
        *,
        panel_version_id: uuid.UUID,
        snapshot_id: uuid.UUID,
    ) -> ExtractionResult:
        panel = await self.db.get(PanelVersion, panel_version_id)
        snapshot = await self.db.get(SourceSnapshot, snapshot_id)
        if panel is None:
            raise LookupError("panel version not found")
        if snapshot is None:
            raise LookupError("source snapshot not found")

        fragments = (
            await self.db.execute(
                select(EvidenceFragment)
                .where(EvidenceFragment.snapshot_id == snapshot.id)
                .order_by(EvidenceFragment.created_at)
            )
        ).scalars().all()
        fragment_by_id = {str(item.id): item for item in fragments}
        context = [
            {
                "evidence_fragment_id": str(item.id),
                "locator": item.locator,
                "text": item.extracted_text,
            }
            for item in fragments
        ]
        system_prompt = (
            "Extract only facts present in the supplied evidence fragments. "
            "Never calculate, estimate, browse, or fill missing values. "
            "Every returned field must cite one supplied evidence_fragment_id."
        )
        user_prompt = (
            f"Panel contract:\n{json.dumps(panel.data_schema, ensure_ascii=False)}\n"
            f"Panel instructions:\n{panel.extraction_prompt}\n"
            f"Evidence fragments:\n{json.dumps(context, ensure_ascii=False)}"
        )
        response = await self.provider.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            output_schema=EXTRACTION_OUTPUT_SCHEMA,
        )

        issues: list[SchemaIssue] = []
        valid_records: list[tuple[dict[str, Any], dict[str, str]]] = []
        records = response.data.get("records")
        if not isinstance(records, list):
            issues.append(SchemaIssue("$.records", "records must be an array"))
            records = []
        required_fields = set(panel.data_schema.get("required", []))
        for index, record in enumerate(records):
            record_issues: list[SchemaIssue] = []
            if not isinstance(record, dict):
                issues.append(SchemaIssue(f"$.records[{index}]", "record must be object"))
                continue
            data = record.get("data")
            evidence = record.get("evidence")
            if not isinstance(data, dict) or not isinstance(evidence, dict):
                issues.append(
                    SchemaIssue(
                        f"$.records[{index}]",
                        "data and evidence must be objects",
                    )
                )
                continue
            record_issues.extend(validate_panel_payload(panel.data_schema, data))
            for field in data:
                evidence_id = evidence.get(field)
                if evidence_id not in fragment_by_id:
                    record_issues.append(
                        SchemaIssue(
                            f"$.records[{index}].evidence.{field}",
                            "field must cite a fragment from this snapshot",
                        )
                    )
            for field in required_fields:
                if field in data and field not in evidence:
                    record_issues.append(
                        SchemaIssue(
                            f"$.records[{index}].evidence.{field}",
                            "required field is missing evidence",
                        )
                    )
            issues.extend(record_issues)
            if not record_issues:
                valid_records.append((data, evidence))

        validation = {
            "valid": not issues,
            "issues": [
                {"path": issue.path, "message": issue.message} for issue in issues
            ],
            "provider_metadata": response.raw_metadata,
        }
        run = ExtractionRun(
            panel_version_id=panel.id,
            snapshot_id=snapshot.id,
            provider=response.provider,
            model=response.model,
            prompt_version=panel.extraction_prompt_version,
            input_hash=sha256_json(
                {
                    "schema": panel.data_schema,
                    "prompt": panel.extraction_prompt,
                    "fragments": context,
                }
            ),
            output=response.data,
            validation=validation,
        )
        self.db.add(run)
        await self.db.flush()

        observation_ids: list[uuid.UUID] = []
        if not issues:
            properties = panel.data_schema.get("properties", {})
            for data, evidence in valid_records:
                dimensions = {
                    key: value
                    for key, value in data.items()
                    if properties.get(key, {}).get("type")
                    in {"string", "boolean"}
                }
                for metric_key, value in data.items():
                    definition = properties.get(metric_key, {})
                    if definition.get("type") not in {"number", "integer"}:
                        continue
                    fragment = fragment_by_id[evidence[metric_key]]
                    observation = MetricObservation(
                        panel_version_key=str(panel.id),
                        schema_version=str(panel.version),
                        metric_key=metric_key,
                        evidence_fragment_id=fragment.id,
                        raw_value={"value": value},
                        normalized_value={"value": value},
                        unit=definition.get("x-unit"),
                        dimensions=dimensions,
                        geographic_scope={},
                        extraction_model=response.model,
                        extraction_prompt_version=panel.extraction_prompt_version,
                        trust_state=TrustState.UNVERIFIED,
                    )
                    self.db.add(observation)
                    await self.db.flush()
                    observation_ids.append(observation.id)

        await self.db.commit()
        return ExtractionResult(run.id, tuple(observation_ids), tuple(issues))
