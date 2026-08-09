from __future__ import annotations

import uuid
from typing import Any, Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel, Field, HttpUrl, SecretStr
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.sources import (
    CollectionJob,
    HumanActionRequest,
    SourceDefinition,
    SourceDiscoveryCandidate,
    SourceDiscoveryRun,
    SourceKind,
    SourcePool,
)
from app.services.collection_queue import CollectionQueue, create_collection_job
from app.services.search_discovery_service import (
    SearchDiscoveryError,
    SearchDiscoveryService,
    discovery_run_integrity_valid,
)


router = APIRouter()


class PoolCreate(BaseModel):
    key: str = Field(min_length=1, max_length=255, pattern=r"^[a-z0-9][a-z0-9_-]*$")
    name: str = Field(min_length=1, max_length=500)
    topic: str = Field(min_length=1)
    dashboard_version_key: str | None = None
    discovery_query: str | None = None
    settings: dict[str, Any] = Field(default_factory=dict)


class SourceCreate(BaseModel):
    key: str = Field(min_length=1, max_length=255, pattern=r"^[a-z0-9][a-z0-9_-]*$")
    name: str = Field(min_length=1, max_length=500)
    canonical_url: HttpUrl
    kind: SourceKind
    enabled: bool = True
    requires_auth: bool = False
    credential_reference: str | None = None
    robots_url: HttpUrl | None = None
    terms_url: HttpUrl | None = None
    global_reputation: float = Field(ge=0, le=1)
    topic_authority: float = Field(ge=0, le=1)
    refresh_policy: dict[str, Any] = Field(default_factory=dict)
    request_config: dict[str, Any] = Field(default_factory=dict)
    parser_config: dict[str, Any] = Field(default_factory=dict)


class GoogleDiscoveryRequest(BaseModel):
    api_key: SecretStr = Field(min_length=1, max_length=500)
    search_engine_id: str = Field(min_length=1, max_length=255)
    query: str | None = Field(default=None, min_length=1, max_length=500)
    limit: int = Field(default=10, ge=1, le=10)
    start: int = Field(default=1, ge=1, le=91)
    safe: Literal["active", "off"] = "active"


def _pool_dict(item: SourcePool) -> dict[str, Any]:
    return {
        "id": str(item.id),
        "key": item.key,
        "name": item.name,
        "topic": item.topic,
        "dashboard_version_key": item.dashboard_version_key,
        "discovery_query": item.discovery_query,
        "settings": item.settings,
        "created_at": item.created_at,
    }


def _source_dict(item: SourceDefinition) -> dict[str, Any]:
    return {
        "id": str(item.id),
        "pool_id": str(item.pool_id),
        "key": item.key,
        "name": item.name,
        "canonical_url": item.canonical_url,
        "kind": item.kind.value,
        "enabled": item.enabled,
        "requires_auth": item.requires_auth,
        "credential_reference": item.credential_reference,
        "robots_url": item.robots_url,
        "terms_url": item.terms_url,
        "global_reputation": item.global_reputation,
        "topic_authority": item.topic_authority,
        "refresh_policy": item.refresh_policy,
        "request_config": item.request_config,
        "parser_config": item.parser_config,
        "created_at": item.created_at,
    }


def _job_dict(item: CollectionJob) -> dict[str, Any]:
    return {
        "id": str(item.id),
        "source_definition_id": str(item.source_definition_id),
        "idempotency_key": item.idempotency_key,
        "state": item.state.value,
        "attempt_count": item.attempt_count,
        "max_attempts": item.max_attempts,
        "policy_result": item.policy_result,
        "result_snapshot_id": (
            str(item.result_snapshot_id) if item.result_snapshot_id else None
        ),
        "error": item.error,
        "requested_at": item.requested_at,
        "started_at": item.started_at,
        "finished_at": item.finished_at,
    }


def _candidate_dict(item: SourceDiscoveryCandidate) -> dict[str, Any]:
    return {
        "id": str(item.id),
        "ordinal": item.ordinal,
        "title": item.title,
        "url": item.url,
        "url_sha256": item.url_sha256,
        "display_host": item.display_host,
        "snippet": item.snippet,
        "mime_type": item.mime_type,
        "suggested_kind": item.suggested_kind,
        "created_at": item.created_at,
    }


def _discovery_run_dict(
    item: SourceDiscoveryRun,
    candidates: list[SourceDiscoveryCandidate],
) -> dict[str, Any]:
    return {
        "id": str(item.id),
        "pool_id": str(item.pool_id),
        "provider": item.provider,
        "query": item.query,
        "provider_config_hash": item.provider_config_hash,
        "result_count": item.result_count,
        "result_hash": item.result_hash,
        "integrity_valid": discovery_run_integrity_valid(item, candidates),
        "requested_at": item.requested_at,
        "completed_at": item.completed_at,
        "candidates": [_candidate_dict(candidate) for candidate in candidates],
    }


@router.post("/pools", status_code=201)
async def create_pool(payload: PoolCreate, db: AsyncSession = Depends(get_db)):
    existing = (
        await db.execute(select(SourcePool).where(SourcePool.key == payload.key))
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="source pool key already exists")
    item = SourcePool(**payload.model_dump())
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return _pool_dict(item)


@router.get("/pools")
async def list_pools(db: AsyncSession = Depends(get_db)):
    items = (await db.execute(select(SourcePool).order_by(SourcePool.name))).scalars()
    return [_pool_dict(item) for item in items]


@router.post("/pools/{pool_id}/discover", status_code=201)
async def discover_pool_sources(
    pool_id: uuid.UUID,
    payload: GoogleDiscoveryRequest,
    db: AsyncSession = Depends(get_db),
):
    pool = await db.get(SourcePool, pool_id)
    if pool is None:
        raise HTTPException(status_code=404, detail="source pool not found")
    query = (payload.query or pool.discovery_query or "").strip()
    if not query:
        raise HTTPException(
            status_code=422,
            detail="discovery query is required in the request or source pool",
        )
    try:
        run, candidates = await SearchDiscoveryService(db).discover_google(
            pool=pool,
            api_key=payload.api_key.get_secret_value(),
            search_engine_id=payload.search_engine_id.strip(),
            query=query,
            limit=payload.limit,
            start=payload.start,
            safe=payload.safe,
        )
    except SearchDiscoveryError as exc:
        await db.rollback()
        raise HTTPException(status_code=502, detail=str(exc)) from None
    return _discovery_run_dict(run, candidates)


@router.get("/discovery-runs")
async def list_discovery_runs(
    pool_id: uuid.UUID | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    statement = select(SourceDiscoveryRun)
    if pool_id is not None:
        statement = statement.where(SourceDiscoveryRun.pool_id == pool_id)
    runs = list(
        (
            await db.execute(
                statement.order_by(desc(SourceDiscoveryRun.requested_at)).limit(limit)
            )
        ).scalars()
    )
    if not runs:
        return []
    candidates = list(
        (
            await db.execute(
                select(SourceDiscoveryCandidate)
                .where(
                    SourceDiscoveryCandidate.run_id.in_([item.id for item in runs])
                )
                .order_by(
                    SourceDiscoveryCandidate.run_id,
                    SourceDiscoveryCandidate.ordinal,
                )
            )
        ).scalars()
    )
    by_run: dict[uuid.UUID, list[SourceDiscoveryCandidate]] = {
        item.id: [] for item in runs
    }
    for candidate in candidates:
        by_run[candidate.run_id].append(candidate)
    return [_discovery_run_dict(item, by_run[item.id]) for item in runs]


@router.post("/pools/{pool_id}", status_code=201)
async def create_source(
    pool_id: uuid.UUID,
    payload: SourceCreate,
    db: AsyncSession = Depends(get_db),
):
    if await db.get(SourcePool, pool_id) is None:
        raise HTTPException(status_code=404, detail="source pool not found")
    values = payload.model_dump()
    values["canonical_url"] = str(payload.canonical_url)
    values["robots_url"] = str(payload.robots_url) if payload.robots_url else None
    values["terms_url"] = str(payload.terms_url) if payload.terms_url else None
    item = SourceDefinition(pool_id=pool_id, **values)
    db.add(item)
    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise HTTPException(status_code=409, detail="source key already exists in pool")
    await db.refresh(item)
    return _source_dict(item)


@router.get("")
async def list_sources(
    pool_id: uuid.UUID | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    statement = select(SourceDefinition)
    if pool_id:
        statement = statement.where(SourceDefinition.pool_id == pool_id)
    items = (await db.execute(statement.order_by(SourceDefinition.name))).scalars()
    return [_source_dict(item) for item in items]


@router.post("/{source_id}/collect", status_code=202)
async def collect_source(
    source_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    source = await db.get(SourceDefinition, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="source not found")
    key = idempotency_key or f"manual:{source_id}:{uuid.uuid4()}"
    existing = (
        await db.execute(
            select(CollectionJob).where(CollectionJob.idempotency_key == key)
        )
    ).scalar_one_or_none()
    if existing:
        return _job_dict(existing)
    queue = CollectionQueue()
    try:
        try:
            job = await create_collection_job(db, queue, source, key)
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
    finally:
        await queue.close()
    return _job_dict(job)


@router.get("/jobs")
async def list_jobs(
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    items = (
        await db.execute(
            select(CollectionJob).order_by(desc(CollectionJob.requested_at)).limit(limit)
        )
    ).scalars()
    return [_job_dict(item) for item in items]


@router.get("/actions")
async def list_human_actions(
    db: AsyncSession = Depends(get_db),
):
    items = (
        await db.execute(
            select(HumanActionRequest).order_by(desc(HumanActionRequest.created_at))
        )
    ).scalars()
    return [
        {
            "id": str(item.id),
            "collection_job_id": str(item.collection_job_id),
            "reason_code": item.reason_code,
            "instructions": item.instructions,
            "context": item.context,
            "state": item.state.value,
            "created_at": item.created_at,
            "resolved_at": item.resolved_at,
        }
        for item in items
    ]
