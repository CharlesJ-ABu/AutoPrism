from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, Field
from sqlalchemy import desc, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models.evidence import (
    EvidenceArtifact,
    EvidenceFragment,
    MetricObservation,
    ObservationRevision,
    SourceSnapshot,
    TrustState,
)
from app.services.artifact_store import LocalArtifactStore


router = APIRouter()


class ObservationRevisionRequest(BaseModel):
    raw_value: dict
    normalized_value: dict
    reason: str = Field(min_length=1)
    revised_by: str = Field(min_length=1, max_length=255)
    evidence_fragment_id: uuid.UUID | None = None
    unit: str | None = None
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    dimensions: dict | None = None
    geographic_scope: dict | None = None
    metadata: dict = Field(default_factory=dict)


@router.get("/observations")
async def list_observations(
    panel_version_key: str | None = Query(default=None),
    trusted_only: bool = Query(default=False),
    limit: int = Query(default=200, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
):
    statement = (
        select(
            MetricObservation,
            EvidenceFragment,
            SourceSnapshot,
            EvidenceArtifact,
        )
        .join(
            EvidenceFragment,
            MetricObservation.evidence_fragment_id == EvidenceFragment.id,
        )
        .join(SourceSnapshot, EvidenceFragment.snapshot_id == SourceSnapshot.id)
        .join(EvidenceArtifact, SourceSnapshot.artifact_id == EvidenceArtifact.id)
    )
    if panel_version_key:
        statement = statement.where(
            MetricObservation.panel_version_key == panel_version_key
        )
    if trusted_only:
        statement = statement.where(
            MetricObservation.trust_state == TrustState.VERIFIED
        )
    rows = (
        await db.execute(
            statement.order_by(desc(MetricObservation.created_at)).limit(limit)
        )
    ).all()
    return [
        {
            "id": str(observation.id),
            "panel_version_key": observation.panel_version_key,
            "schema_version": observation.schema_version,
            "metric_key": observation.metric_key,
            "raw_value": observation.raw_value,
            "normalized_value": observation.normalized_value,
            "unit": observation.unit,
            "currency": observation.currency,
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
            "evidence": {
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
            },
        }
        for observation, fragment, snapshot, artifact in rows
    ]


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
    evidence_fragment_id = payload.evidence_fragment_id or original.evidence_fragment_id
    if await db.get(EvidenceFragment, evidence_fragment_id) is None:
        raise HTTPException(status_code=422, detail="evidence fragment not found")
    replacement = MetricObservation(
        panel_version_key=original.panel_version_key,
        schema_version=original.schema_version,
        metric_key=original.metric_key,
        evidence_fragment_id=evidence_fragment_id,
        supersedes_id=original.id,
        raw_value=payload.raw_value,
        normalized_value=payload.normalized_value,
        unit=payload.unit if payload.unit is not None else original.unit,
        currency=(
            payload.currency if payload.currency is not None else original.currency
        ),
        observed_at=original.observed_at,
        period_start=original.period_start,
        period_end=original.period_end,
        geographic_scope=(
            payload.geographic_scope
            if payload.geographic_scope is not None
            else original.geographic_scope
        ),
        dimensions=(
            payload.dimensions
            if payload.dimensions is not None
            else original.dimensions
        ),
        extraction_model=original.extraction_model,
        extraction_prompt_version=original.extraction_prompt_version,
        confidence=original.confidence,
        trust_state=TrustState.UNVERIFIED,
    )
    db.add(replacement)
    await db.flush()
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
