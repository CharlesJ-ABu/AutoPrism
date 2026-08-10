from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
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


class ResearchActionType(str, enum.Enum):
    DISCOVER = "discover"
    COLLECT = "collect"


class ResearchEventType(str, enum.Enum):
    PROPOSED = "proposed"
    AUTHORIZED = "authorized"
    STARTED = "started"
    COMPLETED = "completed"
    QUEUED = "queued"
    BLOCKED = "blocked"
    FAILED = "failed"


class ResearchRun(Base):
    """Immutable user research objective bound to one source pool."""

    __tablename__ = "research_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    source_pool_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("source_pools.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    objective: Mapped[str] = mapped_column(Text, nullable=False)
    constraints: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    actor_label: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)


class ResearchPlan(Base):
    """Frozen model-generated plan; the model proposes but never executes tools."""

    __tablename__ = "research_plans"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("research_runs.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    provider: Mapped[str] = mapped_column(String(100), nullable=False)
    model: Mapped[str] = mapped_column(String(255), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(100), nullable=False)
    system_prompt_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    input_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    input_manifest: Mapped[dict] = mapped_column(JSONB, nullable=False)
    output_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    plan: Mapped[dict] = mapped_column(JSONB, nullable=False)
    action_count: Mapped[int] = mapped_column(Integer, nullable=False)
    model_metadata: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("id", "run_id", name="uq_research_plan_id_run"),
        UniqueConstraint("run_id", name="uq_research_plans_run_id"),
        CheckConstraint("action_count >= 1 AND action_count <= 20", name="ck_research_plan_action_count"),
        CheckConstraint("system_prompt_sha256 ~ '^[0-9a-f]{64}$'", name="ck_research_plan_prompt_hash"),
        CheckConstraint("input_hash ~ '^[0-9a-f]{64}$'", name="ck_research_plan_input_hash"),
        CheckConstraint("output_hash ~ '^[0-9a-f]{64}$'", name="ck_research_plan_output_hash"),
    )


class ResearchAction(Base):
    """Frozen allowlisted tool proposal belonging to one plan."""

    __tablename__ = "research_actions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    plan_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    action_type: Mapped[ResearchActionType] = mapped_column(
        Enum(ResearchActionType, name="v2_research_action_type"), nullable=False
    )
    specification: Mapped[dict] = mapped_column(JSONB, nullable=False)
    requires_authorization: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    __table_args__ = (
        ForeignKeyConstraint(
            ["plan_id", "run_id"],
            ["research_plans.id", "research_plans.run_id"],
            name="fk_research_action_plan_run",
            ondelete="RESTRICT",
        ),
        UniqueConstraint("plan_id", "ordinal", name="uq_research_action_plan_ordinal"),
        UniqueConstraint("id", "run_id", name="uq_research_action_id_run"),
        CheckConstraint("ordinal >= 0", name="ck_research_action_ordinal"),
    )


class ResearchActionEvent(Base):
    """Append-only state transition for an allowlisted research action."""

    __tablename__ = "research_action_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    action_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    event_type: Mapped[ResearchEventType] = mapped_column(
        Enum(ResearchEventType, name="v2_research_event_type"), nullable=False
    )
    actor_label: Mapped[str] = mapped_column(String(255), nullable=False)
    details: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    predecessor_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    __table_args__ = (
        ForeignKeyConstraint(
            ["action_id", "run_id"],
            ["research_actions.id", "research_actions.run_id"],
            name="fk_research_event_action_run",
            ondelete="RESTRICT",
        ),
        UniqueConstraint("id", "action_id", "run_id", name="uq_research_event_id_action_run"),
        UniqueConstraint("predecessor_id", name="uq_research_event_predecessor"),
        ForeignKeyConstraint(
            ["predecessor_id", "action_id", "run_id"],
            [
                "research_action_events.id",
                "research_action_events.action_id",
                "research_action_events.run_id",
            ],
            name="fk_research_event_same_action",
            ondelete="RESTRICT",
        ),
        Index(
            "uq_research_event_root",
            "action_id",
            unique=True,
            postgresql_where=(predecessor_id.is_(None)),
        ),
    )


class EvidenceInterpretation(Base):
    """Append-only model narrative over frozen currently eligible inputs."""

    __tablename__ = "evidence_interpretations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    provider: Mapped[str] = mapped_column(String(100), nullable=False)
    model: Mapped[str] = mapped_column(String(255), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(100), nullable=False)
    system_prompt_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    input_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    input_manifest: Mapped[dict] = mapped_column(JSONB, nullable=False)
    output_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    output: Mapped[dict] = mapped_column(JSONB, nullable=False)
    input_count: Mapped[int] = mapped_column(Integer, nullable=False)
    model_metadata: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    created_by: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    __table_args__ = (
        CheckConstraint(
            "input_count >= 1 AND input_count <= 100",
            name="ck_evidence_interpretation_input_count",
        ),
        CheckConstraint(
            "system_prompt_sha256 ~ '^[0-9a-f]{64}$'",
            name="ck_evidence_interpretation_prompt_hash",
        ),
        CheckConstraint(
            "input_hash ~ '^[0-9a-f]{64}$'",
            name="ck_evidence_interpretation_input_hash",
        ),
        CheckConstraint(
            "output_hash ~ '^[0-9a-f]{64}$'",
            name="ck_evidence_interpretation_output_hash",
        ),
    )


class EvidenceInterpretationInput(Base):
    """Ordered database references for one frozen model interpretation."""

    __tablename__ = "evidence_interpretation_inputs"

    interpretation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("evidence_interpretations.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    ordinal: Mapped[int] = mapped_column(Integer, primary_key=True)
    observation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("metric_observations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    trust_assessment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("trust_assessments.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    __table_args__ = (
        CheckConstraint(
            "ordinal >= 0",
            name="ck_evidence_interpretation_input_ordinal",
        ),
        UniqueConstraint(
            "interpretation_id",
            "observation_id",
            name="uq_evidence_interpretation_observation",
        ),
    )


def _reject_research_mutation(mapper, connection, target) -> None:
    raise RuntimeError(f"{type(target).__name__} is append-only")


for _append_only_model in (
    ResearchRun,
    ResearchPlan,
    ResearchAction,
    ResearchActionEvent,
    EvidenceInterpretation,
    EvidenceInterpretationInput,
):
    event.listen(_append_only_model, "before_update", _reject_research_mutation)
    event.listen(_append_only_model, "before_delete", _reject_research_mutation)
