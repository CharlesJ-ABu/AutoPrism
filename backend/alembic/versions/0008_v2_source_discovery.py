"""Add immutable, credential-free source discovery history.

Revision ID: 0008_v2_source_discovery
Revises: 0007_v2_numeric_conversion
"""

from alembic import op
import sqlalchemy as sa


revision = "0008_v2_source_discovery"
down_revision = "0007_v2_numeric_conversion"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "source_discovery_runs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("pool_id", sa.UUID(), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("provider_config_hash", sa.String(length=64), nullable=False),
        sa.Column("result_count", sa.Integer(), nullable=False),
        sa.Column("result_hash", sa.String(length=64), nullable=False),
        sa.Column("requested_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "provider = 'google-programmable-search-v1'",
            name="ck_source_discovery_provider",
        ),
        sa.CheckConstraint(
            "result_count >= 0 AND result_count <= 10",
            name="ck_source_discovery_result_count",
        ),
        sa.CheckConstraint(
            "provider_config_hash ~ '^[0-9a-f]{64}$'",
            name="ck_source_discovery_provider_hash",
        ),
        sa.CheckConstraint(
            "result_hash ~ '^[0-9a-f]{64}$'",
            name="ck_source_discovery_result_hash",
        ),
        sa.ForeignKeyConstraint(
            ["pool_id"], ["source_pools.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_source_discovery_runs_pool_id"),
        "source_discovery_runs",
        ["pool_id"],
    )
    op.create_table(
        "source_discovery_candidates",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("run_id", sa.UUID(), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("url_sha256", sa.String(length=64), nullable=False),
        sa.Column("display_host", sa.String(length=500), nullable=False),
        sa.Column("snippet", sa.Text(), nullable=False),
        sa.Column("mime_type", sa.String(length=255), nullable=True),
        sa.Column("suggested_kind", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "ordinal >= 0", name="ck_source_discovery_candidate_ordinal"
        ),
        sa.CheckConstraint(
            "suggested_kind IN ('html', 'pdf', 'csv', 'xlsx', 'rss')",
            name="ck_source_discovery_candidate_kind",
        ),
        sa.CheckConstraint(
            "url_sha256 ~ '^[0-9a-f]{64}$'",
            name="ck_source_discovery_candidate_url_hash",
        ),
        sa.ForeignKeyConstraint(
            ["run_id"], ["source_discovery_runs.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "run_id", "ordinal", name="uq_source_discovery_candidate_ordinal"
        ),
        sa.UniqueConstraint(
            "run_id", "url_sha256", name="uq_source_discovery_candidate_url"
        ),
    )
    op.create_index(
        op.f("ix_source_discovery_candidates_run_id"),
        "source_discovery_candidates",
        ["run_id"],
    )

    for table in ("source_discovery_runs", "source_discovery_candidates"):
        op.execute(
            f"""
            CREATE TRIGGER trg_{table}_immutable
            BEFORE UPDATE OR DELETE ON {table}
            FOR EACH ROW EXECUTE FUNCTION v2_reject_immutable_mutation();
            """
        )
        op.execute(
            f"""
            CREATE TRIGGER trg_{table}_immutable_truncate
            BEFORE TRUNCATE ON {table}
            FOR EACH STATEMENT EXECUTE FUNCTION v2_reject_immutable_mutation();
            """
        )


def downgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
          IF EXISTS (SELECT 1 FROM source_discovery_runs)
             OR EXISTS (SELECT 1 FROM source_discovery_candidates) THEN
            RAISE EXCEPTION
              'downgrade would erase source discovery history; use a disposable empty database';
          END IF;
        END
        $$;
        """
    )
    for table in ("source_discovery_candidates", "source_discovery_runs"):
        op.execute(f"DROP TRIGGER trg_{table}_immutable ON {table}")
        op.execute(f"DROP TRIGGER trg_{table}_immutable_truncate ON {table}")
    op.drop_index(
        op.f("ix_source_discovery_candidates_run_id"),
        table_name="source_discovery_candidates",
    )
    op.drop_table("source_discovery_candidates")
    op.drop_index(
        op.f("ix_source_discovery_runs_pool_id"),
        table_name="source_discovery_runs",
    )
    op.drop_table("source_discovery_runs")
