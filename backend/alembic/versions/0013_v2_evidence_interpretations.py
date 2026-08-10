"""Add append-only evidence-bound model interpretations.

Revision ID: 0013_v2_evidence_interpretations
Revises: 0012_v2_llm_research_runs
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0013_v2_evidence_interpretations"
down_revision = "0012_v2_llm_research_runs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "evidence_interpretations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("provider", sa.String(length=100), nullable=False),
        sa.Column("model", sa.String(length=255), nullable=False),
        sa.Column("prompt_version", sa.String(length=100), nullable=False),
        sa.Column("system_prompt_sha256", sa.String(length=64), nullable=False),
        sa.Column("input_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "input_manifest",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("output_hash", sa.String(length=64), nullable=False),
        sa.Column("output", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("input_count", sa.Integer(), nullable=False),
        sa.Column(
            "model_metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("created_by", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "input_count >= 1 AND input_count <= 100",
            name="ck_evidence_interpretation_input_count",
        ),
        sa.CheckConstraint(
            "system_prompt_sha256 ~ '^[0-9a-f]{64}$'",
            name="ck_evidence_interpretation_prompt_hash",
        ),
        sa.CheckConstraint(
            "input_hash ~ '^[0-9a-f]{64}$'",
            name="ck_evidence_interpretation_input_hash",
        ),
        sa.CheckConstraint(
            "output_hash ~ '^[0-9a-f]{64}$'",
            name="ck_evidence_interpretation_output_hash",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "evidence_interpretation_inputs",
        sa.Column("interpretation_id", sa.UUID(), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("observation_id", sa.UUID(), nullable=False),
        sa.Column("trust_assessment_id", sa.UUID(), nullable=False),
        sa.CheckConstraint(
            "ordinal >= 0",
            name="ck_evidence_interpretation_input_ordinal",
        ),
        sa.ForeignKeyConstraint(
            ["interpretation_id"],
            ["evidence_interpretations.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["observation_id"],
            ["metric_observations.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["trust_assessment_id"],
            ["trust_assessments.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("interpretation_id", "ordinal"),
        sa.UniqueConstraint(
            "interpretation_id",
            "observation_id",
            name="uq_evidence_interpretation_observation",
        ),
    )
    op.create_index(
        op.f("ix_evidence_interpretation_inputs_observation_id"),
        "evidence_interpretation_inputs",
        ["observation_id"],
    )
    op.create_index(
        op.f("ix_evidence_interpretation_inputs_trust_assessment_id"),
        "evidence_interpretation_inputs",
        ["trust_assessment_id"],
    )

    op.execute(
        """
        CREATE FUNCTION v2_validate_interpretation_input_set()
        RETURNS trigger AS $$
        DECLARE
          target_interpretation uuid;
          expected_count integer;
          actual_count integer;
          minimum_ordinal integer;
          maximum_ordinal integer;
          invalid_pairs integer;
        BEGIN
          IF TG_TABLE_NAME = 'evidence_interpretations' THEN
            target_interpretation := NEW.id;
          ELSE
            target_interpretation := NEW.interpretation_id;
          END IF;
          SELECT input_count INTO expected_count
          FROM evidence_interpretations WHERE id = target_interpretation;
          SELECT count(*), min(ordinal), max(ordinal)
          INTO actual_count, minimum_ordinal, maximum_ordinal
          FROM evidence_interpretation_inputs
          WHERE interpretation_id = target_interpretation;
          SELECT count(*) INTO invalid_pairs
          FROM evidence_interpretation_inputs AS input
          JOIN trust_assessments AS assessment
            ON assessment.id = input.trust_assessment_id
          WHERE input.interpretation_id = target_interpretation
            AND assessment.observation_id IS DISTINCT FROM input.observation_id;
          IF expected_count IS NULL
             OR actual_count IS DISTINCT FROM expected_count
             OR minimum_ordinal IS DISTINCT FROM 0
             OR maximum_ordinal IS DISTINCT FROM expected_count - 1
             OR invalid_pairs IS DISTINCT FROM 0 THEN
            RAISE EXCEPTION 'interpretation input set does not match frozen contract';
          END IF;
          RETURN NULL;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE CONSTRAINT TRIGGER trg_evidence_interpretation_input_set
        AFTER INSERT ON evidence_interpretations
        DEFERRABLE INITIALLY DEFERRED
        FOR EACH ROW EXECUTE FUNCTION v2_validate_interpretation_input_set();
        """
    )
    op.execute(
        """
        CREATE CONSTRAINT TRIGGER trg_evidence_interpretation_input_row
        AFTER INSERT ON evidence_interpretation_inputs
        DEFERRABLE INITIALLY DEFERRED
        FOR EACH ROW EXECUTE FUNCTION v2_validate_interpretation_input_set();
        """
    )

    for table in ("evidence_interpretations", "evidence_interpretation_inputs"):
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
          IF EXISTS (SELECT 1 FROM evidence_interpretations)
             OR EXISTS (SELECT 1 FROM evidence_interpretation_inputs) THEN
            RAISE EXCEPTION
              'downgrade would erase interpretation history; use a disposable empty database';
          END IF;
        END
        $$;
        """
    )
    for table in ("evidence_interpretation_inputs", "evidence_interpretations"):
        op.execute(f"DROP TRIGGER trg_{table}_immutable ON {table}")
        op.execute(f"DROP TRIGGER trg_{table}_immutable_truncate ON {table}")
    op.execute(
        "DROP TRIGGER trg_evidence_interpretation_input_row "
        "ON evidence_interpretation_inputs"
    )
    op.execute(
        "DROP TRIGGER trg_evidence_interpretation_input_set "
        "ON evidence_interpretations"
    )
    op.execute("DROP FUNCTION v2_validate_interpretation_input_set()")
    op.drop_index(
        op.f("ix_evidence_interpretation_inputs_trust_assessment_id"),
        table_name="evidence_interpretation_inputs",
    )
    op.drop_index(
        op.f("ix_evidence_interpretation_inputs_observation_id"),
        table_name="evidence_interpretation_inputs",
    )
    op.drop_table("evidence_interpretation_inputs")
    op.drop_table("evidence_interpretations")
