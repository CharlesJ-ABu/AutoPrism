"""V2 source pools, collection policy, and worker job models."""

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
    Float,
    ForeignKey,
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


class SourceKind(str, enum.Enum):
    HTML = "html"
    PDF = "pdf"
    CSV = "csv"
    XLSX = "xlsx"
    RSS = "rss"
    API = "api"


class CollectionJobState(str, enum.Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"


class HumanActionState(str, enum.Enum):
    OPEN = "open"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


class SourcePool(Base):
    __tablename__ = "source_pools"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    key: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    topic: Mapped[str] = mapped_column(Text, nullable=False)
    dashboard_version_key: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, index=True
    )
    discovery_query: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    settings: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)


class SourceDefinition(Base):
    __tablename__ = "source_definitions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    pool_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("source_pools.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    key: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    canonical_url: Mapped[str] = mapped_column(Text, nullable=False)
    kind: Mapped[SourceKind] = mapped_column(
        Enum(SourceKind, name="v2_source_kind"), nullable=False
    )
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    requires_auth: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    credential_reference: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True
    )
    robots_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    terms_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    global_reputation: Mapped[float] = mapped_column(Float, nullable=False)
    topic_authority: Mapped[float] = mapped_column(Float, nullable=False)
    refresh_policy: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    request_config: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    parser_config: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("pool_id", "key", name="uq_source_definition_pool_key"),
        CheckConstraint(
            "global_reputation >= 0 AND global_reputation <= 1",
            name="ck_source_global_reputation",
        ),
        CheckConstraint(
            "topic_authority >= 0 AND topic_authority <= 1",
            name="ck_source_topic_authority",
        ),
    )


class SourceDiscoveryRun(Base):
    """Immutable metadata for one user-authorized discovery request."""

    __tablename__ = "source_discovery_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    pool_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("source_pools.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    query: Mapped[str] = mapped_column(Text, nullable=False)
    provider_config_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    result_count: Mapped[int] = mapped_column(Integer, nullable=False)
    result_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    requested_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    completed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    __table_args__ = (
        CheckConstraint(
            "provider = 'google-programmable-search-v1'",
            name="ck_source_discovery_provider",
        ),
        CheckConstraint(
            "result_count >= 0 AND result_count <= 10",
            name="ck_source_discovery_result_count",
        ),
        CheckConstraint(
            "provider_config_hash ~ '^[0-9a-f]{64}$'",
            name="ck_source_discovery_provider_hash",
        ),
        CheckConstraint(
            "result_hash ~ '^[0-9a-f]{64}$'",
            name="ck_source_discovery_result_hash",
        ),
    )


class SourceDiscoveryCandidate(Base):
    """Immutable, unregistered candidate returned by a discovery provider."""

    __tablename__ = "source_discovery_candidates"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("source_discovery_runs.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    url_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    display_host: Mapped[str] = mapped_column(String(500), nullable=False)
    snippet: Mapped[str] = mapped_column(Text, nullable=False)
    mime_type: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    suggested_kind: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    __table_args__ = (
        CheckConstraint("ordinal >= 0", name="ck_source_discovery_candidate_ordinal"),
        CheckConstraint(
            "suggested_kind IN ('html', 'pdf', 'csv', 'xlsx', 'rss')",
            name="ck_source_discovery_candidate_kind",
        ),
        CheckConstraint(
            "url_sha256 ~ '^[0-9a-f]{64}$'",
            name="ck_source_discovery_candidate_url_hash",
        ),
        UniqueConstraint(
            "run_id",
            "ordinal",
            name="uq_source_discovery_candidate_ordinal",
        ),
        UniqueConstraint(
            "run_id",
            "url_sha256",
            name="uq_source_discovery_candidate_url",
        ),
    )


class CollectionJob(Base):
    __tablename__ = "collection_jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    source_definition_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("source_definitions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    idempotency_key: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True
    )
    state: Mapped[CollectionJobState] = mapped_column(
        Enum(CollectionJobState, name="v2_collection_job_state"),
        default=CollectionJobState.QUEUED,
        nullable=False,
        index=True,
    )
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    policy_result: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    result_snapshot_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("source_snapshots.id", ondelete="RESTRICT"),
        nullable=True,
    )
    error: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    requested_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    __table_args__ = (
        CheckConstraint("attempt_count >= 0", name="ck_collection_job_attempt_count"),
        CheckConstraint("max_attempts > 0", name="ck_collection_job_max_attempts"),
        Index("idx_collection_job_state_requested", "state", "requested_at"),
    )


class HumanActionRequest(Base):
    __tablename__ = "human_action_requests"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    collection_job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("collection_jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reason_code: Mapped[str] = mapped_column(String(100), nullable=False)
    instructions: Mapped[str] = mapped_column(Text, nullable=False)
    context: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    state: Mapped[HumanActionState] = mapped_column(
        Enum(HumanActionState, name="v2_human_action_state"),
        default=HumanActionState.OPEN,
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


def _reject_discovery_mutation(mapper, connection, target) -> None:
    raise RuntimeError(f"{type(target).__name__} is append-only")


for _discovery_model in (SourceDiscoveryRun, SourceDiscoveryCandidate):
    event.listen(_discovery_model, "before_update", _reject_discovery_mutation)
    event.listen(_discovery_model, "before_delete", _reject_discovery_mutation)
