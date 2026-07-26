"""Add append-only trust assessments and stored-input L2 insights.

Revision ID: 0004_v2_trust_assessments_l2
Revises: 0003_v2_lineage_uniqueness
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0004_v2_trust_assessments_l2"
down_revision = "0003_v2_lineage_uniqueness"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "trust_assessments",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("observation_id", sa.UUID(), nullable=False),
        sa.Column("validation_run_id", sa.UUID(), nullable=True),
        sa.Column("calculation_run_id", sa.UUID(), nullable=True),
        sa.Column("review_decision_id", sa.UUID(), nullable=True),
        sa.Column("eligible", sa.Boolean(), nullable=False),
        sa.Column("reason_codes", postgresql.JSONB(), nullable=False),
        sa.Column("policy_version", sa.String(length=100), nullable=False),
        sa.Column("details", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["calculation_run_id"], ["calculation_runs.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["observation_id"], ["metric_observations.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["review_decision_id"], ["review_decisions.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["validation_run_id"], ["validation_runs.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_trust_assessments_observation_id"),
        "trust_assessments",
        ["observation_id"],
    )
    op.create_index(
        op.f("ix_trust_assessments_validation_run_id"),
        "trust_assessments",
        ["validation_run_id"],
    )
    op.create_index(
        op.f("ix_trust_assessments_eligible"),
        "trust_assessments",
        ["eligible"],
    )

    op.create_table(
        "l2_insights",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("input_hash", sa.String(length=64), nullable=False),
        sa.Column("engine_version", sa.String(length=100), nullable=False),
        sa.Column("prompt_version", sa.String(length=100), nullable=False),
        sa.Column("output", postgresql.JSONB(), nullable=False),
        sa.Column("created_by", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "input_hash ~ '^[0-9a-f]{64}$'",
            name="ck_l2_insight_input_hash_hex",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("input_hash"),
    )
    op.create_table(
        "l2_insight_inputs",
        sa.Column("insight_id", sa.UUID(), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("observation_id", sa.UUID(), nullable=False),
        sa.Column("trust_assessment_id", sa.UUID(), nullable=False),
        sa.CheckConstraint("ordinal >= 0", name="ck_l2_insight_input_ordinal"),
        sa.ForeignKeyConstraint(
            ["insight_id"], ["l2_insights.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["observation_id"], ["metric_observations.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["trust_assessment_id"], ["trust_assessments.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("insight_id", "ordinal"),
        sa.UniqueConstraint(
            "insight_id",
            "observation_id",
            name="uq_l2_insight_observation",
        ),
    )
    op.create_index(
        op.f("ix_l2_insight_inputs_observation_id"),
        "l2_insight_inputs",
        ["observation_id"],
    )
    for table in ("trust_assessments", "l2_insights", "l2_insight_inputs"):
        op.execute(
            f"""
            CREATE TRIGGER trg_{table}_immutable
            BEFORE UPDATE OR DELETE ON {table}
            FOR EACH ROW EXECUTE FUNCTION v2_reject_immutable_mutation();
            """
        )


def downgrade() -> None:
    for table in ("l2_insight_inputs", "l2_insights", "trust_assessments"):
        op.execute(f"DROP TRIGGER IF EXISTS trg_{table}_immutable ON {table}")
    op.drop_index(
        op.f("ix_l2_insight_inputs_observation_id"),
        table_name="l2_insight_inputs",
    )
    op.drop_table("l2_insight_inputs")
    op.drop_table("l2_insights")
    op.drop_index(
        op.f("ix_trust_assessments_eligible"),
        table_name="trust_assessments",
    )
    op.drop_index(
        op.f("ix_trust_assessments_validation_run_id"),
        table_name="trust_assessments",
    )
    op.drop_index(
        op.f("ix_trust_assessments_observation_id"),
        table_name="trust_assessments",
    )
    op.drop_table("trust_assessments")
