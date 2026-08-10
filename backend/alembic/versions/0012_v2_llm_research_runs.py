"""Add append-only LLM research plans and allowlisted tool actions.

Revision ID: 0012_v2_llm_research_runs
Revises: 0011_v2_schedule_source_guard
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0012_v2_llm_research_runs"
down_revision = "0011_v2_schedule_source_guard"
branch_labels = None
depends_on = None


def upgrade() -> None:
    action_type = postgresql.ENUM(
        "DISCOVER",
        "COLLECT",
        name="v2_research_action_type",
        create_type=False,
    )
    event_type = postgresql.ENUM(
        "PROPOSED",
        "AUTHORIZED",
        "STARTED",
        "COMPLETED",
        "QUEUED",
        "BLOCKED",
        "FAILED",
        name="v2_research_event_type",
        create_type=False,
    )
    action_type.create(op.get_bind(), checkfirst=True)
    event_type.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "research_runs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("source_pool_id", sa.UUID(), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("objective", sa.Text(), nullable=False),
        sa.Column("constraints", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("actor_label", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["source_pool_id"], ["source_pools.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_research_runs_source_pool_id"),
        "research_runs",
        ["source_pool_id"],
    )

    op.create_table(
        "research_plans",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("run_id", sa.UUID(), nullable=False),
        sa.Column("provider", sa.String(length=100), nullable=False),
        sa.Column("model", sa.String(length=255), nullable=False),
        sa.Column("prompt_version", sa.String(length=100), nullable=False),
        sa.Column("system_prompt_sha256", sa.String(length=64), nullable=False),
        sa.Column("input_hash", sa.String(length=64), nullable=False),
        sa.Column("input_manifest", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("output_hash", sa.String(length=64), nullable=False),
        sa.Column("plan", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("action_count", sa.Integer(), nullable=False),
        sa.Column("model_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "action_count >= 1 AND action_count <= 20",
            name="ck_research_plan_action_count",
        ),
        sa.CheckConstraint(
            "system_prompt_sha256 ~ '^[0-9a-f]{64}$'",
            name="ck_research_plan_prompt_hash",
        ),
        sa.CheckConstraint(
            "input_hash ~ '^[0-9a-f]{64}$'",
            name="ck_research_plan_input_hash",
        ),
        sa.CheckConstraint(
            "output_hash ~ '^[0-9a-f]{64}$'",
            name="ck_research_plan_output_hash",
        ),
        sa.ForeignKeyConstraint(["run_id"], ["research_runs.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id", "run_id", name="uq_research_plan_id_run"),
        sa.UniqueConstraint("run_id", name="uq_research_plans_run_id"),
    )
    op.create_index(op.f("ix_research_plans_run_id"), "research_plans", ["run_id"])

    op.create_table(
        "research_actions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("run_id", sa.UUID(), nullable=False),
        sa.Column("plan_id", sa.UUID(), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("action_type", action_type, nullable=False),
        sa.Column("specification", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("requires_authorization", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("ordinal >= 0", name="ck_research_action_ordinal"),
        sa.ForeignKeyConstraint(
            ["plan_id", "run_id"],
            ["research_plans.id", "research_plans.run_id"],
            name="fk_research_action_plan_run",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id", "run_id", name="uq_research_action_id_run"),
        sa.UniqueConstraint("plan_id", "ordinal", name="uq_research_action_plan_ordinal"),
    )
    op.create_index(op.f("ix_research_actions_plan_id"), "research_actions", ["plan_id"])
    op.create_index(op.f("ix_research_actions_run_id"), "research_actions", ["run_id"])

    op.create_table(
        "research_action_events",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("action_id", sa.UUID(), nullable=False),
        sa.Column("run_id", sa.UUID(), nullable=False),
        sa.Column("event_type", event_type, nullable=False),
        sa.Column("actor_label", sa.String(length=255), nullable=False),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("predecessor_id", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["action_id", "run_id"],
            ["research_actions.id", "research_actions.run_id"],
            name="fk_research_event_action_run",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["predecessor_id", "action_id", "run_id"],
            [
                "research_action_events.id",
                "research_action_events.action_id",
                "research_action_events.run_id",
            ],
            name="fk_research_event_same_action",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "id", "action_id", "run_id", name="uq_research_event_id_action_run"
        ),
        sa.UniqueConstraint("predecessor_id", name="uq_research_event_predecessor"),
    )
    op.create_index(
        op.f("ix_research_action_events_action_id"),
        "research_action_events",
        ["action_id"],
    )
    op.create_index(
        op.f("ix_research_action_events_run_id"),
        "research_action_events",
        ["run_id"],
    )
    op.create_index(
        "uq_research_event_root",
        "research_action_events",
        ["action_id"],
        unique=True,
        postgresql_where=sa.text("predecessor_id IS NULL"),
    )

    op.execute(
        """
        CREATE FUNCTION v2_validate_research_action_set()
        RETURNS trigger AS $$
        DECLARE
          target_plan uuid;
          expected_count integer;
          actual_count integer;
          minimum_ordinal integer;
          maximum_ordinal integer;
        BEGIN
          IF TG_TABLE_NAME = 'research_plans' THEN
            target_plan := NEW.id;
          ELSE
            target_plan := NEW.plan_id;
          END IF;
          SELECT action_count INTO expected_count
          FROM research_plans WHERE id = target_plan;
          SELECT count(*), min(ordinal), max(ordinal)
          INTO actual_count, minimum_ordinal, maximum_ordinal
          FROM research_actions WHERE plan_id = target_plan;
          IF expected_count IS NULL
             OR actual_count IS DISTINCT FROM expected_count
             OR minimum_ordinal IS DISTINCT FROM 0
             OR maximum_ordinal IS DISTINCT FROM expected_count - 1 THEN
            RAISE EXCEPTION 'research action set does not match frozen plan cardinality';
          END IF;
          RETURN NULL;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE CONSTRAINT TRIGGER trg_research_plan_action_set
        AFTER INSERT ON research_plans
        DEFERRABLE INITIALLY DEFERRED
        FOR EACH ROW EXECUTE FUNCTION v2_validate_research_action_set();
        """
    )
    op.execute(
        """
        CREATE CONSTRAINT TRIGGER trg_research_action_set
        AFTER INSERT ON research_actions
        DEFERRABLE INITIALLY DEFERRED
        FOR EACH ROW EXECUTE FUNCTION v2_validate_research_action_set();
        """
    )

    for table in (
        "research_runs",
        "research_plans",
        "research_actions",
        "research_action_events",
    ):
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
          IF EXISTS (SELECT 1 FROM research_runs)
             OR EXISTS (SELECT 1 FROM research_plans)
             OR EXISTS (SELECT 1 FROM research_actions)
             OR EXISTS (SELECT 1 FROM research_action_events) THEN
            RAISE EXCEPTION
              'downgrade would erase research history; use a disposable empty database';
          END IF;
        END
        $$;
        """
    )
    for table in (
        "research_action_events",
        "research_actions",
        "research_plans",
        "research_runs",
    ):
        op.execute(f"DROP TRIGGER trg_{table}_immutable ON {table}")
        op.execute(f"DROP TRIGGER trg_{table}_immutable_truncate ON {table}")
    op.execute("DROP TRIGGER trg_research_action_set ON research_actions")
    op.execute("DROP TRIGGER trg_research_plan_action_set ON research_plans")
    op.execute("DROP FUNCTION v2_validate_research_action_set()")
    op.drop_index("uq_research_event_root", table_name="research_action_events")
    op.drop_index(
        op.f("ix_research_action_events_run_id"),
        table_name="research_action_events",
    )
    op.drop_index(
        op.f("ix_research_action_events_action_id"),
        table_name="research_action_events",
    )
    op.drop_table("research_action_events")
    op.drop_index(op.f("ix_research_actions_run_id"), table_name="research_actions")
    op.drop_index(op.f("ix_research_actions_plan_id"), table_name="research_actions")
    op.drop_table("research_actions")
    op.drop_index(op.f("ix_research_plans_run_id"), table_name="research_plans")
    op.drop_table("research_plans")
    op.drop_index(op.f("ix_research_runs_source_pool_id"), table_name="research_runs")
    op.drop_table("research_runs")
    sa.Enum(name="v2_research_event_type").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="v2_research_action_type").drop(op.get_bind(), checkfirst=True)
