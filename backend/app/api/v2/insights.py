from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.evidence import L2Insight, L2InsightInput
from app.services.insight_service import InsightService
from app.services.insight_map_service import InsightMapService


router = APIRouter()


class InsightRequest(BaseModel):
    observation_ids: list[uuid.UUID] = Field(min_length=1)
    created_by: str = Field(min_length=1, max_length=255)


async def _serialize(insight: L2Insight, db: AsyncSession) -> dict:
    inputs = (
        await db.execute(
            select(L2InsightInput)
            .where(L2InsightInput.insight_id == insight.id)
            .order_by(L2InsightInput.ordinal)
        )
    ).scalars().all()
    return {
        "id": str(insight.id),
        "title": insight.title,
        "input_hash": insight.input_hash,
        "engine_version": insight.engine_version,
        "prompt_version": insight.prompt_version,
        "output": insight.output,
        "created_by": insight.created_by,
        "created_at": insight.created_at,
        "inputs": [
            {
                "ordinal": item.ordinal,
                "observation_id": str(item.observation_id),
                "trust_assessment_id": str(item.trust_assessment_id),
            }
            for item in inputs
        ],
    }


@router.post("", status_code=201)
async def create_insight(
    payload: InsightRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        insight = await InsightService(db).create(
            payload.observation_ids,
            created_by=payload.created_by,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return await _serialize(insight, db)


@router.get("")
async def list_insights(
    limit: int = Query(default=100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    insights = (
        await db.execute(
            select(L2Insight).order_by(desc(L2Insight.created_at)).limit(limit)
        )
    ).scalars().all()
    return [await _serialize(insight, db) for insight in insights]


@router.get("/map-features")
async def list_map_features(
    panel_version_key: list[str] | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    return await InsightMapService(db).list_current_features(
        panel_version_keys=set(panel_version_key) if panel_version_key else None,
        limit=limit,
    )
