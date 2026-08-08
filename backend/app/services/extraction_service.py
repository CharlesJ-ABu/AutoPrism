from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.providers import (
    StructuredModelProvider,
    validate_deterministic_mapping,
)
from app.domain.evidence import canonical_json, sha256_bytes, sha256_json
from app.domain.panel_schema import SchemaIssue, validate_panel_payload
from app.models.dashboards import ExtractionRun, PanelVersion
from app.models.evidence import (
    EvidenceFragment,
    ExtractionRunInput,
    ExtractionRunInputSet,
    MetricObservation,
    ObservationEvidenceLink,
    ObservationEvidenceSet,
    ObservationExtractionLink,
    SourceSnapshot,
    TrustState,
)


EXTRACTION_CONTRACT_VERSION = "evidence-extraction-v3"
EXTRACTION_SYSTEM_PROMPT = (
    "Extract only facts present in the supplied evidence fragments. "
    "Never calculate, estimate, browse, or fill missing values. "
    "Every returned field must cite one or more supplied "
    "evidence_fragment_id values. Use an array when multiple fragments "
    "support the same field."
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
                        "additionalProperties": {
                            "oneOf": [
                                {"type": "string"},
                                {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "minItems": 1,
                                    "uniqueItems": True,
                                },
                            ]
                        },
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


def build_extraction_input_payload(
    *,
    panel: PanelVersion,
    snapshot_id: uuid.UUID,
    fragments: list[EvidenceFragment],
    provider: str,
    model: str,
) -> dict[str, Any]:
    """Build the canonical, replayable extraction request contract."""

    return {
        "contract_version": EXTRACTION_CONTRACT_VERSION,
        "panel_version_id": str(panel.id),
        "snapshot_id": str(snapshot_id),
        "system_prompt": EXTRACTION_SYSTEM_PROMPT,
        "output_schema": EXTRACTION_OUTPUT_SCHEMA,
        "panel_schema": panel.data_schema,
        "panel_extraction_prompt": panel.extraction_prompt,
        "panel_prompt_version": panel.extraction_prompt_version,
        "panel_model_settings": panel.model_settings,
        "provider": provider,
        "model": model,
        "fragments": [
            {
                "evidence_fragment_id": str(item.id),
                "locator_type": item.locator_type,
                "locator": item.locator,
                "extracted_text_sha256": item.extracted_text_sha256,
            }
            for item in fragments
        ],
    }


def build_extraction_manifest_entry(
    *,
    ordinal: int,
    snapshot_id: uuid.UUID,
    fragment: EvidenceFragment,
) -> dict[str, Any]:
    return {
        "ordinal": ordinal,
        "snapshot_id": str(snapshot_id),
        "evidence_fragment_id": str(fragment.id),
        "locator_type": fragment.locator_type,
        "locator": fragment.locator,
        "extracted_text_sha256": fragment.extracted_text_sha256,
    }


def build_extraction_user_prompt(
    *,
    panel: PanelVersion,
    fragments: list[EvidenceFragment],
) -> str:
    context = [
        {
            "evidence_fragment_id": str(item.id),
            "locator": item.locator,
            "text": item.extracted_text,
        }
        for item in fragments
    ]
    return (
        f"Panel contract:\n{json.dumps(panel.data_schema, ensure_ascii=False)}\n"
        f"Panel instructions:\n{panel.extraction_prompt}\n"
        f"Evidence fragments:\n{json.dumps(context, ensure_ascii=False)}"
    )


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
        if not isinstance(panel.data_schema, dict):
            raise ValueError("panel data_schema must be an object")
        if not isinstance(panel.model_settings, dict):
            raise ValueError("panel model_settings must be an object")
        if snapshot.trust_state in {
            TrustState.REJECTED,
            TrustState.LEGACY_UNVERIFIED,
        }:
            raise ValueError("rejected or legacy snapshot cannot be extracted")
        if panel.model_settings.get("extraction_engine") == "json_mapping_v1":
            validate_deterministic_mapping(panel.model_settings)

        fragments = (
            await self.db.execute(
                select(EvidenceFragment)
                .where(EvidenceFragment.snapshot_id == snapshot.id)
                .order_by(EvidenceFragment.created_at, EvidenceFragment.id)
            )
        ).scalars().all()
        if any(
            item.extracted_text is None
            or item.extracted_text_sha256 is None
            or sha256_bytes(item.extracted_text.encode("utf-8"))
            != item.extracted_text_sha256
            for item in fragments
        ):
            raise ValueError("every extraction input fragment must have a valid text hash")
        if not fragments:
            raise ValueError("extraction requires at least one evidence fragment")
        manifest_entries = [
            build_extraction_manifest_entry(
                ordinal=ordinal,
                snapshot_id=snapshot.id,
                fragment=fragment,
            )
            for ordinal, fragment in enumerate(fragments)
        ]
        fragment_by_id = {str(item.id): item for item in fragments}
        user_prompt = build_extraction_user_prompt(
            panel=panel,
            fragments=list(fragments),
        )
        response = await self.provider.generate(
            system_prompt=EXTRACTION_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            output_schema=EXTRACTION_OUTPUT_SCHEMA,
        )
        if not isinstance(response.data, dict):
            raise ValueError("structured extraction response must be an object")
        if not isinstance(response.raw_metadata, dict):
            raise ValueError("structured extraction metadata must be an object")
        try:
            canonical_json(response.data)
            canonical_json(response.raw_metadata)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                "structured extraction response must contain strict finite JSON"
            ) from exc

        issues: list[SchemaIssue] = []
        valid_records: list[tuple[int, dict[str, Any], dict[str, list[str]]]] = []
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
            normalized_evidence: dict[str, list[str]] = {}
            for field in data:
                citation = evidence.get(field)
                if isinstance(citation, str):
                    evidence_ids = [citation]
                elif (
                    isinstance(citation, list)
                    and citation
                    and all(isinstance(item, str) for item in citation)
                    and len(citation) == len(set(citation))
                ):
                    evidence_ids = citation
                else:
                    record_issues.append(
                        SchemaIssue(
                            f"$.records[{index}].evidence.{field}",
                            "field must cite one or more unique fragment ids",
                        )
                    )
                    continue
                missing_ids = [
                    evidence_id
                    for evidence_id in evidence_ids
                    if evidence_id not in fragment_by_id
                ]
                if missing_ids:
                    record_issues.append(
                        SchemaIssue(
                            f"$.records[{index}].evidence.{field}",
                            "every field citation must reference this snapshot",
                        )
                    )
                    continue
                normalized_evidence[field] = evidence_ids
            for field in evidence:
                if field not in data:
                    record_issues.append(
                        SchemaIssue(
                            f"$.records[{index}].evidence.{field}",
                            "evidence cannot cite a field absent from data",
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
                valid_records.append((index, data, normalized_evidence))

        validation = {
            "valid": not issues,
            "extraction_contract_version": EXTRACTION_CONTRACT_VERSION,
            "input_manifest_count": len(manifest_entries),
            "input_manifest_hash": sha256_json(manifest_entries),
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
                build_extraction_input_payload(
                    panel=panel,
                    snapshot_id=snapshot.id,
                    fragments=list(fragments),
                    provider=response.provider,
                    model=response.model,
                )
            ),
            output=response.data,
            validation=validation,
        )
        self.db.add(run)
        await self.db.flush()
        self.db.add(
            ExtractionRunInputSet(
                extraction_run_id=run.id,
                input_count=len(fragments),
            )
        )
        await self.db.flush()
        for ordinal, (fragment, manifest_entry) in enumerate(
            zip(fragments, manifest_entries, strict=True)
        ):
            self.db.add(
                ExtractionRunInput(
                    extraction_run_id=run.id,
                    ordinal=ordinal,
                    evidence_fragment_id=fragment.id,
                    extracted_text_sha256=fragment.extracted_text_sha256,
                    manifest_entry_hash=sha256_json(manifest_entry),
                )
            )
        await self.db.flush()

        observation_ids: list[uuid.UUID] = []
        if not issues:
            properties = panel.data_schema.get("properties", {})
            for record_index, data, evidence in valid_records:
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
                    evidence_ids = evidence[metric_key]
                    fragment = fragment_by_id[evidence_ids[0]]
                    field_path = (
                        f"$.records[{record_index}].data.{metric_key}"
                    )
                    claim_citations = [
                        (metric_key, evidence_id, field_path)
                        for evidence_id in evidence_ids
                    ]
                    for dimension_key in sorted(dimensions):
                        dimension_path = (
                            f"$.records[{record_index}].data.{dimension_key}"
                        )
                        claim_citations.extend(
                            (
                                dimension_key,
                                dimension_evidence_id,
                                dimension_path,
                            )
                            for dimension_evidence_id in evidence[dimension_key]
                        )
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
                    self.db.add(
                        ObservationEvidenceSet(
                            observation_id=observation.id,
                            citation_count=len(claim_citations),
                        )
                    )
                    await self.db.flush()
                    for ordinal, (
                        claim_key,
                        evidence_id,
                        claim_field_path,
                    ) in enumerate(claim_citations):
                        self.db.add(
                            ObservationEvidenceLink(
                                observation_id=observation.id,
                                ordinal=ordinal,
                                evidence_fragment_id=fragment_by_id[evidence_id].id,
                                role=(
                                    "primary"
                                    if ordinal == 0
                                    else (
                                        "supporting"
                                        if claim_key == metric_key
                                        else "dimension"
                                    )
                                ),
                                claim_key=claim_key,
                                field_path=claim_field_path,
                            )
                        )
                    self.db.add(
                        ObservationExtractionLink(
                            observation_id=observation.id,
                            extraction_run_id=run.id,
                            output_record_ordinal=record_index,
                            field_path=field_path,
                            match_method="direct_write",
                        )
                    )
                    observation_ids.append(observation.id)

        await self.db.commit()
        return ExtractionResult(run.id, tuple(observation_ids), tuple(issues))
