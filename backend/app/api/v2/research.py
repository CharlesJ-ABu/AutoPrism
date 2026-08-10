from __future__ import annotations

import uuid
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, HttpUrl, SecretStr
from sqlalchemy import desc, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.providers import ModelConfig, create_provider
from app.core.config import settings
from app.core.database import get_db
from app.domain.evidence import canonical_json, sha256_bytes, sha256_json
from app.models.research import (
    EvidenceInterpretation,
    EvidenceInterpretationInput,
    ResearchAction,
    ResearchActionEvent,
    ResearchActionType,
    ResearchEventType,
    ResearchPlan,
    ResearchRun,
)
from app.models.evidence import TrustAssessment
from app.models.sources import CollectionJob, SourceDefinition, SourcePool
from app.services.collection_queue import CollectionQueue, create_collection_job
from app.services.research_service import (
    RESEARCH_PLAN_PROMPT_VERSION,
    RESEARCH_PLAN_SYSTEM_PROMPT,
    ResearchActionService,
    ResearchPlanningService,
    ResearchPlanDocument,
    build_research_action_payloads,
    build_research_input_manifest,
)
from app.services.interpretation_service import (
    INTERPRETATION_PROMPT_VERSION,
    INTERPRETATION_SYSTEM_PROMPT,
    InterpretationService,
)
from app.services.trust_service import TrustService
from app.services.search_discovery_service import (
    SearchDiscoveryError,
    SearchDiscoveryService,
)


router = APIRouter()


class ResearchPlanRequest(BaseModel):
    source_pool_id: uuid.UUID
    title: str = Field(min_length=3, max_length=500)
    objective: str = Field(min_length=10, max_length=5000)
    constraints: dict[str, Any] = Field(default_factory=dict)
    provider: str | None = Field(default=None, max_length=100)
    model: str | None = Field(default=None, max_length=255)
    base_url: HttpUrl | None = None
    api_key: SecretStr | None = Field(default=None, max_length=500)


class DiscoveryExecutionRequest(BaseModel):
    api_key: SecretStr = Field(min_length=1, max_length=500)
    search_engine_id: str = Field(min_length=1, max_length=255)
    authorization_confirmed: bool


class CollectionExecutionRequest(BaseModel):
    authorization_confirmed: bool


class InterpretationRequest(BaseModel):
    title: str = Field(min_length=3, max_length=500)
    question: str = Field(min_length=10, max_length=5000)
    observation_ids: list[uuid.UUID] = Field(min_length=1, max_length=100)
    created_by: str = Field(min_length=1, max_length=255)
    provider: str | None = Field(default=None, max_length=100)
    model: str | None = Field(default=None, max_length=255)
    base_url: HttpUrl | None = None
    api_key: SecretStr | None = Field(default=None, max_length=500)


async def _events_for_action(
    db: AsyncSession,
    action_id: uuid.UUID,
) -> list[ResearchActionEvent]:
    events = list(
        (
            await db.execute(
                select(ResearchActionEvent)
                .where(ResearchActionEvent.action_id == action_id)
            )
        ).scalars()
    )
    by_predecessor = {event.predecessor_id: event for event in events}
    ordered: list[ResearchActionEvent] = []
    predecessor_id = None
    while predecessor_id in by_predecessor:
        event = by_predecessor.pop(predecessor_id)
        ordered.append(event)
        predecessor_id = event.id
    return ordered if not by_predecessor else []


def _event_dict(event: ResearchActionEvent) -> dict[str, Any]:
    return {
        "id": str(event.id),
        "event_type": event.event_type.value,
        "actor_label": event.actor_label,
        "details": event.details,
        "predecessor_id": str(event.predecessor_id) if event.predecessor_id else None,
        "created_at": event.created_at,
    }


async def _action_dict(
    db: AsyncSession,
    action: ResearchAction,
) -> dict[str, Any]:
    events = await _events_for_action(db, action.id)
    current = events[-1] if events else None
    job = None
    if current and isinstance(current.details, dict):
        raw_job_id = current.details.get("collection_job_id")
        try:
            job_id = uuid.UUID(raw_job_id) if isinstance(raw_job_id, str) else None
        except ValueError:
            job_id = None
        if job_id:
            job = await db.get(CollectionJob, job_id)
    return {
        "id": str(action.id),
        "run_id": str(action.run_id),
        "plan_id": str(action.plan_id),
        "ordinal": action.ordinal,
        "action_type": action.action_type.value,
        "specification": action.specification,
        "requires_authorization": action.requires_authorization,
        "created_at": action.created_at,
        "current_state": current.event_type.value if current else "missing",
        "events": [_event_dict(event) for event in events],
        "collection_job": (
            {
                "id": str(job.id),
                "state": job.state.value,
                "policy_result": job.policy_result,
                "result_snapshot_id": (
                    str(job.result_snapshot_id) if job.result_snapshot_id else None
                ),
                "error": job.error,
            }
            if job
            else None
        ),
    }


async def _run_dict(db: AsyncSession, run: ResearchRun) -> dict[str, Any]:
    plan = (
        await db.execute(select(ResearchPlan).where(ResearchPlan.run_id == run.id))
    ).scalar_one_or_none()
    actions: list[ResearchAction] = []
    if plan:
        actions = list(
            (
                await db.execute(
                    select(ResearchAction)
                    .where(ResearchAction.plan_id == plan.id)
                    .order_by(ResearchAction.ordinal)
                )
            ).scalars()
        )
    serialized_actions = [await _action_dict(db, action) for action in actions]
    prompt_hash = sha256_bytes(RESEARCH_PLAN_SYSTEM_PROMPT.encode("utf-8"))
    expected_actions: list[tuple[ResearchActionType, dict[str, Any]]] = []
    try:
        manifest_inventory = plan.input_manifest.get("inventory") if plan else None
        registered_sources = (
            manifest_inventory.get("registered_sources")
            if isinstance(manifest_inventory, dict)
            else None
        )
        if plan and isinstance(registered_sources, list):
            expected_actions = build_research_action_payloads(
                ResearchPlanDocument.model_validate(plan.plan),
                registered_sources,
            )
    except (TypeError, ValueError):
        expected_actions = []
    integrity_valid = bool(
        plan
        and plan.prompt_version == RESEARCH_PLAN_PROMPT_VERSION
        and plan.system_prompt_sha256 == prompt_hash
        and isinstance(plan.input_manifest, dict)
        and plan.input_hash == sha256_json(plan.input_manifest)
        and plan.input_manifest
        == build_research_input_manifest(
            inventory=plan.input_manifest.get("inventory"),
            provider_name=plan.input_manifest.get("provider"),
            model_name=plan.input_manifest.get("model"),
            provider_config_hash=plan.input_manifest.get("provider_config_hash"),
        )
        and plan.output_hash == sha256_json(plan.plan)
        and plan.action_count == len(actions)
        and [action.ordinal for action in actions] == list(range(len(actions)))
        and len(expected_actions) == len(actions)
        and all(
            action.action_type == expected_type
            and action.specification == expected_specification
            and action.requires_authorization is True
            for action, (expected_type, expected_specification) in zip(
                actions,
                expected_actions,
                strict=True,
            )
        )
        and all(
            serialized["events"]
            and serialized["events"][0]["event_type"] == "proposed"
            for serialized in serialized_actions
        )
    )
    return {
        "id": str(run.id),
        "source_pool_id": str(run.source_pool_id),
        "title": run.title,
        "objective": run.objective,
        "constraints": run.constraints,
        "actor_label": run.actor_label,
        "created_at": run.created_at,
        "plan": (
            {
                "id": str(plan.id),
                "provider": plan.provider,
                "model": plan.model,
                "prompt_version": plan.prompt_version,
                "system_prompt_sha256": plan.system_prompt_sha256,
                "input_hash": plan.input_hash,
                "input_manifest": plan.input_manifest,
                "output_hash": plan.output_hash,
                "document": plan.plan,
                "action_count": plan.action_count,
                "model_metadata": plan.model_metadata,
                "integrity_valid": integrity_valid,
                "created_at": plan.created_at,
            }
            if plan
            else None
        ),
        "actions": serialized_actions,
    }


async def _interpretation_dict(
    db: AsyncSession,
    interpretation: EvidenceInterpretation,
) -> dict[str, Any]:
    inputs = list(
        (
            await db.execute(
                select(EvidenceInterpretationInput)
                .where(
                    EvidenceInterpretationInput.interpretation_id
                    == interpretation.id
                )
                .order_by(EvidenceInterpretationInput.ordinal)
            )
        ).scalars()
    )
    trust_service = TrustService(db)
    current_inputs = []
    for item in inputs:
        assessment = await db.get(TrustAssessment, item.trust_assessment_id)
        current_inputs.append(
            bool(assessment and await trust_service.is_assessment_current(assessment))
        )
    manifest = (
        interpretation.input_manifest
        if isinstance(interpretation.input_manifest, dict)
        else {}
    )
    manifest_inputs = manifest.get("inputs")
    manifest_inputs_valid = bool(
        isinstance(manifest_inputs, list)
        and all(isinstance(item, dict) for item in manifest_inputs)
    )
    try:
        input_hash_valid = interpretation.input_hash == sha256_json(
            interpretation.input_manifest
        )
        output_hash_valid = interpretation.output_hash == sha256_json(
            interpretation.output
        )
    except (TypeError, ValueError, OverflowError):
        input_hash_valid = False
        output_hash_valid = False
    integrity_valid = bool(
        interpretation.prompt_version == INTERPRETATION_PROMPT_VERSION
        and interpretation.system_prompt_sha256
        == sha256_bytes(INTERPRETATION_SYSTEM_PROMPT.encode("utf-8"))
        and manifest_inputs_valid
        and input_hash_valid
        and output_hash_valid
        and interpretation.input_count == len(inputs)
        and [item.ordinal for item in inputs] == list(range(len(inputs)))
        and manifest.get("contract_version")
        == INTERPRETATION_PROMPT_VERSION
        and [item.get("observation_id") for item in manifest_inputs]
        == [str(item.observation_id) for item in inputs]
        and [item.get("trust_assessment_id") for item in manifest_inputs]
        == [str(item.trust_assessment_id) for item in inputs]
    )
    return {
        "id": str(interpretation.id),
        "title": interpretation.title,
        "question": interpretation.question,
        "provider": interpretation.provider,
        "model": interpretation.model,
        "prompt_version": interpretation.prompt_version,
        "system_prompt_sha256": interpretation.system_prompt_sha256,
        "input_hash": interpretation.input_hash,
        "input_manifest": interpretation.input_manifest,
        "output_hash": interpretation.output_hash,
        "output": interpretation.output,
        "input_count": interpretation.input_count,
        "created_by": interpretation.created_by,
        "created_at": interpretation.created_at,
        "integrity_valid": integrity_valid,
        "currently_grounded": integrity_valid and all(current_inputs),
        "inputs": [
            {
                "ordinal": item.ordinal,
                "observation_id": str(item.observation_id),
                "trust_assessment_id": str(item.trust_assessment_id),
                "currently_eligible": current_inputs[index],
            }
            for index, item in enumerate(inputs)
        ],
    }


@router.post("/runs", status_code=201)
async def create_research_run(
    payload: ResearchPlanRequest,
    db: AsyncSession = Depends(get_db),
):
    pool = await db.get(SourcePool, payload.source_pool_id)
    if pool is None:
        raise HTTPException(status_code=404, detail="source pool not found")
    try:
        constraints_json = canonical_json(payload.constraints)
    except (TypeError, ValueError, OverflowError):
        raise HTTPException(
            status_code=422,
            detail="research constraints must be finite canonical JSON",
        ) from None
    if len(constraints_json) > 20_000:
        raise HTTPException(status_code=422, detail="research constraints are too large")
    provider_name = payload.provider or settings.AI_PROVIDER
    model_name = payload.model or settings.AI_MODEL
    provider_base_url = (
        str(payload.base_url) if payload.base_url else settings.AI_API_BASE
    )
    provider_config_hash = sha256_json(
        {
            "provider": provider_name,
            "model": model_name,
            "base_url": provider_base_url,
        }
    )
    try:
        provider = create_provider(
            ModelConfig(
                provider=provider_name,
                model=model_name,
                api_key=(
                    payload.api_key.get_secret_value()
                    if payload.api_key is not None
                    else settings.AI_API_KEY
                ),
                base_url=provider_base_url,
            )
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    try:
        run, _plan, _actions = await ResearchPlanningService(db, provider).create_plan(
            pool=pool,
            title=payload.title,
            objective=payload.objective,
            constraints=payload.constraints,
            provider_name=provider_name,
            model_name=model_name,
            provider_config_hash=provider_config_hash,
        )
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from None
    except httpx.HTTPError:
        await db.rollback()
        raise HTTPException(status_code=502, detail="model provider request failed") from None
    except (KeyError, TypeError, IndexError):
        await db.rollback()
        raise HTTPException(
            status_code=502,
            detail="model provider returned a malformed response",
        ) from None
    return await _run_dict(db, run)


@router.get("/runs")
async def list_research_runs(
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    runs = list(
        (
            await db.execute(
                select(ResearchRun).order_by(desc(ResearchRun.created_at)).limit(limit)
            )
        ).scalars()
    )
    return [await _run_dict(db, run) for run in runs]


@router.get("/runs/{run_id}")
async def get_research_run(
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    run = await db.get(ResearchRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="research run not found")
    return await _run_dict(db, run)


@router.post("/interpretations", status_code=201)
async def create_interpretation(
    payload: InterpretationRequest,
    db: AsyncSession = Depends(get_db),
):
    provider_name = payload.provider or settings.AI_PROVIDER
    model_name = payload.model or settings.AI_MODEL
    provider_base_url = str(payload.base_url) if payload.base_url else settings.AI_API_BASE
    provider_config_hash = sha256_json(
        {
            "provider": provider_name,
            "model": model_name,
            "base_url": provider_base_url,
        }
    )
    try:
        provider = create_provider(
            ModelConfig(
                provider=provider_name,
                model=model_name,
                api_key=(
                    payload.api_key.get_secret_value()
                    if payload.api_key is not None
                    else settings.AI_API_KEY
                ),
                base_url=provider_base_url,
            )
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    try:
        interpretation = await InterpretationService(db, provider).create(
            title=payload.title,
            question=payload.question,
            observation_ids=payload.observation_ids,
            provider_name=provider_name,
            model_name=model_name,
            provider_config_hash=provider_config_hash,
            created_by=payload.created_by,
        )
    except LookupError as exc:
        await db.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from None
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from None
    except httpx.HTTPError:
        await db.rollback()
        raise HTTPException(status_code=502, detail="model provider request failed") from None
    except (KeyError, TypeError, IndexError):
        await db.rollback()
        raise HTTPException(
            status_code=502,
            detail="model provider returned a malformed response",
        ) from None
    return await _interpretation_dict(db, interpretation)


@router.get("/interpretations")
async def list_interpretations(
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    interpretations = list(
        (
            await db.execute(
                select(EvidenceInterpretation)
                .order_by(desc(EvidenceInterpretation.created_at))
                .limit(limit)
            )
        ).scalars()
    )
    return [
        await _interpretation_dict(db, interpretation)
        for interpretation in interpretations
    ]


async def _load_action_context(
    db: AsyncSession,
    action_id: uuid.UUID,
) -> tuple[ResearchAction, ResearchRun, SourcePool]:
    action = await db.get(ResearchAction, action_id)
    if action is None:
        raise HTTPException(status_code=404, detail="research action not found")
    run = await db.get(ResearchRun, action.run_id)
    pool = await db.get(SourcePool, run.source_pool_id) if run else None
    if run is None or pool is None:
        raise HTTPException(status_code=409, detail="research action lineage is incomplete")
    return action, run, pool


async def _authorize_and_start(
    db: AsyncSession,
    action: ResearchAction,
) -> ResearchActionService:
    service = ResearchActionService(db)
    try:
        current = await service.current_event(action.id)
        if current.event_type in {
            ResearchEventType.PROPOSED,
            ResearchEventType.BLOCKED,
            ResearchEventType.FAILED,
        }:
            await service.append_event(
                action=action,
                event_type=ResearchEventType.AUTHORIZED,
                actor_label="local-user-self-attested",
                details={"authorization_confirmed": True},
            )
        await service.append_event(
            action=action,
            event_type=ResearchEventType.STARTED,
            actor_label="autoprism-research-orchestrator",
            details={"action_type": action.action_type.value},
        )
    except (ValueError, IntegrityError) as exc:
        await db.rollback()
        raise HTTPException(
            status_code=409,
            detail="research action changed or is not executable in its current state",
        ) from exc
    return service


@router.post("/actions/{action_id}/discover")
async def execute_discovery_action(
    action_id: uuid.UUID,
    payload: DiscoveryExecutionRequest,
    db: AsyncSession = Depends(get_db),
):
    if not payload.authorization_confirmed:
        raise HTTPException(status_code=422, detail="discovery requires explicit authorization")
    action, _run, pool = await _load_action_context(db, action_id)
    if action.action_type != ResearchActionType.DISCOVER:
        raise HTTPException(status_code=422, detail="research action is not discovery")
    service = await _authorize_and_start(db, action)
    specification = action.specification
    try:
        discovery_run, candidates = await SearchDiscoveryService(db).discover_google(
            pool=pool,
            api_key=payload.api_key.get_secret_value(),
            search_engine_id=payload.search_engine_id,
            query=str(specification["query"]),
            limit=int(specification["limit"]),
            start=1,
            safe="active",
        )
    except (SearchDiscoveryError, KeyError, TypeError, ValueError) as exc:
        await db.rollback()
        await service.append_event(
            action=action,
            event_type=ResearchEventType.FAILED,
            actor_label="autoprism-research-orchestrator",
            details={"reason_code": "DISCOVERY_FAILED"},
        )
        detail = (
            str(exc)
            if isinstance(exc, SearchDiscoveryError)
            else "planned discovery specification is invalid"
        )
        raise HTTPException(status_code=502, detail=detail) from None
    await service.append_event(
        action=action,
        event_type=ResearchEventType.COMPLETED,
        actor_label="autoprism-research-orchestrator",
        details={
            "discovery_run_id": str(discovery_run.id),
            "result_count": len(candidates),
        },
    )
    return await _action_dict(db, action)


@router.post("/actions/{action_id}/collect", status_code=202)
async def execute_collection_action(
    action_id: uuid.UUID,
    payload: CollectionExecutionRequest,
    db: AsyncSession = Depends(get_db),
):
    if not payload.authorization_confirmed:
        raise HTTPException(status_code=422, detail="collection requires explicit authorization")
    action, run, _pool = await _load_action_context(db, action_id)
    if action.action_type != ResearchActionType.COLLECT:
        raise HTTPException(status_code=422, detail="research action is not collection")
    raw_source_id = action.specification.get("source_definition_id")
    try:
        source_id = uuid.UUID(raw_source_id) if isinstance(raw_source_id, str) else None
    except ValueError:
        source_id = None
    source = await db.get(SourceDefinition, source_id) if source_id else None
    if source is None or source.pool_id != run.source_pool_id or not source.enabled:
        raise HTTPException(status_code=409, detail="planned source is unavailable or disabled")
    service = await _authorize_and_start(db, action)
    events = await _events_for_action(db, action.id)
    attempt = sum(event.event_type == ResearchEventType.AUTHORIZED for event in events)
    queue = CollectionQueue()
    try:
        job = await create_collection_job(
            db,
            queue,
            source,
            f"research:{action.id}:attempt:{attempt}",
        )
    except RuntimeError as exc:
        await service.append_event(
            action=action,
            event_type=ResearchEventType.FAILED,
            actor_label="autoprism-research-orchestrator",
            details={"reason_code": "QUEUE_UNAVAILABLE"},
        )
        raise HTTPException(status_code=503, detail=str(exc)) from None
    finally:
        await queue.close()
    await service.append_event(
        action=action,
        event_type=ResearchEventType.QUEUED,
        actor_label="autoprism-research-orchestrator",
        details={
            "collection_job_id": str(job.id),
            "source_definition_id": str(source.id),
        },
    )
    return await _action_dict(db, action)
