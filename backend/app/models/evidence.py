"""V2 append-only persistence models for acquisition and evidence lineage."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
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


class TrustState(str, enum.Enum):
    UNVERIFIED = "unverified"
    VERIFIED = "verified"
    REJECTED = "rejected"
    LEGACY_UNVERIFIED = "legacy_unverified"


class VerificationState(str, enum.Enum):
    PENDING = "pending"
    PASSED = "passed"
    CONFLICT = "conflict"
    NEEDS_REVIEW = "needs_review"
    REJECTED = "rejected"


class ReviewState(str, enum.Enum):
    OPEN = "open"
    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_INFORMATION = "needs_information"


class EvidenceArtifact(Base):
    """Content-addressed immutable source bytes."""

    __tablename__ = "evidence_artifacts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    sha256: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    byte_size: Mapped[int] = mapped_column(Integer, nullable=False)
    media_type: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_uri: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    __table_args__ = (
        CheckConstraint("byte_size >= 0", name="ck_evidence_artifact_size"),
        CheckConstraint("length(sha256) = 64", name="ck_evidence_artifact_sha_length"),
    )


class SourceSnapshot(Base):
    """One immutable observation of a source at a retrieval time."""

    __tablename__ = "source_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    source_key: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    canonical_url: Mapped[str] = mapped_column(Text, nullable=False)
    artifact_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("evidence_artifacts.id", ondelete="RESTRICT"),
        nullable=False,
    )
    predecessor_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("source_snapshots.id", ondelete="RESTRICT"),
        nullable=True,
    )
    retrieved_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    http_status: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    response_headers: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    source_metadata: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    trust_state: Mapped[TrustState] = mapped_column(
        Enum(TrustState, name="v2_trust_state"),
        default=TrustState.UNVERIFIED,
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    __table_args__ = (
        Index("idx_source_snapshot_url_retrieved", "canonical_url", "retrieved_at"),
        UniqueConstraint(
            "source_key",
            "retrieved_at",
            "artifact_id",
            name="uq_source_snapshot_capture",
        ),
    )


class EvidenceFragment(Base):
    """A reproducible location inside a source snapshot."""

    __tablename__ = "evidence_fragments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    snapshot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("source_snapshots.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    locator_type: Mapped[str] = mapped_column(String(50), nullable=False)
    locator: Mapped[dict] = mapped_column(JSONB, nullable=False)
    extracted_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    extracted_text_sha256: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "snapshot_id",
            "locator_type",
            "locator",
            name="uq_evidence_fragment_locator",
        ),
    )


class MetricObservation(Base):
    """Append-only INFO value with exact evidence and schema lineage."""

    __tablename__ = "metric_observations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    panel_version_key: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    schema_version: Mapped[str] = mapped_column(String(100), nullable=False)
    metric_key: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    evidence_fragment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("evidence_fragments.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    supersedes_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("metric_observations.id", ondelete="RESTRICT"),
        nullable=True,
    )
    raw_value: Mapped[dict] = mapped_column(JSONB, nullable=False)
    normalized_value: Mapped[dict] = mapped_column(JSONB, nullable=False)
    unit: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    currency: Mapped[Optional[str]] = mapped_column(String(3), nullable=True)
    observed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    period_start: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    period_end: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    geographic_scope: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    dimensions: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    extraction_model: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    extraction_prompt_version: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True
    )
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    trust_state: Mapped[TrustState] = mapped_column(
        Enum(TrustState, name="v2_metric_trust_state"),
        default=TrustState.UNVERIFIED,
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    __table_args__ = (
        CheckConstraint(
            "confidence IS NULL OR (confidence >= 0 AND confidence <= 1)",
            name="ck_metric_observation_confidence",
        ),
        CheckConstraint(
            "period_end IS NULL OR period_start IS NULL OR period_end >= period_start",
            name="ck_metric_observation_period",
        ),
        Index(
            "idx_metric_observation_lookup",
            "panel_version_key",
            "metric_key",
            "observed_at",
        ),
    )


class CalculationRun(Base):
    """Deterministic calculation record that can be replayed."""

    __tablename__ = "calculation_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    output_observation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("metric_observations.id", ondelete="RESTRICT"),
        nullable=False,
        unique=True,
    )
    operation: Mapped[str] = mapped_column(String(100), nullable=False)
    input_observation_ids: Mapped[list] = mapped_column(JSONB, nullable=False)
    parameters: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    result: Mapped[dict] = mapped_column(JSONB, nullable=False)
    engine_version: Mapped[str] = mapped_column(String(100), nullable=False)
    replay_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)


class ValidationRun(Base):
    """Cross-source validation result for one comparable metric group."""

    __tablename__ = "validation_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    comparison_key: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    observation_ids: Mapped[list] = mapped_column(JSONB, nullable=False)
    rule_version: Mapped[str] = mapped_column(String(100), nullable=False)
    tolerance: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    result: Mapped[dict] = mapped_column(JSONB, nullable=False)
    state: Mapped[VerificationState] = mapped_column(
        Enum(VerificationState, name="v2_verification_state"),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)


class ReviewCase(Base):
    """Immutable review request created when automation cannot establish trust."""

    __tablename__ = "review_cases"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    validation_run_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("validation_runs.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    observation_ids: Mapped[list] = mapped_column(JSONB, nullable=False)
    reason_codes: Mapped[list] = mapped_column(JSONB, nullable=False)
    # Transitional columns created by the first V2 development schema. New V2
    # code records decisions in ReviewDecision and never updates these fields.
    state: Mapped[ReviewState] = mapped_column(
        Enum(ReviewState, name="v2_review_state"),
        default=ReviewState.OPEN,
        nullable=False,
        index=True,
    )
    decision: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    decided_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    decided_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)


class ReviewDecision(Base):
    """Append-only human decision; later decisions supersede earlier ones."""

    __tablename__ = "review_decisions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    review_case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("review_cases.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    supersedes_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("review_decisions.id", ondelete="RESTRICT"),
        nullable=True,
    )
    outcome: Mapped[ReviewState] = mapped_column(
        Enum(ReviewState, name="v2_review_state"),
        nullable=False,
        index=True,
    )
    decision: Mapped[dict] = mapped_column(JSONB, nullable=False)
    decided_by: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)


def _reject_immutable_mutation(mapper, connection, target) -> None:
    raise RuntimeError(
        f"{type(target).__name__} is append-only; create a superseding record"
    )


# ORM-level guardrail. Phase 0's Alembic migration will add equivalent
# database-level protection so bulk SQL cannot bypass the invariant.
for _immutable_model in (
    EvidenceArtifact,
    SourceSnapshot,
    EvidenceFragment,
    MetricObservation,
    CalculationRun,
    ValidationRun,
    ReviewCase,
    ReviewDecision,
):
    event.listen(_immutable_model, "before_update", _reject_immutable_mutation)
    event.listen(_immutable_model, "before_delete", _reject_immutable_mutation)
