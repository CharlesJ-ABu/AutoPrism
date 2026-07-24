from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.evidence import ReviewCase, ReviewDecision, ReviewState
from app.services.verification_service import VerificationService


router = APIRouter()


class ValidationRequest(BaseModel):
    observation_ids: list[uuid.UUID] = Field(min_length=1)
    absolute_tolerance: str = "0"
    relative_tolerance: str = "0"


class CalculationRequest(BaseModel):
    operation: str
    input_observation_ids: list[uuid.UUID] = Field(min_length=1)
    output_metric_key: str
    output_unit: str | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)


class DecisionRequest(BaseModel):
    outcome: ReviewState
    decision: dict[str, Any]
    decided_by: str = Field(min_length=1, max_length=255)
    supersedes_id: uuid.UUID | None = None


@router.post("/validate")
async def validate_observations(
    payload: ValidationRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        run, review = await VerificationService(db).validate_observations(
            payload.observation_ids,
            absolute_tolerance=payload.absolute_tolerance,
            relative_tolerance=payload.relative_tolerance,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return {
        "validation_run_id": str(run.id),
        "state": run.state.value,
        "result": run.result,
        "review_case_id": str(review.id) if review else None,
    }


@router.post("/calculate")
async def calculate(
    payload: CalculationRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        observation, run = await VerificationService(db).calculate(
            operation=payload.operation,
            input_observation_ids=payload.input_observation_ids,
            output_metric_key=payload.output_metric_key,
            output_unit=payload.output_unit,
            parameters=payload.parameters,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return {
        "observation_id": str(observation.id),
        "calculation_run_id": str(run.id),
        "result": run.result,
        "replay_hash": run.replay_hash,
    }


@router.get("/reviews")
async def list_reviews(db: AsyncSession = Depends(get_db)):
    cases = (
        await db.execute(select(ReviewCase).order_by(desc(ReviewCase.created_at)))
    ).scalars()
    output = []
    for item in cases:
        latest = (
            await db.execute(
                select(ReviewDecision)
                .where(ReviewDecision.review_case_id == item.id)
                .order_by(desc(ReviewDecision.created_at))
                .limit(1)
            )
        ).scalar_one_or_none()
        output.append(
            {
                "id": str(item.id),
                "validation_run_id": (
                    str(item.validation_run_id) if item.validation_run_id else None
                ),
                "observation_ids": item.observation_ids,
                "reason_codes": item.reason_codes,
                "created_at": item.created_at,
                "latest_decision": (
                    {
                        "id": str(latest.id),
                        "outcome": latest.outcome.value,
                        "decision": latest.decision,
                        "decided_by": latest.decided_by,
                        "created_at": latest.created_at,
                    }
                    if latest
                    else None
                ),
            }
        )
    return output


@router.post("/reviews/{case_id}/decisions", status_code=201)
async def decide_review(
    case_id: uuid.UUID,
    payload: DecisionRequest,
    db: AsyncSession = Depends(get_db),
):
    if payload.outcome is ReviewState.OPEN:
        raise HTTPException(status_code=422, detail="OPEN is not a decision outcome")
    if await db.get(ReviewCase, case_id) is None:
        raise HTTPException(status_code=404, detail="review case not found")
    if payload.supersedes_id:
        previous = await db.get(ReviewDecision, payload.supersedes_id)
        if previous is None or previous.review_case_id != case_id:
            raise HTTPException(status_code=422, detail="invalid supersedes_id")
    decision = ReviewDecision(
        review_case_id=case_id,
        supersedes_id=payload.supersedes_id,
        outcome=payload.outcome,
        decision=payload.decision,
        decided_by=payload.decided_by,
    )
    db.add(decision)
    await db.commit()
    await db.refresh(decision)
    return {
        "id": str(decision.id),
        "review_case_id": str(decision.review_case_id),
        "outcome": decision.outcome.value,
        "decision": decision.decision,
        "decided_by": decision.decided_by,
        "created_at": decision.created_at,
    }
