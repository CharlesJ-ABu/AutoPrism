from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.providers import DeterministicMappingProvider, ModelConfig, create_provider
from app.core.config import settings
from app.core.database import get_db
from app.models.dashboards import PanelVersion
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
    engine = panel.model_settings.get("extraction_engine")
    if engine == "json_mapping_v1":
        provider = DeterministicMappingProvider(panel.model_settings)
    else:
        try:
            provider = create_provider(
                ModelConfig(
                    provider=payload.provider or settings.AI_PROVIDER,
                    model=payload.model or settings.AI_MODEL,
                    api_key=payload.api_key or settings.AI_API_KEY,
                    base_url=payload.base_url or settings.AI_API_BASE,
                )
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
    try:
        result = await ExtractionService(db, provider).extract(
            panel_version_id=payload.panel_version_id,
            snapshot_id=payload.snapshot_id,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {
        "run_id": str(result.run_id),
        "observation_ids": [str(item) for item in result.observation_ids],
        "issues": [
            {"path": issue.path, "message": issue.message}
            for issue in result.issues
        ],
    }
