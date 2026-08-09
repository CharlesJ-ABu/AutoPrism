"""V2 append-only persistence models for acquisition and evidence lineage."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone
from decimal import Decimal
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
    Numeric,
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


class UncertaintyState(str, enum.Enum):
    EXACT = "exact"
    BOUNDED = "bounded"
    UNKNOWN = "unknown"


class ConversionKind(str, enum.Enum):
    UNIT = "unit"
    CURRENCY = "currency"


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
    source_definition_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("source_definitions.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
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
            "source_definition_id",
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
        Index(
            "uq_metric_observation_supersedes",
            "supersedes_id",
            unique=True,
            postgresql_where=supersedes_id.is_not(None),
        ),
    )


class ObservationEvidenceSet(Base):
    """Frozen cardinality for one observation's evidence citations."""

    __tablename__ = "observation_evidence_sets"

    observation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("metric_observations.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    citation_count: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    __table_args__ = (
        CheckConstraint(
            "citation_count > 0",
            name="ck_observation_evidence_set_count",
        ),
    )


class ObservationEvidenceLink(Base):
    """Ordered evidence fragments supporting one frozen INFO evidence set."""

    __tablename__ = "observation_evidence_links"

    observation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("observation_evidence_sets.observation_id", ondelete="RESTRICT"),
        primary_key=True,
    )
    ordinal: Mapped[int] = mapped_column(Integer, primary_key=True)
    evidence_fragment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("evidence_fragments.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(String(50), nullable=False)
    claim_key: Mapped[str] = mapped_column(String(255), nullable=False)
    field_path: Mapped[str] = mapped_column(String(500), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    __table_args__ = (
        CheckConstraint("ordinal >= 0", name="ck_observation_evidence_ordinal"),
        CheckConstraint(
            "role IN ('primary', 'supporting', 'dimension', 'calculation_input')",
            name="ck_observation_evidence_role",
        ),
        UniqueConstraint(
            "observation_id",
            "evidence_fragment_id",
            "field_path",
            name="uq_observation_evidence_claim_fragment",
        ),
        Index(
            "uq_observation_evidence_primary",
            "observation_id",
            unique=True,
            postgresql_where=role == "primary",
        ),
    )


class LineageBackfillAudit(Base):
    """Append-only migration evidence for conservative historical run linking."""

    __tablename__ = "lineage_backfill_audits"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    details: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)


class ObservationExtractionLink(Base):
    """Append-only direct link from an extracted INFO value to its exact run output."""

    __tablename__ = "observation_extraction_links"

    observation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("metric_observations.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    extraction_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("extraction_runs.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    output_record_ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    field_path: Mapped[str] = mapped_column(String(500), nullable=False)
    match_method: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    __table_args__ = (
        CheckConstraint(
            "output_record_ordinal >= 0",
            name="ck_observation_extraction_record_ordinal",
        ),
        CheckConstraint(
            "match_method IN ('direct_write', 'backfill_exact')",
            name="ck_observation_extraction_match_method",
        ),
        UniqueConstraint(
            "extraction_run_id",
            "output_record_ordinal",
            "field_path",
            name="uq_observation_extraction_output_field",
        ),
    )


class ObservationGeography(Base):
    """Frozen evidence-bound geographic scope for one INFO observation."""

    __tablename__ = "observation_geographies"

    observation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("metric_observations.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    scope: Mapped[dict] = mapped_column(JSONB, nullable=False)
    evidence_count: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    __table_args__ = (
        CheckConstraint(
            "jsonb_typeof(scope) = 'object'",
            name="ck_observation_geography_scope_object",
        ),
        CheckConstraint(
            "scope ->> 'contract_version' = 'geo-scope-v1'",
            name="ck_observation_geography_contract",
        ),
        CheckConstraint(
            "evidence_count > 0",
            name="ck_observation_geography_evidence_count",
        ),
    )


class ObservationGeographyEvidence(Base):
    """Ordered source claims that prove one frozen geographic scope."""

    __tablename__ = "observation_geography_evidence"

    observation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("observation_geographies.observation_id", ondelete="RESTRICT"),
        primary_key=True,
    )
    ordinal: Mapped[int] = mapped_column(Integer, primary_key=True)
    evidence_fragment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("evidence_fragments.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    claim_key: Mapped[str] = mapped_column(String(255), nullable=False)
    field_path: Mapped[str] = mapped_column(String(500), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    __table_args__ = (
        CheckConstraint(
            "ordinal >= 0",
            name="ck_observation_geography_evidence_ordinal",
        ),
        UniqueConstraint(
            "observation_id",
            "evidence_fragment_id",
            "field_path",
            name="uq_observation_geography_claim_fragment",
        ),
    )


class ExtractionRunInputSet(Base):
    """Frozen cardinality for one extraction request input manifest."""

    __tablename__ = "extraction_run_input_sets"

    extraction_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("extraction_runs.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    input_count: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    __table_args__ = (
        CheckConstraint(
            "input_count >= 0",
            name="ck_extraction_run_input_set_count",
        ),
    )


class ExtractionRunInput(Base):
    """Ordered immutable manifest of fragments supplied to one extraction."""

    __tablename__ = "extraction_run_inputs"

    extraction_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("extraction_run_input_sets.extraction_run_id", ondelete="RESTRICT"),
        primary_key=True,
    )
    ordinal: Mapped[int] = mapped_column(Integer, primary_key=True)
    evidence_fragment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("evidence_fragments.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    extracted_text_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    manifest_entry_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    __table_args__ = (
        CheckConstraint("ordinal >= 0", name="ck_extraction_run_input_ordinal"),
        CheckConstraint(
            "extracted_text_sha256 ~ '^[0-9a-f]{64}$'",
            name="ck_extraction_run_input_text_hash_hex",
        ),
        CheckConstraint(
            "manifest_entry_hash ~ '^[0-9a-f]{64}$'",
            name="ck_extraction_run_input_entry_hash_hex",
        ),
        UniqueConstraint(
            "extraction_run_id",
            "evidence_fragment_id",
            name="uq_extraction_run_input_fragment",
        ),
    )


class ObservationRevision(Base):
    """Auditable explanation of one immutable observation replacement."""

    __tablename__ = "observation_revisions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    original_observation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("metric_observations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    replacement_observation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("metric_observations.id", ondelete="RESTRICT"),
        nullable=False,
        unique=True,
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    revised_by: Mapped[str] = mapped_column(String(255), nullable=False)
    metadata_json: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "original_observation_id",
            name="uq_observation_revision_original",
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


class CalculationRunInput(Base):
    """Ordered inputs and the exact trust decisions frozen by decimal-v2."""

    __tablename__ = "calculation_run_inputs"

    calculation_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("calculation_runs.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    ordinal: Mapped[int] = mapped_column(Integer, primary_key=True)
    observation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("metric_observations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    trust_assessment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("trust_assessments.id", ondelete="RESTRICT", use_alter=True),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    __table_args__ = (
        CheckConstraint("ordinal >= 0", name="ck_calculation_run_input_ordinal"),
        UniqueConstraint(
            "calculation_run_id",
            "observation_id",
            name="uq_calculation_run_input_observation",
        ),
    )


class ObservationNumericValue(Base):
    """Frozen machine-readable decimal and its explicitly declared uncertainty."""

    __tablename__ = "observation_numeric_values"

    observation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("metric_observations.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    value: Mapped[Decimal] = mapped_column(Numeric(), nullable=False)
    uncertainty_kind: Mapped[UncertaintyState] = mapped_column(
        Enum(UncertaintyState, name="v2_uncertainty_state"), nullable=False
    )
    absolute_error: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(), nullable=True
    )
    uncertainty_basis: Mapped[dict] = mapped_column(JSONB, nullable=False)
    evidence_count: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    __table_args__ = (
        CheckConstraint(
            "(uncertainty_kind = 'EXACT' AND absolute_error = 0) "
            "OR (uncertainty_kind = 'BOUNDED' AND absolute_error >= 0) "
            "OR (uncertainty_kind = 'UNKNOWN' AND absolute_error IS NULL)",
            name="ck_observation_numeric_uncertainty",
        ),
        CheckConstraint(
            "jsonb_typeof(uncertainty_basis) = 'object'",
            name="ck_observation_numeric_basis_object",
        ),
        CheckConstraint(
            "(uncertainty_kind = 'BOUNDED' AND evidence_count > 0) OR "
            "(uncertainty_kind IN ('EXACT', 'UNKNOWN') AND evidence_count = 0)",
            name="ck_observation_numeric_evidence_count",
        ),
    )


class ObservationNumericEvidence(Base):
    """Ordered source claims proving a bounded absolute-error value."""

    __tablename__ = "observation_numeric_evidence"

    observation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("observation_numeric_values.observation_id", ondelete="RESTRICT"),
        primary_key=True,
    )
    ordinal: Mapped[int] = mapped_column(Integer, primary_key=True)
    evidence_fragment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("evidence_fragments.id", ondelete="RESTRICT"),
        nullable=False,
    )
    claim_key: Mapped[str] = mapped_column(String(255), nullable=False)
    field_path: Mapped[str] = mapped_column(String(500), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    __table_args__ = (
        CheckConstraint("ordinal >= 0", name="ck_observation_numeric_evidence_ordinal"),
        UniqueConstraint(
            "observation_id",
            "evidence_fragment_id",
            "field_path",
            name="uq_observation_numeric_evidence_claim",
        ),
    )


class ConversionRun(Base):
    """Append-only replayable unit or currency conversion."""

    __tablename__ = "conversion_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    output_observation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("metric_observations.id", ondelete="RESTRICT"),
        nullable=False,
        unique=True,
    )
    input_observation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("metric_observations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    input_trust_assessment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("trust_assessments.id", ondelete="RESTRICT", use_alter=True),
        nullable=False,
    )
    kind: Mapped[ConversionKind] = mapped_column(
        Enum(ConversionKind, name="v2_conversion_kind"), nullable=False
    )
    fx_rate_observation_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("metric_observations.id", ondelete="RESTRICT"),
        nullable=True,
    )
    fx_rate_trust_assessment_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("trust_assessments.id", ondelete="RESTRICT", use_alter=True),
        nullable=True,
    )
    registry_version: Mapped[str] = mapped_column(String(100), nullable=False)
    engine_version: Mapped[str] = mapped_column(String(100), nullable=False)
    plan: Mapped[dict] = mapped_column(JSONB, nullable=False)
    input_snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False)
    result: Mapped[dict] = mapped_column(JSONB, nullable=False)
    replay_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    __table_args__ = (
        CheckConstraint(
            "replay_hash ~ '^[0-9a-f]{64}$'",
            name="ck_conversion_run_replay_hash_hex",
        ),
        CheckConstraint(
            "(kind = 'UNIT' AND fx_rate_observation_id IS NULL "
            "AND fx_rate_trust_assessment_id IS NULL) OR "
            "(kind = 'CURRENCY' AND fx_rate_observation_id IS NOT NULL "
            "AND fx_rate_trust_assessment_id IS NOT NULL)",
            name="ck_conversion_run_kind_inputs",
        ),
    )


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

    __table_args__ = (
        Index(
            "uq_review_decision_supersedes",
            "supersedes_id",
            unique=True,
            postgresql_where=supersedes_id.is_not(None),
        ),
        Index(
            "uq_review_decision_root",
            "review_case_id",
            unique=True,
            postgresql_where=supersedes_id.is_(None),
        ),
    )


class TrustAssessment(Base):
    """Append-only eligibility decision over one immutable observation."""

    __tablename__ = "trust_assessments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    observation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("metric_observations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    validation_run_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("validation_runs.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    calculation_run_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("calculation_runs.id", ondelete="RESTRICT"),
        nullable=True,
    )
    conversion_run_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversion_runs.id", ondelete="RESTRICT", use_alter=True),
        nullable=True,
    )
    review_decision_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("review_decisions.id", ondelete="RESTRICT"),
        nullable=True,
    )
    eligible: Mapped[bool] = mapped_column(Boolean, nullable=False, index=True)
    reason_codes: Mapped[list] = mapped_column(JSONB, nullable=False)
    policy_version: Mapped[str] = mapped_column(String(100), nullable=False)
    details: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)


class L2Insight(Base):
    """Stored-input-only deterministic L2 synthesis."""

    __tablename__ = "l2_insights"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    input_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    engine_version: Mapped[str] = mapped_column(String(100), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(100), nullable=False)
    output: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_by: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    __table_args__ = (
        CheckConstraint(
            "input_hash ~ '^[0-9a-f]{64}$'",
            name="ck_l2_insight_input_hash_hex",
        ),
    )


class L2InsightInput(Base):
    """Normalized ordered L2 input with database-enforced references."""

    __tablename__ = "l2_insight_inputs"

    insight_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("l2_insights.id", ondelete="RESTRICT"),
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
    )

    __table_args__ = (
        CheckConstraint("ordinal >= 0", name="ck_l2_insight_input_ordinal"),
        UniqueConstraint(
            "insight_id",
            "observation_id",
            name="uq_l2_insight_observation",
        ),
    )


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
    ObservationEvidenceSet,
    ObservationEvidenceLink,
    LineageBackfillAudit,
    ObservationExtractionLink,
    ObservationGeography,
    ObservationGeographyEvidence,
    ExtractionRunInputSet,
    ExtractionRunInput,
    ObservationRevision,
    CalculationRun,
    CalculationRunInput,
    ObservationNumericValue,
    ObservationNumericEvidence,
    ConversionRun,
    ValidationRun,
    ReviewCase,
    ReviewDecision,
    TrustAssessment,
    L2Insight,
    L2InsightInput,
):
    event.listen(_immutable_model, "before_update", _reject_immutable_mutation)
    event.listen(_immutable_model, "before_delete", _reject_immutable_mutation)
