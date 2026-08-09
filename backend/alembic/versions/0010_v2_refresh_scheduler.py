"""Add append-only refresh schedules and dispatch history.

Revision ID: 0010_v2_refresh_scheduler
Revises: 0009_v2_discovery_cardinality
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0010_v2_refresh_scheduler"
down_revision = "0009_v2_discovery_cardinality"
branch_labels = None
depends_on = None


def upgrade() -> None:
    schedule_mode = postgresql.ENUM(
        "MANUAL",
        "INTERVAL",
        name="v2_refresh_schedule_mode",
        create_type=False,
    )
    dispatch_outcome = postgresql.ENUM(
        "QUEUED",
        "SKIPPED",
        "FAILED",
        name="v2_schedule_dispatch_outcome",
        create_type=False,
    )
    schedule_mode.create(op.get_bind(), checkfirst=True)
    dispatch_outcome.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "source_refresh_schedules",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("source_definition_id", sa.UUID(), nullable=False),
        sa.Column("mode", schedule_mode, nullable=False),
        sa.Column("interval_seconds", sa.Integer(), nullable=True),
        sa.Column("authorization_attested", sa.Boolean(), nullable=False),
        sa.Column("actor_label", sa.String(length=255), nullable=False),
        sa.Column("supersedes_id", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "(mode = 'MANUAL' AND interval_seconds IS NULL) OR "
            "(mode = 'INTERVAL' AND interval_seconds BETWEEN 900 AND 2678400 "
            "AND authorization_attested)",
            name="ck_source_refresh_schedule_contract",
        ),
        sa.ForeignKeyConstraint(
            ["source_definition_id"],
            ["source_definitions.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "id",
            "source_definition_id",
            name="uq_source_refresh_schedule_id_source",
        ),
        sa.UniqueConstraint(
            "supersedes_id", name="uq_source_refresh_schedule_supersedes"
        ),
        sa.ForeignKeyConstraint(
            ["supersedes_id", "source_definition_id"],
            [
                "source_refresh_schedules.id",
                "source_refresh_schedules.source_definition_id",
            ],
            name="fk_source_refresh_schedule_same_source",
            ondelete="RESTRICT",
        ),
    )
    op.create_index(
        op.f("ix_source_refresh_schedules_source_definition_id"),
        "source_refresh_schedules",
        ["source_definition_id"],
    )
    op.create_index(
        "uq_source_refresh_schedule_root",
        "source_refresh_schedules",
        ["source_definition_id"],
        unique=True,
        postgresql_where=sa.text("supersedes_id IS NULL"),
    )

    op.create_table(
        "schedule_dispatches",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("schedule_id", sa.UUID(), nullable=False),
        sa.Column("source_definition_id", sa.UUID(), nullable=False),
        sa.Column("bucket_key", sa.String(length=255), nullable=False),
        sa.Column("due_at", sa.DateTime(), nullable=False),
        sa.Column("observed_at", sa.DateTime(), nullable=False),
        sa.Column("outcome", dispatch_outcome, nullable=False),
        sa.Column("reason_code", sa.String(length=100), nullable=False),
        sa.Column("collection_job_id", sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(
            ["schedule_id"], ["source_refresh_schedules.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["source_definition_id"],
            ["source_definitions.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["collection_job_id"], ["collection_jobs.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("bucket_key", name="uq_schedule_dispatch_bucket"),
    )
    op.create_index(
        op.f("ix_schedule_dispatches_schedule_id"),
        "schedule_dispatches",
        ["schedule_id"],
    )
    op.create_index(
        op.f("ix_schedule_dispatches_source_definition_id"),
        "schedule_dispatches",
        ["source_definition_id"],
    )

    for table in ("source_refresh_schedules", "schedule_dispatches"):
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
          IF EXISTS (SELECT 1 FROM source_refresh_schedules)
             OR EXISTS (SELECT 1 FROM schedule_dispatches) THEN
            RAISE EXCEPTION
              'downgrade would erase refresh schedule history; use a disposable empty database';
          END IF;
        END
        $$;
        """
    )
    for table in ("schedule_dispatches", "source_refresh_schedules"):
        op.execute(f"DROP TRIGGER trg_{table}_immutable ON {table}")
        op.execute(f"DROP TRIGGER trg_{table}_immutable_truncate ON {table}")
    op.drop_index(
        op.f("ix_schedule_dispatches_source_definition_id"),
        table_name="schedule_dispatches",
    )
    op.drop_index(
        op.f("ix_schedule_dispatches_schedule_id"),
        table_name="schedule_dispatches",
    )
    op.drop_table("schedule_dispatches")
    op.drop_index(
        "uq_source_refresh_schedule_root",
        table_name="source_refresh_schedules",
    )
    op.drop_index(
        op.f("ix_source_refresh_schedules_source_definition_id"),
        table_name="source_refresh_schedules",
    )
    op.drop_table("source_refresh_schedules")
    sa.Enum(name="v2_schedule_dispatch_outcome").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="v2_refresh_schedule_mode").drop(op.get_bind(), checkfirst=True)
