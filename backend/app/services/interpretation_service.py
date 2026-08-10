from __future__ import annotations

import math
import re
import uuid
from decimal import Decimal, InvalidOperation
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.providers import StructuredModelProvider
from app.domain.evidence import canonical_json, sha256_bytes, sha256_json
from app.models.evidence import (
    EvidenceArtifact,
    EvidenceFragment,
    MetricObservation,
    ObservationEvidenceLink,
    SourceSnapshot,
    TrustAssessment,
)
from app.models.research import EvidenceInterpretation, EvidenceInterpretationInput
from app.services.trust_service import TrustService


INTERPRETATION_PROMPT_VERSION = "evidence-bound-interpretation-v1"
INTERPRETATION_SYSTEM_PROMPT = """You are AutoPrism's evidence-bound analyst.
Use only the frozen database inputs in the user message. Do not browse, recall
outside facts, invent missing values, fill defaults, or perform arithmetic.
Every factual interpretation must be a claim and must cite exact observation
and trust-assessment IDs supplied in the input. Keep the two ID arrays paired
in the same order. Numbers may only be copied verbatim from cited normalized
values; do not calculate new numbers. State uncertainty and limitations.
This output is model narrative, not a trust decision. Return only the requested
JSON object."""

ClaimText = Annotated[str, Field(min_length=3, max_length=3000)]


class InterpretationClaim(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    statement: ClaimText
    observation_ids: list[uuid.UUID] = Field(min_length=1, max_length=20)
    trust_assessment_ids: list[uuid.UUID] = Field(min_length=1, max_length=20)
    reasoning: str = Field(min_length=3, max_length=3000)
    limitation: str = Field(min_length=3, max_length=2000)

    @model_validator(mode="after")
    def validate_pairs(self):
        if len(self.observation_ids) != len(self.trust_assessment_ids):
            raise ValueError("claim observation and assessment IDs must be paired")
        if len(set(self.observation_ids)) != len(self.observation_ids):
            raise ValueError("claim observation IDs must not contain duplicates")
        return self


class InterpretationDocument(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    summary: str = Field(min_length=3, max_length=3000)
    claims: list[InterpretationClaim] = Field(min_length=1, max_length=30)
    limitations: list[Annotated[str, Field(min_length=3, max_length=1000)]] = Field(
        min_length=1,
        max_length=20,
    )


INTERPRETATION_OUTPUT_SCHEMA = InterpretationDocument.model_json_schema()
_NUMBER_TOKEN = re.compile(r"(?<![\w-])[+-]?(?:\d+(?:\.\d+)?|\.\d+)(?:[eE][+-]?\d+)?")


def _iso(value: Any) -> str | None:
    return value.isoformat(timespec="microseconds") if value is not None else None


def _safe_model_metadata(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    output: dict[str, Any] = {}
    response_id = value.get("id")
    if isinstance(response_id, str):
        output["response_id_sha256"] = sha256_bytes(response_id.encode("utf-8"))
    usage = value.get("usage")
    if isinstance(usage, dict):
        output["usage"] = {
            str(key)[:100]: item
            for key, item in usage.items()
            if isinstance(item, (int, float))
            and not isinstance(item, bool)
            and (not isinstance(item, float) or math.isfinite(item))
        }
    return output


def _decimal_token(value: Any) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (int, float, Decimal, str)):
        raise ValueError("eligible observation lacks a canonical numeric value")
    try:
        parsed = Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError("eligible observation lacks a canonical numeric value") from exc
    if not parsed.is_finite():
        raise ValueError("eligible observation contains a non-finite numeric value")
    return parsed


def _validate_document(
    document: InterpretationDocument,
    allowed_pairs: dict[uuid.UUID, uuid.UUID],
    numeric_values: dict[uuid.UUID, Decimal],
) -> None:
    if _NUMBER_TOKEN.search(document.summary):
        raise ValueError("interpretation summary cannot contain uncited numeric facts")
    used: set[uuid.UUID] = set()
    for claim in document.claims:
        cited_values: set[Decimal] = set()
        for observation_id, assessment_id in zip(
            claim.observation_ids,
            claim.trust_assessment_ids,
            strict=True,
        ):
            if allowed_pairs.get(observation_id) != assessment_id:
                raise ValueError("interpretation claim cited an unavailable input pair")
            used.add(observation_id)
            cited_values.add(numeric_values[observation_id])
        for field_name, text in (
            ("statement", claim.statement),
            ("reasoning", claim.reasoning),
        ):
            for token in _NUMBER_TOKEN.findall(text):
                if _decimal_token(token) not in cited_values:
                    raise ValueError(
                        f"interpretation claim {field_name} contains an uncited numeric value"
                    )
    if used != set(allowed_pairs):
        raise ValueError("interpretation output must cite every selected input")


class InterpretationService:
    def __init__(self, db: AsyncSession, provider: StructuredModelProvider):
        self.db = db
        self.provider = provider

    async def _load_inputs(
        self,
        observation_ids: list[uuid.UUID],
    ) -> tuple[list[MetricObservation], list[TrustAssessment], list[dict[str, Any]]]:
        if len(observation_ids) > 100:
            raise ValueError("interpretation accepts at most 100 observations")
        if len(set(observation_ids)) != len(observation_ids):
            raise ValueError("observation_ids must not contain duplicates")
        trust_service = TrustService(self.db)
        observations: list[MetricObservation] = []
        assessments: list[TrustAssessment] = []
        manifest_inputs: list[dict[str, Any]] = []
        for observation_id in observation_ids:
            observation = await self.db.get(MetricObservation, observation_id)
            if observation is None:
                raise LookupError(f"observation not found: {observation_id}")
            assessment = (
                await self.db.execute(
                    select(TrustAssessment)
                    .where(TrustAssessment.observation_id == observation.id)
                    .order_by(desc(TrustAssessment.created_at), desc(TrustAssessment.id))
                    .limit(1)
                )
            ).scalar_one_or_none()
            if assessment is None or not await trust_service.is_assessment_current(assessment):
                raise ValueError(
                    f"observation lacks a current eligible trust assessment: {observation.id}"
                )
            normalized = observation.normalized_value
            if not isinstance(normalized, dict) or set(normalized) != {"value"}:
                raise ValueError("eligible observation lacks a canonical normalized value")
            _decimal_token(normalized["value"])
            evidence_rows = (
                await self.db.execute(
                    select(
                        ObservationEvidenceLink,
                        EvidenceFragment,
                        SourceSnapshot,
                        EvidenceArtifact,
                    )
                    .join(
                        EvidenceFragment,
                        EvidenceFragment.id == ObservationEvidenceLink.evidence_fragment_id,
                    )
                    .join(SourceSnapshot, SourceSnapshot.id == EvidenceFragment.snapshot_id)
                    .join(EvidenceArtifact, EvidenceArtifact.id == SourceSnapshot.artifact_id)
                    .where(ObservationEvidenceLink.observation_id == observation.id)
                    .order_by(ObservationEvidenceLink.ordinal)
                )
            ).all()
            evidence = [
                {
                    "ordinal": link.ordinal,
                    "role": link.role,
                    "claim_key": link.claim_key,
                    "field_path": link.field_path,
                    "fragment_id": str(fragment.id),
                    "locator_type": fragment.locator_type,
                    "locator": fragment.locator,
                    "extracted_text": (
                        fragment.extracted_text[:4000]
                        if fragment.extracted_text is not None
                        else None
                    ),
                    "extracted_text_truncated": bool(
                        fragment.extracted_text is not None
                        and len(fragment.extracted_text) > 4000
                    ),
                    "extracted_text_sha256": fragment.extracted_text_sha256,
                    "snapshot_id": str(snapshot.id),
                    "source_key": snapshot.source_key,
                    "source_url": snapshot.canonical_url,
                    "retrieved_at": _iso(snapshot.retrieved_at),
                    "artifact_id": str(artifact.id),
                    "artifact_sha256": artifact.sha256,
                }
                for link, fragment, snapshot, artifact in evidence_rows
            ]
            if not evidence:
                raise ValueError(f"eligible observation has no evidence set: {observation.id}")
            manifest_inputs.append(
                {
                    "observation_id": str(observation.id),
                    "trust_assessment_id": str(assessment.id),
                    "metric_key": observation.metric_key,
                    "normalized_value": observation.normalized_value,
                    "unit": observation.unit,
                    "currency": observation.currency,
                    "observed_at": _iso(observation.observed_at),
                    "period_start": _iso(observation.period_start),
                    "period_end": _iso(observation.period_end),
                    "geographic_scope": observation.geographic_scope,
                    "dimensions": observation.dimensions,
                    "evidence": evidence,
                }
            )
            observations.append(observation)
            assessments.append(assessment)
        return observations, assessments, manifest_inputs

    async def create(
        self,
        *,
        title: str,
        question: str,
        observation_ids: list[uuid.UUID],
        provider_name: str,
        model_name: str,
        provider_config_hash: str,
        created_by: str,
    ) -> EvidenceInterpretation:
        observations, assessments, inputs = await self._load_inputs(observation_ids)
        manifest = {
            "contract_version": INTERPRETATION_PROMPT_VERSION,
            "question": question,
            "prompt_version": INTERPRETATION_PROMPT_VERSION,
            "system_prompt": INTERPRETATION_SYSTEM_PROMPT,
            "provider": provider_name,
            "model": model_name,
            "provider_config_hash": provider_config_hash,
            "inputs": inputs,
        }
        response = await self.provider.generate(
            system_prompt=INTERPRETATION_SYSTEM_PROMPT,
            user_prompt=(
                "Answer this interpretation question using only the frozen inputs below:\n"
                + canonical_json({"question": question, "inputs": inputs})
            ),
            output_schema=INTERPRETATION_OUTPUT_SCHEMA,
        )
        if response.provider != provider_name or response.model != model_name:
            raise ValueError("model provider identity does not match the frozen request")
        document = InterpretationDocument.model_validate(response.data)
        allowed_pairs = {
            observation.id: assessment.id
            for observation, assessment in zip(observations, assessments, strict=True)
        }
        numeric_values = {
            observation.id: _decimal_token(observation.normalized_value["value"])
            for observation in observations
        }
        _validate_document(document, allowed_pairs, numeric_values)

        # Fail closed if any peer became stale while the model request was running.
        trust_service = TrustService(self.db)
        for assessment in assessments:
            if not await trust_service.is_assessment_current(assessment):
                raise ValueError("an interpretation input became ineligible before commit")

        frozen_output = document.model_dump(mode="json")
        interpretation = EvidenceInterpretation(
            title=title,
            question=question,
            provider=provider_name,
            model=model_name,
            prompt_version=INTERPRETATION_PROMPT_VERSION,
            system_prompt_sha256=sha256_bytes(
                INTERPRETATION_SYSTEM_PROMPT.encode("utf-8")
            ),
            input_hash=sha256_json(manifest),
            input_manifest=manifest,
            output_hash=sha256_json(frozen_output),
            output=frozen_output,
            input_count=len(observations),
            model_metadata=_safe_model_metadata(response.raw_metadata),
            created_by=created_by,
        )
        self.db.add(interpretation)
        await self.db.flush()
        self.db.add_all(
            [
                EvidenceInterpretationInput(
                    interpretation_id=interpretation.id,
                    ordinal=ordinal,
                    observation_id=observation.id,
                    trust_assessment_id=assessment.id,
                )
                for ordinal, (observation, assessment) in enumerate(
                    zip(observations, assessments, strict=True)
                )
            ]
        )
        await self.db.commit()
        await self.db.refresh(interpretation)
        return interpretation
