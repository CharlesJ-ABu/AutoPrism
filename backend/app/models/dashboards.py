"""Versioned dynamic dashboards and panel contracts."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    event,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class VersionState(str, enum.Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class TemplateKind(str, enum.Enum):
    UI_DSL = "ui_dsl"
    CUSTOM_REACT = "custom_react"


class Dashboard(Base):
    __tablename__ = "dashboards"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    key: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)


class DashboardVersion(Base):
    __tablename__ = "dashboard_versions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    dashboard_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("dashboards.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    state: Mapped[VersionState] = mapped_column(
        Enum(VersionState, name="v2_dashboard_version_state"),
        default=VersionState.DRAFT,
        nullable=False,
        index=True,
    )
    research_brief: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    generation_model: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    generation_prompt_version: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "dashboard_id", "version", name="uq_dashboard_version_number"
        ),
    )


class PanelDefinition(Base):
    __tablename__ = "panel_definitions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    dashboard_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("dashboards.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    key: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("dashboard_id", "key", name="uq_panel_dashboard_key"),
    )


class PanelVersion(Base):
    """Frozen panel implementation bound to one dashboard version."""

    __tablename__ = "panel_versions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    panel_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("panel_definitions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    dashboard_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("dashboard_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    data_schema: Mapped[dict] = mapped_column(JSONB, nullable=False)
    template_kind: Mapped[TemplateKind] = mapped_column(
        Enum(TemplateKind, name="v2_panel_template_kind"),
        nullable=False,
    )
    ui_dsl: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    component_code: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    component_code_sha256: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True
    )
    visualization_contract: Mapped[dict] = mapped_column(
        JSONB, default=dict, nullable=False
    )
    extraction_prompt: Mapped[str] = mapped_column(Text, default="", nullable=False)
    extraction_prompt_version: Mapped[str] = mapped_column(
        String(100), default="1", nullable=False
    )
    model_settings: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    source_pool_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("source_pools.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "panel_id",
            "version",
            name="uq_panel_version_number",
        ),
        UniqueConstraint(
            "panel_id",
            "dashboard_version_id",
            name="uq_panel_dashboard_version",
        ),
    )


class ExtractionRun(Base):
    __tablename__ = "extraction_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    panel_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("panel_versions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    snapshot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("source_snapshots.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    provider: Mapped[str] = mapped_column(String(100), nullable=False)
    model: Mapped[str] = mapped_column(String(255), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(100), nullable=False)
    input_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    output: Mapped[dict] = mapped_column(JSONB, nullable=False)
    validation: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)


def _reject_version_mutation(mapper, connection, target) -> None:
    raise RuntimeError(
        f"{type(target).__name__} is frozen; create a new version instead"
    )


for _version_model in (DashboardVersion, PanelVersion, ExtractionRun):
    event.listen(_version_model, "before_update", _reject_version_mutation)
    event.listen(_version_model, "before_delete", _reject_version_mutation)
