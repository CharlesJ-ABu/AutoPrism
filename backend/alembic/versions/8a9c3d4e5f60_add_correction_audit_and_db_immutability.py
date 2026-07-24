"""add correction audit and database immutability

Revision ID: 8a9c3d4e5f60
Revises: d59076df48fb
Create Date: 2026-07-25 02:05:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "8a9c3d4e5f60"
down_revision: Union[str, None] = "d59076df48fb"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

IMMUTABLE_TABLES = (
    "evidence_artifacts",
    "source_snapshots",
    "evidence_fragments",
    "metric_observations",
    "observation_revisions",
    "calculation_runs",
    "validation_runs",
    "review_cases",
    "review_decisions",
    "dashboard_versions",
    "panel_versions",
    "extraction_runs",
)


def upgrade() -> None:
    op.create_table(
        "observation_revisions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("original_observation_id", sa.UUID(), nullable=False),
        sa.Column("replacement_observation_id", sa.UUID(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("revised_by", sa.String(length=255), nullable=False),
        sa.Column(
            "metadata_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["original_observation_id"],
            ["metric_observations.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["replacement_observation_id"],
            ["metric_observations.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("replacement_observation_id"),
    )
    op.create_index(
        op.f("ix_observation_revisions_original_observation_id"),
        "observation_revisions",
        ["original_observation_id"],
        unique=False,
    )
    op.execute(
        """
        CREATE FUNCTION v2_reject_immutable_mutation()
        RETURNS trigger AS $$
        BEGIN
          RAISE EXCEPTION '% is append-only; insert a superseding record', TG_TABLE_NAME;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    for table in IMMUTABLE_TABLES:
        op.execute(
            f"""
            CREATE TRIGGER trg_{table}_immutable
            BEFORE UPDATE OR DELETE ON {table}
            FOR EACH ROW EXECUTE FUNCTION v2_reject_immutable_mutation();
            """
        )


def downgrade() -> None:
    for table in reversed(IMMUTABLE_TABLES):
        op.execute(f"DROP TRIGGER IF EXISTS trg_{table}_immutable ON {table}")
    op.execute("DROP FUNCTION IF EXISTS v2_reject_immutable_mutation()")
    op.drop_index(
        op.f("ix_observation_revisions_original_observation_id"),
        table_name="observation_revisions",
    )
    op.drop_table("observation_revisions")
