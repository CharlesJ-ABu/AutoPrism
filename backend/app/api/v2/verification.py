from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import desc, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.domain.evidence import (
    CalculationOperation,
    normalize_calculation_contract,
)
from app.domain.numeric import unit_registry_payload
from app.models.evidence import (
    CalculationRun,
    ConversionKind,
    ConversionRun,
    MetricObservation,
    ReviewCase,
    ReviewDecision,
    ReviewState,
    TrustAssessment,
    ValidationRun,
)
from app.services.trust_service import TrustService
from app.services.verification_service import VerificationService


router = APIRouter()


class ValidationRequest(BaseModel):
    observation_ids: list[uuid.UUID] = Field(min_length=1)
    absolute_tolerance: str = Field(min_length=1)
    relative_tolerance: str = Field(min_length=1)


class CalculationRequest(BaseModel):
    operation: CalculationOperation
    input_observation_ids: list[uuid.UUID] = Field(min_length=1)
    output_metric_key: str
    output_unit: str | None = None
    output_quantum: str = Field(min_length=1)
    parameters: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_operation_parameters(self):
        # Request validation has no database values yet. Zero placeholders let
        # the shared domain helper validate operation arity and parameter shape;
        # VerificationService repeats the same contract against stored values.
        normalize_calculation_contract(
            self.operation,
            [0] * len(self.input_observation_ids),
            self.parameters,
        )
        return self


class ConversionRequest(BaseModel):
    input_observation_id: uuid.UUID
    kind: ConversionKind
    output_metric_key: str = Field(min_length=1, max_length=255)
    output_quantum: str = Field(min_length=1)
    to_unit: str | None = None
    to_currency: str | None = Field(default=None, min_length=3, max_length=3)
    fx_rate_observation_id: uuid.UUID | None = None

    @model_validator(mode="after")
    def validate_kind_fields(self):
        if self.kind is ConversionKind.UNIT:
            if not self.to_unit or self.to_currency or self.fx_rate_observation_id:
                raise ValueError("unit conversion requires only to_unit")
        elif (
            not self.to_currency
            or self.to_unit is not None
            or self.fx_rate_observation_id is None
        ):
            raise ValueError(
                "currency conversion requires to_currency and fx_rate_observation_id"
            )
        return self


class DecisionRequest(BaseModel):
    outcome: ReviewState
    decision: dict[str, Any] = Field(min_length=1)
    decided_by: str = Field(min_length=1, max_length=255)
    supersedes_id: uuid.UUID | None = None


class AssessmentRequest(BaseModel):
    observation_id: uuid.UUID
    validation_run_id: uuid.UUID | None = None


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
    except (ValueError, KeyError, TypeError) as exc:
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
            output_quantum=payload.output_quantum,
            parameters=payload.parameters,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except (ValueError, KeyError, TypeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return {
        "observation_id": str(observation.id),
        "calculation_run_id": str(run.id),
        "result": run.result,
        "replay_hash": run.replay_hash,
    }


@router.get("/unit-registry")
async def get_unit_registry():
    return unit_registry_payload()


@router.post("/conversions")
async def create_conversion(
    payload: ConversionRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        observation, run = await VerificationService(db).convert(
            input_observation_id=payload.input_observation_id,
            kind=payload.kind,
            output_metric_key=payload.output_metric_key,
            output_quantum=payload.output_quantum,
            to_unit=payload.to_unit,
            to_currency=payload.to_currency,
            fx_rate_observation_id=payload.fx_rate_observation_id,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except (ValueError, KeyError, TypeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return {
        "observation_id": str(observation.id),
        "conversion_run_id": str(run.id),
        "result": run.result,
        "replay_hash": run.replay_hash,
    }


async def _panel_observation_ids(
    db: AsyncSession,
    panel_version_key: str | None,
) -> set[str] | None:
    if panel_version_key is None:
        return None
    values = (
        await db.execute(
            select(MetricObservation.id).where(
                MetricObservation.panel_version_key == panel_version_key
            )
        )
    ).scalars()
    return {str(value) for value in values}


@router.get("/calculations")
async def list_calculations(
    panel_version_key: str | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
):
    statement = (
        select(CalculationRun, MetricObservation)
        .join(
            MetricObservation,
            CalculationRun.output_observation_id == MetricObservation.id,
        )
    )
    if panel_version_key:
        statement = statement.where(
            MetricObservation.panel_version_key == panel_version_key
        )
    rows = (
        await db.execute(
            statement.order_by(desc(CalculationRun.created_at)).limit(limit)
        )
    ).all()
    return [
        {
            "id": str(run.id),
            "output_observation_id": str(run.output_observation_id),
            "output_metric_key": output.metric_key,
            "operation": run.operation,
            "input_observation_ids": run.input_observation_ids,
            "parameters": run.parameters,
            "result": run.result,
            "engine_version": run.engine_version,
            "replay_hash": run.replay_hash,
            "created_at": run.created_at,
        }
        for run, output in rows
    ]


@router.get("/conversions")
async def list_conversions(
    panel_version_key: str | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
):
    statement = select(ConversionRun, MetricObservation).join(
        MetricObservation,
        ConversionRun.output_observation_id == MetricObservation.id,
    )
    if panel_version_key:
        statement = statement.where(
            MetricObservation.panel_version_key == panel_version_key
        )
    rows = (
        await db.execute(
            statement.order_by(desc(ConversionRun.created_at)).limit(limit)
        )
    ).all()
    return [
        {
            "id": str(run.id),
            "output_observation_id": str(run.output_observation_id),
            "output_metric_key": output.metric_key,
            "input_observation_id": str(run.input_observation_id),
            "input_trust_assessment_id": str(run.input_trust_assessment_id),
            "kind": run.kind.value,
            "fx_rate_observation_id": (
                str(run.fx_rate_observation_id)
                if run.fx_rate_observation_id
                else None
            ),
            "registry_version": run.registry_version,
            "engine_version": run.engine_version,
            "plan": run.plan,
            "input_snapshot": run.input_snapshot,
            "result": run.result,
            "replay_hash": run.replay_hash,
            "created_at": run.created_at,
        }
        for run, output in rows
    ]


@router.get("/validations")
async def list_validations(
    panel_version_key: str | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
):
    panel_ids = await _panel_observation_ids(db, panel_version_key)
    runs = (
        await db.execute(
            select(ValidationRun)
            .order_by(desc(ValidationRun.created_at))
            .limit(limit)
        )
    ).scalars()
    return [
        {
            "id": str(run.id),
            "comparison_key": run.comparison_key,
            "observation_ids": run.observation_ids,
            "rule_version": run.rule_version,
            "tolerance": run.tolerance,
            "result": run.result,
            "state": run.state.value,
            "created_at": run.created_at,
        }
        for run in runs
        if panel_ids is None or bool(panel_ids.intersection(run.observation_ids))
    ]


@router.get("/reviews")
async def list_reviews(
    panel_version_key: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    panel_ids = await _panel_observation_ids(db, panel_version_key)
    cases = (
        await db.execute(select(ReviewCase).order_by(desc(ReviewCase.created_at)))
    ).scalars().all()
    output = []
    for item in cases:
        if panel_ids is not None and not panel_ids.intersection(item.observation_ids):
            continue
        decisions = (
            await db.execute(
                select(ReviewDecision)
                .where(ReviewDecision.review_case_id == item.id)
                .order_by(ReviewDecision.created_at, ReviewDecision.id)
            )
        ).scalars().all()
        latest = decisions[-1] if decisions else None
        output.append(
            {
                "id": str(item.id),
                "validation_run_id": (
                    str(item.validation_run_id) if item.validation_run_id else None
                ),
                "observation_ids": item.observation_ids,
                "reason_codes": item.reason_codes,
                "created_at": item.created_at,
                "decisions": [
                    {
                        "id": str(decision.id),
                        "supersedes_id": (
                            str(decision.supersedes_id)
                            if decision.supersedes_id
                            else None
                        ),
                        "outcome": decision.outcome.value,
                        "decision": decision.decision,
                        "decided_by": decision.decided_by,
                        "created_at": decision.created_at,
                    }
                    for decision in decisions
                ],
                "latest_decision": (
                    {
                        "id": str(latest.id),
                        "supersedes_id": (
                            str(latest.supersedes_id)
                            if latest.supersedes_id
                            else None
                        ),
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


@router.post("/assessments", status_code=201)
async def assess_observation(
    payload: AssessmentRequest,
    db: AsyncSession = Depends(get_db),
):
    service = TrustService(db)
    try:
        assessment = await service.assess(
            observation_id=payload.observation_id,
            validation_run_id=payload.validation_run_id,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {
        "id": str(assessment.id),
        "observation_id": str(assessment.observation_id),
        "validation_run_id": (
            str(assessment.validation_run_id)
            if assessment.validation_run_id
            else None
        ),
        "calculation_run_id": (
            str(assessment.calculation_run_id)
            if assessment.calculation_run_id
            else None
        ),
        "conversion_run_id": (
            str(assessment.conversion_run_id)
            if assessment.conversion_run_id
            else None
        ),
        "review_decision_id": (
            str(assessment.review_decision_id)
            if assessment.review_decision_id
            else None
        ),
        "eligible": assessment.eligible,
        "currently_eligible": await service.is_assessment_current(assessment),
        "reason_codes": assessment.reason_codes,
        "policy_version": assessment.policy_version,
        "details": assessment.details,
        "created_at": assessment.created_at,
    }


@router.get("/assessments")
async def list_assessments(
    panel_version_key: str | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
):
    statement = (
        select(TrustAssessment, MetricObservation)
        .join(
            MetricObservation,
            TrustAssessment.observation_id == MetricObservation.id,
        )
    )
    if panel_version_key:
        statement = statement.where(
            MetricObservation.panel_version_key == panel_version_key
        )
    rows = (
        await db.execute(
            statement.order_by(
                desc(TrustAssessment.created_at),
                desc(TrustAssessment.id),
            ).limit(limit)
        )
    ).all()
    output = []
    latest_observation_ids: set[uuid.UUID] = set()
    trust_service = TrustService(db)
    for assessment, observation in rows:
        is_latest_assessment = observation.id not in latest_observation_ids
        latest_observation_ids.add(observation.id)
        currently_eligible = bool(
            is_latest_assessment
            and await trust_service.is_assessment_current(assessment)
        )
        output.append(
            {
                "id": str(assessment.id),
                "observation_id": str(assessment.observation_id),
                "metric_key": observation.metric_key,
                "validation_run_id": (
                    str(assessment.validation_run_id)
                    if assessment.validation_run_id
                    else None
                ),
                "calculation_run_id": (
                    str(assessment.calculation_run_id)
                    if assessment.calculation_run_id
                    else None
                ),
                "conversion_run_id": (
                    str(assessment.conversion_run_id)
                    if assessment.conversion_run_id
                    else None
                ),
                "review_decision_id": (
                    str(assessment.review_decision_id)
                    if assessment.review_decision_id
                    else None
                ),
                "eligible": assessment.eligible,
                "currently_eligible": currently_eligible,
                "reason_codes": assessment.reason_codes,
                "policy_version": assessment.policy_version,
                "details": assessment.details,
                "created_at": assessment.created_at,
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
    latest = (
        await db.execute(
            select(ReviewDecision)
            .where(ReviewDecision.review_case_id == case_id)
            .order_by(desc(ReviewDecision.created_at), desc(ReviewDecision.id))
            .limit(1)
        )
    ).scalar_one_or_none()
    if latest is None and payload.supersedes_id is not None:
        raise HTTPException(status_code=422, detail="first decision cannot supersede")
    if latest is not None and payload.supersedes_id != latest.id:
        raise HTTPException(
            status_code=409,
            detail=f"decision must supersede latest decision {latest.id}",
        )
    decision = ReviewDecision(
        review_case_id=case_id,
        supersedes_id=payload.supersedes_id,
        outcome=payload.outcome,
        decision=payload.decision,
        decided_by=payload.decided_by,
    )
    db.add(decision)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=409,
            detail="review decision was concurrently superseded",
        ) from exc
    await db.refresh(decision)
    return {
        "id": str(decision.id),
        "review_case_id": str(decision.review_case_id),
        "supersedes_id": (
            str(decision.supersedes_id) if decision.supersedes_id else None
        ),
        "outcome": decision.outcome.value,
        "decision": decision.decision,
        "decided_by": decision.decided_by,
        "created_at": decision.created_at,
    }
