from __future__ import annotations

import re
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.providers import ModelConfig, create_provider
from app.core.config import settings
from app.core.database import get_db
from app.domain.evidence import sha256_bytes
from app.domain.panel_schema import validate_panel_schema, validate_ui_dsl
from app.models.dashboards import (
    Dashboard,
    DashboardVersion,
    ExtractionRun,
    PanelDefinition,
    PanelVersion,
    TemplateKind,
    VersionState,
)
from app.models.evidence import EvidenceArtifact, EvidenceFragment, SourceSnapshot
from app.services.dashboard_design_service import DashboardDesignService


router = APIRouter()
KEY_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]*$")


class DashboardCreate(BaseModel):
    key: str = Field(min_length=1, max_length=255)
    title: str = Field(min_length=1, max_length=500)
    description: str = ""


class PanelVersionCreate(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    key: str
    title: str
    description: str = ""
    data_schema: dict[str, Any]
    template_kind: TemplateKind = TemplateKind.UI_DSL
    ui_dsl: dict[str, Any] = Field(default_factory=dict)
    component_code: str | None = None
    visualization_contract: dict[str, Any] = Field(default_factory=dict)
    extraction_prompt: str = ""
    extraction_prompt_version: str = "1"
    model_settings: dict[str, Any] = Field(default_factory=dict)
    source_pool_id: uuid.UUID | None = None


class DashboardVersionCreate(BaseModel):
    state: VersionState = VersionState.DRAFT
    research_brief: dict[str, Any] = Field(default_factory=dict)
    generation_model: str | None = None
    generation_prompt_version: str | None = None
    panels: list[PanelVersionCreate] = Field(min_length=1)


class ProposalRequest(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    provider: str | None = None
    model: str | None = None
    base_url: str | None = None
    api_key: str | None = None


@router.post("", status_code=201)
async def create_dashboard(
    payload: DashboardCreate,
    db: AsyncSession = Depends(get_db),
):
    if not KEY_PATTERN.fullmatch(payload.key):
        raise HTTPException(status_code=422, detail="invalid dashboard key")
    if (
        await db.execute(select(Dashboard).where(Dashboard.key == payload.key))
    ).scalar_one_or_none():
        raise HTTPException(status_code=409, detail="dashboard key already exists")
    dashboard = Dashboard(**payload.model_dump())
    db.add(dashboard)
    await db.commit()
    await db.refresh(dashboard)
    return _dashboard_dict(dashboard)


@router.post("/propose")
async def propose_dashboard(payload: ProposalRequest):
    provider = create_provider(
        ModelConfig(
            provider=payload.provider or settings.AI_PROVIDER,
            model=payload.model or settings.AI_MODEL,
            api_key=payload.api_key or settings.AI_API_KEY,
            base_url=payload.base_url or settings.AI_API_BASE,
        )
    )
    try:
        return await DashboardDesignService(provider).propose(payload.title)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=exc.args[0])


@router.get("")
async def list_dashboards(db: AsyncSession = Depends(get_db)):
    dashboards = (await db.execute(select(Dashboard).order_by(Dashboard.title))).scalars()
    output = []
    for dashboard in dashboards:
        latest = (
            await db.execute(
                select(DashboardVersion)
                .where(DashboardVersion.dashboard_id == dashboard.id)
                .order_by(desc(DashboardVersion.version))
                .limit(1)
            )
        ).scalar_one_or_none()
        output.append(
            {
                **_dashboard_dict(dashboard),
                "latest_version": _version_dict(latest) if latest else None,
            }
        )
    return output


@router.post("/{dashboard_id}/versions", status_code=201)
async def create_dashboard_version(
    dashboard_id: uuid.UUID,
    payload: DashboardVersionCreate,
    db: AsyncSession = Depends(get_db),
):
    dashboard = await db.get(Dashboard, dashboard_id)
    if dashboard is None:
        raise HTTPException(status_code=404, detail="dashboard not found")
    for panel in payload.panels:
        if not KEY_PATTERN.fullmatch(panel.key):
            raise HTTPException(status_code=422, detail=f"invalid panel key: {panel.key}")
        issues = (
            validate_panel_schema(panel.data_schema)
            + validate_ui_dsl(panel.data_schema, panel.ui_dsl)
        )
        if issues:
            raise HTTPException(
                status_code=422,
                detail={
                    "panel": panel.key,
                    "issues": [
                        {"path": issue.path, "message": issue.message}
                        for issue in issues
                    ],
                },
            )
        if panel.template_kind is TemplateKind.CUSTOM_REACT and not panel.component_code:
            raise HTTPException(
                status_code=422,
                detail=f"custom React panel {panel.key} requires component_code",
            )

    next_version = (
        await db.scalar(
            select(func.coalesce(func.max(DashboardVersion.version), 0)).where(
                DashboardVersion.dashboard_id == dashboard.id
            )
        )
        + 1
    )
    version = DashboardVersion(
        dashboard_id=dashboard.id,
        version=next_version,
        state=payload.state,
        research_brief=payload.research_brief,
        generation_model=payload.generation_model,
        generation_prompt_version=payload.generation_prompt_version,
    )
    db.add(version)
    await db.flush()
    created_panels = []
    for panel_payload in payload.panels:
        definition = (
            await db.execute(
                select(PanelDefinition).where(
                    PanelDefinition.dashboard_id == dashboard.id,
                    PanelDefinition.key == panel_payload.key,
                )
            )
        ).scalar_one_or_none()
        if definition is None:
            definition = PanelDefinition(
                dashboard_id=dashboard.id,
                key=panel_payload.key,
            )
            db.add(definition)
            await db.flush()
        panel_version_number = (
            await db.scalar(
                select(func.coalesce(func.max(PanelVersion.version), 0)).where(
                    PanelVersion.panel_id == definition.id
                )
            )
            + 1
        )
        values = panel_payload.model_dump()
        values.pop("key")
        component_code = values.get("component_code")
        values["component_code_sha256"] = (
            sha256_bytes(component_code.encode("utf-8"))
            if component_code
            else None
        )
        panel_version = PanelVersion(
            panel_id=definition.id,
            dashboard_version_id=version.id,
            version=panel_version_number,
            **values,
        )
        db.add(panel_version)
        await db.flush()
        created_panels.append(_panel_version_dict(panel_version, definition.key))
    await db.commit()
    return {**_version_dict(version), "panels": created_panels}


@router.get("/{dashboard_id}/versions")
async def list_dashboard_versions(
    dashboard_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    dashboard = await db.get(Dashboard, dashboard_id)
    if dashboard is None:
        raise HTTPException(status_code=404, detail="dashboard not found")
    rows = (
        await db.execute(
            select(DashboardVersion, func.count(PanelVersion.id))
            .outerjoin(
                PanelVersion,
                PanelVersion.dashboard_version_id == DashboardVersion.id,
            )
            .where(DashboardVersion.dashboard_id == dashboard_id)
            .group_by(DashboardVersion.id)
            .order_by(desc(DashboardVersion.version))
        )
    ).all()
    return [
        {
            **_version_dict(version),
            "panel_count": panel_count,
        }
        for version, panel_count in rows
    ]


@router.get("/{dashboard_id}/versions/{version_number}")
async def get_dashboard_version(
    dashboard_id: uuid.UUID,
    version_number: int,
    db: AsyncSession = Depends(get_db),
):
    version = (
        await db.execute(
            select(DashboardVersion).where(
                DashboardVersion.dashboard_id == dashboard_id,
                DashboardVersion.version == version_number,
            )
        )
    ).scalar_one_or_none()
    if version is None:
        raise HTTPException(status_code=404, detail="dashboard version not found")
    rows = (
        await db.execute(
            select(PanelVersion, PanelDefinition.key)
            .join(PanelDefinition, PanelVersion.panel_id == PanelDefinition.id)
            .where(PanelVersion.dashboard_version_id == version.id)
            .order_by(PanelDefinition.key)
        )
    ).all()
    return {
        **_version_dict(version),
        "panels": [_panel_version_dict(panel, key) for panel, key in rows],
    }


@router.get("/{dashboard_id}/versions/{version_number}/view")
async def get_dashboard_view(
    dashboard_id: uuid.UUID,
    version_number: int,
    db: AsyncSession = Depends(get_db),
):
    dashboard = await db.get(Dashboard, dashboard_id)
    if dashboard is None:
        raise HTTPException(status_code=404, detail="dashboard not found")
    version = (
        await db.execute(
            select(DashboardVersion).where(
                DashboardVersion.dashboard_id == dashboard_id,
                DashboardVersion.version == version_number,
            )
        )
    ).scalar_one_or_none()
    if version is None:
        raise HTTPException(status_code=404, detail="dashboard version not found")
    panel_rows = (
        await db.execute(
            select(PanelVersion, PanelDefinition.key)
            .join(PanelDefinition, PanelVersion.panel_id == PanelDefinition.id)
            .where(PanelVersion.dashboard_version_id == version.id)
            .order_by(PanelDefinition.key)
        )
    ).all()
    panels = []
    for panel, key in panel_rows:
        run = (
            await db.execute(
                select(ExtractionRun)
                .where(ExtractionRun.panel_version_id == panel.id)
                .order_by(desc(ExtractionRun.created_at))
                .limit(1)
            )
        ).scalar_one_or_none()
        data = None
        evidence = []
        snapshot = None
        if run is not None:
            records = run.output.get("records", [])
            if records:
                data = records[0].get("data")
                fragment_ids = {
                    uuid.UUID(fragment_id)
                    for record in records
                    for fragment_id in record.get("evidence", {}).values()
                }
                if fragment_ids:
                    evidence_rows = (
                        await db.execute(
                            select(
                                EvidenceFragment,
                                SourceSnapshot,
                                EvidenceArtifact,
                            )
                            .join(
                                SourceSnapshot,
                                EvidenceFragment.snapshot_id == SourceSnapshot.id,
                            )
                            .join(
                                EvidenceArtifact,
                                SourceSnapshot.artifact_id == EvidenceArtifact.id,
                            )
                            .where(EvidenceFragment.id.in_(fragment_ids))
                        )
                    ).all()
                    for fragment, source_snapshot, artifact in evidence_rows:
                        snapshot = source_snapshot
                        evidence.append(
                            {
                                "fragment_id": str(fragment.id),
                                "locator_type": fragment.locator_type,
                                "locator": fragment.locator,
                                "text_sha256": fragment.extracted_text_sha256,
                                "source_url": source_snapshot.canonical_url,
                                "retrieved_at": source_snapshot.retrieved_at,
                                "published_at": source_snapshot.published_at,
                                "artifact_id": str(artifact.id),
                                "artifact_sha256": artifact.sha256,
                                "artifact_byte_size": artifact.byte_size,
                                "artifact_media_type": artifact.media_type,
                            }
                        )
        panels.append(
            {
                **_panel_version_dict(panel, key),
                "data": data,
                "extraction": (
                    {
                        "id": str(run.id),
                        "provider": run.provider,
                        "model": run.model,
                        "input_hash": run.input_hash,
                        "validation": run.validation,
                        "created_at": run.created_at,
                    }
                    if run
                    else None
                ),
                "snapshot_id": str(snapshot.id) if snapshot else None,
                "evidence": evidence,
            }
        )
    return {
        "dashboard": _dashboard_dict(dashboard),
        "version": _version_dict(version),
        "panels": panels,
    }


def _dashboard_dict(item: Dashboard) -> dict[str, Any]:
    return {
        "id": str(item.id),
        "key": item.key,
        "title": item.title,
        "description": item.description,
        "created_at": item.created_at,
    }


def _version_dict(item: DashboardVersion) -> dict[str, Any]:
    return {
        "id": str(item.id),
        "dashboard_id": str(item.dashboard_id),
        "version": item.version,
        "state": item.state.value,
        "research_brief": item.research_brief,
        "generation_model": item.generation_model,
        "generation_prompt_version": item.generation_prompt_version,
        "created_at": item.created_at,
    }


def _panel_version_dict(item: PanelVersion, key: str) -> dict[str, Any]:
    return {
        "id": str(item.id),
        "panel_id": str(item.panel_id),
        "key": key,
        "version": item.version,
        "title": item.title,
        "description": item.description,
        "data_schema": item.data_schema,
        "template_kind": item.template_kind.value,
        "ui_dsl": item.ui_dsl,
        "component_code": item.component_code,
        "component_code_sha256": item.component_code_sha256,
        "visualization_contract": item.visualization_contract,
        "extraction_prompt": item.extraction_prompt,
        "extraction_prompt_version": item.extraction_prompt_version,
        "model_settings": item.model_settings,
        "source_pool_id": str(item.source_pool_id) if item.source_pool_id else None,
        "created_at": item.created_at,
    }
