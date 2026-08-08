from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.providers import DeterministicMappingProvider, ModelConfig, create_provider
from app.core.config import settings
from app.core.database import get_db
from app.models.dashboards import ExtractionRun, PanelVersion
from app.models.evidence import (
    EvidenceArtifact,
    EvidenceFragment,
    ExtractionRunInput,
    ExtractionRunInputSet,
    SourceSnapshot,
)
from app.services.extraction_service import ExtractionService


router = APIRouter()


class ExtractionRequest(BaseModel):
    panel_version_id: uuid.UUID
    snapshot_id: uuid.UUID
    provider: str | None = None
    model: str | None = None
    base_url: str | None = None
    api_key: str | None = None


@router.post("", status_code=201)
async def extract(payload: ExtractionRequest, db: AsyncSession = Depends(get_db)):
    panel = await db.get(PanelVersion, payload.panel_version_id)
    if panel is None:
        raise HTTPException(status_code=404, detail="panel version not found")
    try:
        if not isinstance(panel.model_settings, dict):
            raise ValueError("panel model_settings must be an object")
        engine = panel.model_settings.get("extraction_engine")
        if engine == "json_mapping_v1":
            provider = DeterministicMappingProvider(panel.model_settings)
        else:
            provider = create_provider(
                ModelConfig(
                    provider=payload.provider or settings.AI_PROVIDER,
                    model=payload.model or settings.AI_MODEL,
                    api_key=payload.api_key or settings.AI_API_KEY,
                    base_url=payload.base_url or settings.AI_API_BASE,
                )
            )
        result = await ExtractionService(db, provider).extract(
            panel_version_id=payload.panel_version_id,
            snapshot_id=payload.snapshot_id,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {
        "run_id": str(result.run_id),
        "observation_ids": [str(item) for item in result.observation_ids],
        "issues": [
            {"path": issue.path, "message": issue.message}
            for issue in result.issues
        ],
    }


@router.get("/{run_id}/inputs")
async def get_extraction_inputs(
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    run = await db.get(ExtractionRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="extraction run not found")
    input_set = await db.get(ExtractionRunInputSet, run.id)
    validation = run.validation if isinstance(run.validation, dict) else {}
    rows = (
        await db.execute(
            select(
                ExtractionRunInput,
                EvidenceFragment,
                SourceSnapshot,
                EvidenceArtifact,
            )
            .join(
                EvidenceFragment,
                ExtractionRunInput.evidence_fragment_id == EvidenceFragment.id,
            )
            .join(
                SourceSnapshot,
                EvidenceFragment.snapshot_id == SourceSnapshot.id,
            )
            .join(
                EvidenceArtifact,
                SourceSnapshot.artifact_id == EvidenceArtifact.id,
            )
            .where(ExtractionRunInput.extraction_run_id == run.id)
            .order_by(ExtractionRunInput.ordinal)
        )
    ).all()
    return {
        "extraction_run_id": str(run.id),
        "status": (
            "frozen_manifest_present"
            if input_set is not None
            else "legacy_unreplayable"
        ),
        "input_count": input_set.input_count if input_set is not None else None,
        "frozen_count": validation.get("input_manifest_count"),
        "manifest_hash": validation.get("input_manifest_hash"),
        "inputs": [
            {
                "ordinal": item.ordinal,
                "evidence_fragment_id": str(fragment.id),
                "snapshot_id": str(snapshot.id),
                "source_key": snapshot.source_key,
                "source_url": snapshot.canonical_url,
                "retrieved_at": snapshot.retrieved_at,
                "locator_type": fragment.locator_type,
                "locator": fragment.locator,
                "extracted_text": fragment.extracted_text,
                "extracted_text_sha256": item.extracted_text_sha256,
                "manifest_entry_hash": item.manifest_entry_hash,
                "artifact_id": str(artifact.id),
                "artifact_sha256": artifact.sha256,
                "artifact_byte_size": artifact.byte_size,
                "artifact_media_type": artifact.media_type,
            }
            for item, fragment, snapshot, artifact in rows
        ],
    }
