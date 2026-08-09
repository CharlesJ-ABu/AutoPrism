from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, Field
from sqlalchemy import desc, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.core.config import settings
from app.core.database import get_db
from app.domain.panel_schema import validate_observation_contract
from app.models.dashboards import ExtractionRun, PanelVersion
from app.models.evidence import (
    CalculationRun,
    ConversionRun,
    EvidenceArtifact,
    EvidenceFragment,
    ExtractionRunInputSet,
    MetricObservation,
    ObservationEvidenceLink,
    ObservationEvidenceSet,
    ObservationExtractionLink,
    ObservationNumericValue,
    ObservationRevision,
    SourceSnapshot,
    TrustAssessment,
    TrustState,
)
from app.services.artifact_store import LocalArtifactStore
from app.services.trust_service import TRUST_POLICY_VERSION, TrustService


router = APIRouter()


class ObservationRevisionRequest(BaseModel):
    raw_value: dict
    normalized_value: dict
    reason: str = Field(min_length=1)
    revised_by: str = Field(min_length=1, max_length=255)
    evidence_fragment_id: uuid.UUID | None = None
    evidence_fragment_ids: list[uuid.UUID] | None = Field(
        default=None,
        min_length=1,
    )
    evidence_claims: dict[str, list[uuid.UUID]] | None = None
    unit: str | None = None
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    observed_at: datetime | None = None
    period_start: datetime | None = None
    period_end: datetime | None = None
    dimensions: dict | None = None
    geographic_scope: dict | None = None
    metadata: dict = Field(default_factory=dict)


async def _serialize_observations(
    db: AsyncSession,
    observations: list[MetricObservation],
) -> list[dict]:
    if not observations:
        return []
    observation_ids = [item.id for item in observations]
    evidence_sets = (
        await db.execute(
            select(ObservationEvidenceSet).where(
                ObservationEvidenceSet.observation_id.in_(observation_ids)
            )
        )
    ).scalars().all()
    evidence_count_by_observation = {
        item.observation_id: item.citation_count for item in evidence_sets
    }
    evidence_rows = (
        await db.execute(
            select(
                ObservationEvidenceLink,
                EvidenceFragment,
                SourceSnapshot,
                EvidenceArtifact,
            )
            .join(
                EvidenceFragment,
                ObservationEvidenceLink.evidence_fragment_id
                == EvidenceFragment.id,
            )
            .join(
                SourceSnapshot,
                EvidenceFragment.snapshot_id == SourceSnapshot.id,
            )
            .join(
                EvidenceArtifact,
                SourceSnapshot.artifact_id == EvidenceArtifact.id,
            )
            .where(ObservationEvidenceLink.observation_id.in_(observation_ids))
            .order_by(
                ObservationEvidenceLink.observation_id,
                ObservationEvidenceLink.ordinal,
            )
        )
    ).all()
    evidence_by_observation: dict[uuid.UUID, list[dict]] = {
        observation_id: [] for observation_id in observation_ids
    }
    for link, fragment, snapshot, artifact in evidence_rows:
        evidence_by_observation[link.observation_id].append(
            {
                "association_id": f"{link.observation_id}:{link.ordinal}",
                "ordinal": link.ordinal,
                "role": link.role,
                "claim_key": link.claim_key,
                "field_path": link.field_path,
                "fragment": {
                    "fragment_id": str(fragment.id),
                    "locator_type": fragment.locator_type,
                    "locator": fragment.locator,
                    "text": fragment.extracted_text,
                    "text_sha256": fragment.extracted_text_sha256,
                    "snapshot_id": str(snapshot.id),
                    "source_definition_id": (
                        str(snapshot.source_definition_id)
                        if snapshot.source_definition_id
                        else None
                    ),
                    "source_key": snapshot.source_key,
                    "source_url": snapshot.canonical_url,
                    "retrieved_at": snapshot.retrieved_at,
                    "published_at": snapshot.published_at,
                    "artifact_id": str(artifact.id),
                    "artifact_sha256": artifact.sha256,
                    "artifact_byte_size": artifact.byte_size,
                    "artifact_media_type": artifact.media_type,
                },
            }
        )

    extraction_rows = (
        await db.execute(
            select(ObservationExtractionLink, ExtractionRun)
            .join(
                ExtractionRun,
                ObservationExtractionLink.extraction_run_id == ExtractionRun.id,
            )
            .where(ObservationExtractionLink.observation_id.in_(observation_ids))
        )
    ).all()
    extraction_by_observation = {
        link.observation_id: (link, run) for link, run in extraction_rows
    }
    extraction_run_ids = [run.id for _link, run in extraction_rows]
    input_sets = (
        (
            await db.execute(
                select(ExtractionRunInputSet).where(
                    ExtractionRunInputSet.extraction_run_id.in_(
                        extraction_run_ids
                    )
                )
            )
        ).scalars().all()
        if extraction_run_ids
        else []
    )
    input_set_by_run = {item.extraction_run_id: item for item in input_sets}
    revision_rows = (
        await db.execute(
            select(ObservationRevision).where(
                ObservationRevision.replacement_observation_id.in_(observation_ids)
            )
        )
    ).scalars().all()
    revision_by_replacement = {
        item.replacement_observation_id: item for item in revision_rows
    }
    calculation_rows = (
        await db.execute(
            select(CalculationRun).where(
                CalculationRun.output_observation_id.in_(observation_ids)
            )
        )
    ).scalars().all()
    calculation_by_output = {
        item.output_observation_id: item for item in calculation_rows
    }
    conversion_rows = (
        await db.execute(
            select(ConversionRun).where(
                ConversionRun.output_observation_id.in_(observation_ids)
            )
        )
    ).scalars().all()
    conversion_by_output = {
        item.output_observation_id: item for item in conversion_rows
    }
    numeric_rows = (
        await db.execute(
            select(ObservationNumericValue).where(
                ObservationNumericValue.observation_id.in_(observation_ids)
            )
        )
    ).scalars().all()
    numeric_by_observation = {item.observation_id: item for item in numeric_rows}

    # Keep the original single-evidence object during the compatibility window,
    # but never promote it into the new frozen evidence_refs array when the set
    # is absent. Missing normalized lineage remains explicit and ineligible.
    primary_rows = (
        await db.execute(
            select(
                MetricObservation.id,
                EvidenceFragment,
                SourceSnapshot,
                EvidenceArtifact,
            )
            .join(
                EvidenceFragment,
                MetricObservation.evidence_fragment_id == EvidenceFragment.id,
            )
            .join(
                SourceSnapshot,
                EvidenceFragment.snapshot_id == SourceSnapshot.id,
            )
            .join(
                EvidenceArtifact,
                SourceSnapshot.artifact_id == EvidenceArtifact.id,
            )
            .where(MetricObservation.id.in_(observation_ids))
        )
    ).all()
    compatibility_evidence = {
        observation_id: {
            "fragment_id": str(fragment.id),
            "locator_type": fragment.locator_type,
            "locator": fragment.locator,
            "text": fragment.extracted_text,
            "text_sha256": fragment.extracted_text_sha256,
            "snapshot_id": str(snapshot.id),
            "source_url": snapshot.canonical_url,
            "retrieved_at": snapshot.retrieved_at,
            "published_at": snapshot.published_at,
            "artifact_id": str(artifact.id),
            "artifact_sha256": artifact.sha256,
        }
        for observation_id, fragment, snapshot, artifact in primary_rows
    }

    payloads: list[dict] = []
    for observation in observations:
        extraction = extraction_by_observation.get(observation.id)
        revision = revision_by_replacement.get(observation.id)
        calculation = calculation_by_output.get(observation.id)
        conversion = conversion_by_output.get(observation.id)
        numeric = numeric_by_observation.get(observation.id)
        origin_count = sum(
            item is not None
            for item in (calculation, conversion, revision, extraction)
        )
        if origin_count > 1:
            origin_kind = "legacy"
            lineage_state = "incomplete"
            parent_observation_ids = []
        elif conversion is not None:
            origin_kind = "conversion"
            lineage_state = "derived"
            parent_observation_ids = [str(conversion.input_observation_id)] + (
                [str(conversion.fx_rate_observation_id)]
                if conversion.fx_rate_observation_id
                else []
            )
        elif calculation is not None:
            origin_kind = "calculation"
            lineage_state = "derived"
            parent_observation_ids = calculation.input_observation_ids
        elif revision is not None and (
            observation.supersedes_id == revision.original_observation_id
        ):
            origin_kind = "revision"
            lineage_state = "derived"
            parent_observation_ids = [str(revision.original_observation_id)]
        elif revision is not None:
            origin_kind = "legacy"
            lineage_state = "incomplete"
            parent_observation_ids = []
        elif extraction is not None:
            origin_kind = "extraction"
            lineage_state = "direct"
            parent_observation_ids = []
        elif observation.extraction_model is not None or (
            observation.trust_state is TrustState.LEGACY_UNVERIFIED
        ):
            origin_kind = "legacy"
            lineage_state = "legacy_unverified"
            parent_observation_ids = []
        else:
            origin_kind = "legacy"
            lineage_state = "incomplete"
            parent_observation_ids = []

        extraction_payload = None
        if extraction is not None and origin_count == 1:
            link, run = extraction
            input_set = input_set_by_run.get(run.id)
            run_validation = run.validation if isinstance(run.validation, dict) else {}
            extraction_payload = {
                "id": str(run.id),
                "panel_version_id": str(run.panel_version_id),
                "snapshot_id": str(run.snapshot_id),
                "provider": run.provider,
                "model": run.model,
                "prompt_version": run.prompt_version,
                "input_hash": run.input_hash,
                "validation": run.validation,
                "input_manifest": {
                    "status": (
                        "frozen_header_present"
                        if input_set is not None
                        else "legacy_unreplayable"
                    ),
                    "input_count": (
                        input_set.input_count if input_set is not None else None
                    ),
                    "frozen_count": run_validation.get("input_manifest_count"),
                    "manifest_hash": run_validation.get("input_manifest_hash"),
                },
                "output_record_ordinal": link.output_record_ordinal,
                "field_path": link.field_path,
                "match_method": link.match_method,
                "created_at": run.created_at,
            }
        evidence_refs = evidence_by_observation[observation.id]
        primary_refs = [
            item for item in evidence_refs if item["role"] == "primary"
        ]
        evidence_set_complete = bool(
            evidence_refs
            and len(evidence_refs)
            == evidence_count_by_observation.get(observation.id, -1)
            and [item["ordinal"] for item in evidence_refs]
            == list(range(len(evidence_refs)))
            and len(primary_refs) == 1
            and primary_refs[0]["ordinal"] == 0
            and primary_refs[0]["fragment"]["fragment_id"]
            == str(observation.evidence_fragment_id)
            and all(item["claim_key"] and item["field_path"] for item in evidence_refs)
        )
        payloads.append(
            {
                "id": str(observation.id),
                "panel_version_key": observation.panel_version_key,
                "schema_version": observation.schema_version,
                "metric_key": observation.metric_key,
                "raw_value": observation.raw_value,
                "normalized_value": observation.normalized_value,
                "unit": observation.unit,
                "currency": observation.currency,
                "numeric": (
                    {
                        "value": str(numeric.value),
                        "uncertainty_kind": numeric.uncertainty_kind.value,
                        "absolute_error": (
                            str(numeric.absolute_error)
                            if numeric.absolute_error is not None
                            else None
                        ),
                        "uncertainty_basis": numeric.uncertainty_basis,
                        "evidence_count": numeric.evidence_count,
                    }
                    if numeric is not None
                    else None
                ),
                "observed_at": observation.observed_at,
                "period_start": observation.period_start,
                "period_end": observation.period_end,
                "geographic_scope": observation.geographic_scope,
                "dimensions": observation.dimensions,
                "extraction_model": observation.extraction_model,
                "extraction_prompt_version": observation.extraction_prompt_version,
                "confidence": observation.confidence,
                "trust_state": observation.trust_state.value,
                "supersedes_id": (
                    str(observation.supersedes_id)
                    if observation.supersedes_id
                    else None
                ),
                "created_at": observation.created_at,
                "evidence": compatibility_evidence[observation.id],
                "lineage": {
                    "state": lineage_state,
                    "origin": {
                        "kind": origin_kind,
                        "extraction_run": extraction_payload,
                        "parent_observation_ids": parent_observation_ids,
                        "revision_id": (
                            str(revision.id)
                            if revision is not None and origin_count == 1
                            else None
                        ),
                        "calculation_run_id": (
                            str(calculation.id)
                            if calculation is not None and origin_count == 1
                            else None
                        ),
                        "conversion_run_id": (
                            str(conversion.id)
                            if conversion is not None and origin_count == 1
                            else None
                        ),
                    },
                    "evidence_refs": evidence_refs,
                    "evidence_set_complete": evidence_set_complete,
                },
            }
        )
    return payloads


@router.get("/observations")
async def list_observations(
    panel_version_key: str | None = Query(default=None),
    trusted_only: bool = Query(default=False),
    limit: int = Query(default=200, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
):
    statement = select(MetricObservation)
    if panel_version_key:
        statement = statement.where(
            MetricObservation.panel_version_key == panel_version_key
        )
    if trusted_only:
        replacement_observation = aliased(MetricObservation)
        latest_assessment_id = (
            select(TrustAssessment.id)
            .where(TrustAssessment.observation_id == MetricObservation.id)
            .order_by(
                desc(TrustAssessment.created_at),
                desc(TrustAssessment.id),
            )
            .limit(1)
            .correlate(MetricObservation)
            .scalar_subquery()
        )
        candidate_statement = (
            statement.add_columns(TrustAssessment)
            .join(
                TrustAssessment,
                TrustAssessment.id == latest_assessment_id,
            )
            .where(
                TrustAssessment.eligible.is_(True),
                TrustAssessment.policy_version == TRUST_POLICY_VERSION,
                ~select(replacement_observation.id)
                .where(
                    replacement_observation.supersedes_id
                    == MetricObservation.id
                )
                .exists(),
            )
            .order_by(
                desc(MetricObservation.created_at),
                desc(MetricObservation.id),
            )
        )
        observations: list[MetricObservation] = []
        offset = 0
        batch_size = max(100, limit)
        trust_service = TrustService(db)
        while len(observations) < limit:
            candidate_rows = (
                await db.execute(
                    candidate_statement.limit(batch_size).offset(offset)
                )
            ).all()
            if not candidate_rows:
                break
            offset += len(candidate_rows)
            for observation, assessment in candidate_rows:
                if await trust_service.is_assessment_current(assessment):
                    observations.append(observation)
                    if len(observations) == limit:
                        break
    else:
        observations = (
            await db.execute(
                statement.order_by(
                    desc(MetricObservation.created_at),
                    desc(MetricObservation.id),
                ).limit(limit)
            )
        ).scalars().all()
    return await _serialize_observations(db, list(observations))


@router.get("/observations/{observation_id}")
async def get_observation(
    observation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    observation = await db.get(MetricObservation, observation_id)
    if observation is None:
        raise HTTPException(status_code=404, detail="observation not found")
    return (await _serialize_observations(db, [observation]))[0]


@router.post("/observations/{observation_id}/revisions", status_code=201)
async def revise_observation(
    observation_id: uuid.UUID,
    payload: ObservationRevisionRequest,
    db: AsyncSession = Depends(get_db),
):
    original = await db.get(MetricObservation, observation_id)
    if original is None:
        raise HTTPException(status_code=404, detail="observation not found")
    existing = (
        await db.execute(
            select(MetricObservation).where(
                MetricObservation.supersedes_id == original.id
            ).limit(1)
        )
    ).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(
            status_code=409,
            detail=f"observation already superseded by {existing.id}",
        )
    try:
        panel_version_id = uuid.UUID(original.panel_version_key)
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=422,
            detail="observation panel version key is not replayable",
        ) from exc
    panel_version = await db.get(PanelVersion, panel_version_id)
    if panel_version is None or str(panel_version.version) != original.schema_version:
        raise HTTPException(
            status_code=422,
            detail="observation panel schema version is not replayable",
        )
    replacement_dimensions = (
        payload.dimensions if payload.dimensions is not None else original.dimensions
    )
    replacement_unit = payload.unit if payload.unit is not None else original.unit
    replacement_currency = (
        payload.currency if payload.currency is not None else original.currency
    )
    replacement_observed_at = (
        payload.observed_at
        if payload.observed_at is not None
        else original.observed_at
    )
    replacement_period_start = (
        payload.period_start
        if payload.period_start is not None
        else original.period_start
    )
    replacement_period_end = (
        payload.period_end if payload.period_end is not None else original.period_end
    )
    replacement_geographic_scope = (
        payload.geographic_scope
        if payload.geographic_scope is not None
        else original.geographic_scope
    )
    if any(
        (
            replacement_unit != original.unit,
            replacement_currency != original.currency,
            replacement_observed_at != original.observed_at,
            replacement_period_start != original.period_start,
            replacement_period_end != original.period_end,
            replacement_geographic_scope != original.geographic_scope,
            replacement_dimensions != original.dimensions,
        )
    ):
        raise HTTPException(
            status_code=422,
            detail=(
                "manual revisions cannot change unit, currency, time, geography, "
                "or dimensions without a deterministic conversion contract"
            ),
        )
    contract_issues = validate_observation_contract(
        panel_version.data_schema,
        metric_key=original.metric_key,
        raw_value=payload.raw_value,
        normalized_value=payload.normalized_value,
        unit=replacement_unit,
        dimensions=replacement_dimensions,
    )
    if contract_issues:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "revision violates the frozen observation contract",
                "issues": [
                    {"path": issue.path, "message": issue.message}
                    for issue in contract_issues
                ],
            },
        )
    value_changed = bool(
        payload.raw_value != original.raw_value
        or payload.normalized_value != original.normalized_value
    )
    if value_changed and payload.evidence_claims is None:
        raise HTTPException(
            status_code=422,
            detail="a value correction requires explicit evidence_claims",
        )
    legacy_evidence_arguments = sum(
        item is not None
        for item in (
            payload.evidence_fragment_id,
            payload.evidence_fragment_ids,
            payload.evidence_claims,
        )
    )
    if legacy_evidence_arguments > 1:
        raise HTTPException(
            status_code=422,
            detail=(
                "provide only one of evidence_fragment_id, "
                "evidence_fragment_ids, or evidence_claims"
            ),
        )
    original_links = (
        await db.execute(
            select(ObservationEvidenceLink)
            .where(ObservationEvidenceLink.observation_id == original.id)
            .order_by(ObservationEvidenceLink.ordinal)
        )
    ).scalars().all()
    expected_claim_keys = {original.metric_key, *replacement_dimensions.keys()}
    claim_links: list[tuple[uuid.UUID, str, str, str]] = []
    if payload.evidence_claims is not None:
        if set(payload.evidence_claims) != expected_claim_keys:
            raise HTTPException(
                status_code=422,
                detail=(
                    "evidence_claims must contain exactly the metric and every "
                    "dimension claim"
                ),
            )
        for claim_key in [original.metric_key, *sorted(replacement_dimensions)]:
            claim_fragment_ids = payload.evidence_claims[claim_key]
            if not claim_fragment_ids or len(claim_fragment_ids) != len(
                set(claim_fragment_ids)
            ):
                raise HTTPException(
                    status_code=422,
                    detail=f"evidence_claims.{claim_key} must be non-empty and unique",
                )
            for claim_ordinal, fragment_id in enumerate(claim_fragment_ids):
                claim_links.append(
                    (
                        fragment_id,
                        (
                            "primary"
                            if claim_key == original.metric_key
                            and claim_ordinal == 0
                            else (
                                "supporting"
                                if claim_key == original.metric_key
                                else "dimension"
                            )
                        ),
                        claim_key,
                        f"$.revision.claims.{claim_key}",
                    )
                )
    else:
        if replacement_dimensions != original.dimensions:
            raise HTTPException(
                status_code=422,
                detail="changing dimensions requires explicit evidence_claims",
            )
        explicit_metric_ids = (
            payload.evidence_fragment_ids
            if payload.evidence_fragment_ids is not None
            else (
                [payload.evidence_fragment_id]
                if payload.evidence_fragment_id is not None
                else None
            )
        )
        if explicit_metric_ids is not None:
            if len(explicit_metric_ids) != len(set(explicit_metric_ids)):
                raise HTTPException(
                    status_code=422,
                    detail="evidence_fragment_ids must be unique",
                )
            claim_links.extend(
                (
                    fragment_id,
                    "primary" if ordinal == 0 else "supporting",
                    original.metric_key,
                    f"$.revision.claims.{original.metric_key}",
                )
                for ordinal, fragment_id in enumerate(explicit_metric_ids)
            )
            claim_links.extend(
                (
                    item.evidence_fragment_id,
                    "dimension",
                    item.claim_key,
                    f"$.revision.claims.{item.claim_key}",
                )
                for item in original_links
                if item.claim_key in replacement_dimensions
            )
        elif original_links:
            claim_links = [
                (
                    item.evidence_fragment_id,
                    item.role,
                    item.claim_key,
                    f"$.revision.claims.{item.claim_key}",
                )
                for item in original_links
            ]
        elif replacement_dimensions:
            raise HTTPException(
                status_code=422,
                detail="dimension claims require frozen evidence links",
            )
        else:
            claim_links = [
                (
                    original.evidence_fragment_id,
                    "primary",
                    original.metric_key,
                    f"$.revision.claims.{original.metric_key}",
                )
            ]
    linked_claim_keys = {item[2] for item in claim_links}
    if linked_claim_keys != expected_claim_keys:
        raise HTTPException(
            status_code=422,
            detail="frozen evidence is incomplete for the replacement claims",
        )
    evidence_fragment_ids = list(dict.fromkeys(item[0] for item in claim_links))
    fragments = [
        await db.get(EvidenceFragment, evidence_fragment_id)
        for evidence_fragment_id in evidence_fragment_ids
    ]
    if any(fragment is None for fragment in fragments):
        raise HTTPException(status_code=422, detail="evidence fragment not found")
    evidence_fragment_id = claim_links[0][0]
    if (
        replacement_period_start is not None
        and replacement_period_end is not None
        and replacement_period_end < replacement_period_start
    ):
        raise HTTPException(status_code=422, detail="period_end must not precede period_start")
    replacement = MetricObservation(
        panel_version_key=original.panel_version_key,
        schema_version=original.schema_version,
        metric_key=original.metric_key,
        evidence_fragment_id=evidence_fragment_id,
        supersedes_id=original.id,
        raw_value=payload.raw_value,
        normalized_value=payload.normalized_value,
        unit=replacement_unit,
        currency=replacement_currency,
        observed_at=replacement_observed_at,
        period_start=replacement_period_start,
        period_end=replacement_period_end,
        geographic_scope=replacement_geographic_scope,
        dimensions=replacement_dimensions,
        # A manual correction is not a direct model output. Its upstream run is
        # reached through ObservationRevision -> original observation instead.
        extraction_model=None,
        extraction_prompt_version=None,
        confidence=None,
        trust_state=TrustState.UNVERIFIED,
    )
    db.add(replacement)
    await db.flush()
    db.add(
        ObservationEvidenceSet(
            observation_id=replacement.id,
            citation_count=len(claim_links),
        )
    )
    await db.flush()
    for ordinal, (fragment_id, role, claim_key, field_path) in enumerate(
        claim_links
    ):
        db.add(
            ObservationEvidenceLink(
                observation_id=replacement.id,
                ordinal=ordinal,
                evidence_fragment_id=fragment_id,
                role=role,
                claim_key=claim_key,
                field_path=field_path,
            )
        )
    revision = ObservationRevision(
        original_observation_id=original.id,
        replacement_observation_id=replacement.id,
        reason=payload.reason,
        revised_by=payload.revised_by,
        metadata_json=payload.metadata,
    )
    db.add(revision)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=409,
            detail="observation was concurrently superseded",
        ) from exc
    return {
        "revision_id": str(revision.id),
        "original_observation_id": str(original.id),
        "replacement_observation_id": str(replacement.id),
        "reason": revision.reason,
        "revised_by": revision.revised_by,
        "created_at": revision.created_at,
    }


@router.get("/revisions")
async def list_revisions(
    panel_version_key: str | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
):
    statement = (
        select(ObservationRevision, MetricObservation)
        .join(
            MetricObservation,
            ObservationRevision.original_observation_id == MetricObservation.id,
        )
    )
    if panel_version_key:
        statement = statement.where(
            MetricObservation.panel_version_key == panel_version_key
        )
    rows = (
        await db.execute(
            statement.order_by(desc(ObservationRevision.created_at)).limit(limit)
        )
    ).all()
    return [
        {
            "id": str(revision.id),
            "original_observation_id": str(revision.original_observation_id),
            "replacement_observation_id": str(revision.replacement_observation_id),
            "metric_key": original.metric_key,
            "reason": revision.reason,
            "revised_by": revision.revised_by,
            "metadata": revision.metadata_json,
            "created_at": revision.created_at,
        }
        for revision, original in rows
    ]


@router.get("/snapshots")
async def list_snapshots(
    source_definition_id: uuid.UUID | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    fragment_count = (
        select(
            EvidenceFragment.snapshot_id,
            func.count(EvidenceFragment.id).label("fragment_count"),
        )
        .group_by(EvidenceFragment.snapshot_id)
        .subquery()
    )
    statement = (
        select(SourceSnapshot, EvidenceArtifact, fragment_count.c.fragment_count)
        .join(EvidenceArtifact, SourceSnapshot.artifact_id == EvidenceArtifact.id)
        .outerjoin(fragment_count, SourceSnapshot.id == fragment_count.c.snapshot_id)
    )
    if source_definition_id:
        statement = statement.where(
            SourceSnapshot.source_definition_id == source_definition_id
        )
    rows = (
        await db.execute(
            statement.order_by(desc(SourceSnapshot.retrieved_at)).limit(limit)
        )
    ).all()
    return [
        {
            "id": str(snapshot.id),
            "source_definition_id": (
                str(snapshot.source_definition_id)
                if snapshot.source_definition_id
                else None
            ),
            "source_key": snapshot.source_key,
            "canonical_url": snapshot.canonical_url,
            "retrieved_at": snapshot.retrieved_at,
            "published_at": snapshot.published_at,
            "http_status": snapshot.http_status,
            "trust_state": snapshot.trust_state.value,
            "metadata": snapshot.source_metadata,
            "artifact": {
                "id": str(artifact.id),
                "sha256": artifact.sha256,
                "byte_size": artifact.byte_size,
                "media_type": artifact.media_type,
            },
            "fragment_count": fragment_total or 0,
        }
        for snapshot, artifact, fragment_total in rows
    ]


@router.get("/snapshots/{snapshot_id}/fragments")
async def list_fragments(
    snapshot_id: uuid.UUID,
    limit: int = Query(default=200, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
):
    if await db.get(SourceSnapshot, snapshot_id) is None:
        raise HTTPException(status_code=404, detail="snapshot not found")
    items = (
        await db.execute(
            select(EvidenceFragment)
            .where(EvidenceFragment.snapshot_id == snapshot_id)
            .order_by(EvidenceFragment.created_at)
            .limit(limit)
        )
    ).scalars()
    return [
        {
            "id": str(item.id),
            "locator_type": item.locator_type,
            "locator": item.locator,
            "text": item.extracted_text,
            "text_sha256": item.extracted_text_sha256,
        }
        for item in items
    ]


@router.get("/artifacts/{artifact_id}")
async def download_artifact(
    artifact_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    artifact = await db.get(EvidenceArtifact, artifact_id)
    if artifact is None:
        raise HTTPException(status_code=404, detail="artifact not found")
    store = LocalArtifactStore(settings.ARTIFACT_STORAGE_PATH)
    try:
        content = store.read(artifact.sha256)
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    return Response(
        content=content,
        media_type=artifact.media_type,
        headers={
            "ETag": artifact.sha256,
            "Content-Disposition": f'attachment; filename="{artifact.sha256}"',
        },
    )
