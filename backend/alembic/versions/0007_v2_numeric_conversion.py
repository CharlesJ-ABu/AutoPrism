"""Add frozen numeric uncertainty and deterministic conversion lineage.

Revision ID: 0007_v2_numeric_conversion
Revises: 0006_v2_trusted_insight_map
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0007_v2_numeric_conversion"
down_revision = "0006_v2_trusted_insight_map"
branch_labels = None
depends_on = None


def upgrade() -> None:
    uncertainty_state = postgresql.ENUM(
        "EXACT",
        "BOUNDED",
        "UNKNOWN",
        name="v2_uncertainty_state",
        create_type=False,
    )
    conversion_kind = postgresql.ENUM(
        "UNIT", "CURRENCY", name="v2_conversion_kind", create_type=False
    )
    uncertainty_state.create(op.get_bind(), checkfirst=True)
    conversion_kind.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "observation_numeric_values",
        sa.Column("observation_id", sa.UUID(), nullable=False),
        sa.Column("value", sa.Numeric(), nullable=False),
        sa.Column(
            "uncertainty_kind",
            uncertainty_state,
            nullable=False,
        ),
        sa.Column("absolute_error", sa.Numeric(), nullable=True),
        sa.Column("uncertainty_basis", postgresql.JSONB(), nullable=False),
        sa.Column("evidence_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "(uncertainty_kind = 'EXACT' AND absolute_error = 0) "
            "OR (uncertainty_kind = 'BOUNDED' AND absolute_error >= 0) "
            "OR (uncertainty_kind = 'UNKNOWN' AND absolute_error IS NULL)",
            name="ck_observation_numeric_uncertainty",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(uncertainty_basis) = 'object'",
            name="ck_observation_numeric_basis_object",
        ),
        sa.CheckConstraint(
            "(uncertainty_kind = 'BOUNDED' AND evidence_count > 0) OR "
            "(uncertainty_kind IN ('EXACT', 'UNKNOWN') AND evidence_count = 0)",
            name="ck_observation_numeric_evidence_count",
        ),
        sa.ForeignKeyConstraint(
            ["observation_id"], ["metric_observations.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("observation_id"),
    )
    op.create_table(
        "observation_numeric_evidence",
        sa.Column("observation_id", sa.UUID(), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("evidence_fragment_id", sa.UUID(), nullable=False),
        sa.Column("claim_key", sa.String(length=255), nullable=False),
        sa.Column("field_path", sa.String(length=500), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "ordinal >= 0", name="ck_observation_numeric_evidence_ordinal"
        ),
        sa.ForeignKeyConstraint(
            ["observation_id"],
            ["observation_numeric_values.observation_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["evidence_fragment_id"],
            ["evidence_fragments.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("observation_id", "ordinal"),
        sa.UniqueConstraint(
            "observation_id",
            "evidence_fragment_id",
            "field_path",
            name="uq_observation_numeric_evidence_claim",
        ),
    )

    op.create_table(
        "conversion_runs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("output_observation_id", sa.UUID(), nullable=False),
        sa.Column("input_observation_id", sa.UUID(), nullable=False),
        sa.Column("input_trust_assessment_id", sa.UUID(), nullable=False),
        sa.Column("kind", conversion_kind, nullable=False),
        sa.Column("fx_rate_observation_id", sa.UUID(), nullable=True),
        sa.Column("fx_rate_trust_assessment_id", sa.UUID(), nullable=True),
        sa.Column("registry_version", sa.String(length=100), nullable=False),
        sa.Column("engine_version", sa.String(length=100), nullable=False),
        sa.Column("plan", postgresql.JSONB(), nullable=False),
        sa.Column("input_snapshot", postgresql.JSONB(), nullable=False),
        sa.Column("result", postgresql.JSONB(), nullable=False),
        sa.Column("replay_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "replay_hash ~ '^[0-9a-f]{64}$'",
            name="ck_conversion_run_replay_hash_hex",
        ),
        sa.CheckConstraint(
            "(kind = 'UNIT' AND fx_rate_observation_id IS NULL "
            "AND fx_rate_trust_assessment_id IS NULL) OR "
            "(kind = 'CURRENCY' AND fx_rate_observation_id IS NOT NULL "
            "AND fx_rate_trust_assessment_id IS NOT NULL)",
            name="ck_conversion_run_kind_inputs",
        ),
        sa.ForeignKeyConstraint(
            ["output_observation_id"],
            ["metric_observations.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["input_observation_id"],
            ["metric_observations.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["input_trust_assessment_id"],
            ["trust_assessments.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["fx_rate_observation_id"],
            ["metric_observations.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["fx_rate_trust_assessment_id"],
            ["trust_assessments.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "output_observation_id", name="uq_conversion_run_output_observation"
        ),
    )
    op.create_index(
        op.f("ix_conversion_runs_input_observation_id"),
        "conversion_runs",
        ["input_observation_id"],
    )
    op.create_table(
        "calculation_run_inputs",
        sa.Column("calculation_run_id", sa.UUID(), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("observation_id", sa.UUID(), nullable=False),
        sa.Column("trust_assessment_id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "ordinal >= 0", name="ck_calculation_run_input_ordinal"
        ),
        sa.ForeignKeyConstraint(
            ["calculation_run_id"],
            ["calculation_runs.id"],
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
        sa.PrimaryKeyConstraint("calculation_run_id", "ordinal"),
        sa.UniqueConstraint(
            "calculation_run_id",
            "observation_id",
            name="uq_calculation_run_input_observation",
        ),
    )

    op.add_column(
        "trust_assessments",
        sa.Column("conversion_run_id", sa.UUID(), nullable=True),
    )
    op.create_foreign_key(
        "fk_trust_assessment_conversion_run",
        "trust_assessments",
        "conversion_runs",
        ["conversion_run_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    # Extend the frozen-origin invariant. Existing triggers call this function,
    # and the new conversion trigger closes the append-after-commit path.
    op.execute(
        """
        CREATE OR REPLACE FUNCTION v2_validate_observation_origin_exclusive()
        RETURNS trigger AS $$
        DECLARE
          target_id uuid;
          origin_count integer;
        BEGIN
          IF TG_TABLE_NAME = 'observation_extraction_links' THEN
            target_id := NEW.observation_id;
          ELSIF TG_TABLE_NAME = 'observation_revisions' THEN
            target_id := NEW.replacement_observation_id;
          ELSE
            target_id := NEW.output_observation_id;
          END IF;
          SELECT
            (SELECT count(*) FROM observation_extraction_links
             WHERE observation_id = target_id)
            + (SELECT count(*) FROM observation_revisions
               WHERE replacement_observation_id = target_id)
            + (SELECT count(*) FROM calculation_runs
               WHERE output_observation_id = target_id)
            + (SELECT count(*) FROM conversion_runs
               WHERE output_observation_id = target_id)
          INTO origin_count;
          IF origin_count > 1 THEN
            RAISE EXCEPTION 'observation % has multiple origin records', target_id;
          END IF;
          RETURN NULL;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE CONSTRAINT TRIGGER trg_conversion_runs_origin_exclusive
        AFTER INSERT OR UPDATE ON conversion_runs
        DEFERRABLE INITIALLY DEFERRED
        FOR EACH ROW EXECUTE FUNCTION v2_validate_observation_origin_exclusive();
        """
    )

    op.execute(
        """
        CREATE FUNCTION v2_validate_observation_numeric_evidence()
        RETURNS trigger AS $$
        DECLARE
          target_id uuid;
          numeric_value observation_numeric_values%ROWTYPE;
          link_count integer;
          minimum_ordinal integer;
          maximum_ordinal integer;
        BEGIN
          target_id := NEW.observation_id;
          SELECT * INTO STRICT numeric_value
          FROM observation_numeric_values
          WHERE observation_id = target_id;
          SELECT count(*), min(ordinal), max(ordinal)
          INTO link_count, minimum_ordinal, maximum_ordinal
          FROM observation_numeric_evidence
          WHERE observation_id = target_id;
          IF link_count <> numeric_value.evidence_count THEN
            RAISE EXCEPTION 'observation % numeric evidence is incomplete', target_id;
          END IF;
          IF link_count > 0
             AND (minimum_ordinal <> 0 OR maximum_ordinal <> link_count - 1) THEN
            RAISE EXCEPTION 'observation % numeric evidence ordinals are incomplete', target_id;
          END IF;
          RETURN NULL;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    for table in ("observation_numeric_values", "observation_numeric_evidence"):
        op.execute(
            f"""
            CREATE CONSTRAINT TRIGGER trg_{table}_evidence_complete
            AFTER INSERT OR UPDATE ON {table}
            DEFERRABLE INITIALLY DEFERRED
            FOR EACH ROW EXECUTE FUNCTION v2_validate_observation_numeric_evidence();
            """
        )

    op.execute(
        """
        CREATE FUNCTION v2_validate_calculation_run_inputs()
        RETURNS trigger AS $$
        DECLARE
          target_id uuid;
          run calculation_runs%ROWTYPE;
          input_count integer;
          minimum_ordinal integer;
          maximum_ordinal integer;
        BEGIN
          IF TG_TABLE_NAME = 'calculation_runs' THEN
            target_id := NEW.id;
          ELSE
            target_id := NEW.calculation_run_id;
          END IF;
          SELECT * INTO STRICT run FROM calculation_runs WHERE id = target_id;
          IF run.engine_version <> 'decimal-v2-bounded' THEN
            RETURN NULL;
          END IF;
          IF jsonb_typeof(run.input_observation_ids) <> 'array' THEN
            RAISE EXCEPTION 'calculation % input header is invalid', target_id;
          END IF;
          SELECT count(*), min(ordinal), max(ordinal)
          INTO input_count, minimum_ordinal, maximum_ordinal
          FROM calculation_run_inputs WHERE calculation_run_id = target_id;
          IF input_count <> jsonb_array_length(run.input_observation_ids)
             OR input_count = 0 OR minimum_ordinal <> 0
             OR maximum_ordinal <> input_count - 1 THEN
            RAISE EXCEPTION 'calculation % input set is incomplete', target_id;
          END IF;
          IF EXISTS (
            SELECT 1
            FROM calculation_run_inputs AS input
            LEFT JOIN trust_assessments AS assessment
              ON assessment.id = input.trust_assessment_id
            WHERE input.calculation_run_id = target_id
              AND (
                run.input_observation_ids ->> input.ordinal
                  IS DISTINCT FROM input.observation_id::text
                OR assessment.observation_id IS DISTINCT FROM input.observation_id
              )
          ) THEN
            RAISE EXCEPTION 'calculation % input lineage is inconsistent', target_id;
          END IF;
          RETURN NULL;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    for table in ("calculation_runs", "calculation_run_inputs"):
        op.execute(
            f"""
            CREATE CONSTRAINT TRIGGER trg_{table}_inputs_complete
            AFTER INSERT OR UPDATE ON {table}
            DEFERRABLE INITIALLY DEFERRED
            FOR EACH ROW EXECUTE FUNCTION v2_validate_calculation_run_inputs();
            """
        )

    for table in (
        "observation_numeric_values",
        "observation_numeric_evidence",
        "calculation_run_inputs",
        "conversion_runs",
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
          IF EXISTS (SELECT 1 FROM observation_numeric_values)
             OR EXISTS (SELECT 1 FROM observation_numeric_evidence)
             OR EXISTS (SELECT 1 FROM calculation_run_inputs)
             OR EXISTS (SELECT 1 FROM conversion_runs)
             OR EXISTS (
               SELECT 1 FROM trust_assessments WHERE conversion_run_id IS NOT NULL
             ) THEN
            RAISE EXCEPTION
              'downgrade would erase frozen numeric or conversion history; use a disposable empty database';
          END IF;
        END
        $$;
        """
    )
    op.execute(
        "DROP TRIGGER trg_conversion_runs_origin_exclusive ON conversion_runs"
    )
    for table in ("calculation_run_inputs", "calculation_runs"):
        op.execute(f"DROP TRIGGER trg_{table}_inputs_complete ON {table}")
    op.execute("DROP FUNCTION v2_validate_calculation_run_inputs()")
    for table in ("observation_numeric_evidence", "observation_numeric_values"):
        op.execute(f"DROP TRIGGER trg_{table}_evidence_complete ON {table}")
    op.execute("DROP FUNCTION v2_validate_observation_numeric_evidence()")
    for table in (
        "conversion_runs",
        "observation_numeric_evidence",
        "calculation_run_inputs",
        "observation_numeric_values",
    ):
        op.execute(f"DROP TRIGGER trg_{table}_immutable ON {table}")
        op.execute(f"DROP TRIGGER trg_{table}_immutable_truncate ON {table}")

    op.drop_constraint(
        "fk_trust_assessment_conversion_run",
        "trust_assessments",
        type_="foreignkey",
    )
    op.drop_column("trust_assessments", "conversion_run_id")
    op.drop_index(
        op.f("ix_conversion_runs_input_observation_id"),
        table_name="conversion_runs",
    )
    op.drop_table("conversion_runs")
    op.drop_table("calculation_run_inputs")
    op.drop_table("observation_numeric_evidence")
    op.drop_table("observation_numeric_values")

    # Restore the exact 0005 origin rule for a disposable downgrade path.
    op.execute(
        """
        CREATE OR REPLACE FUNCTION v2_validate_observation_origin_exclusive()
        RETURNS trigger AS $$
        DECLARE
          target_id uuid;
          origin_count integer;
        BEGIN
          IF TG_TABLE_NAME = 'observation_extraction_links' THEN
            target_id := NEW.observation_id;
          ELSIF TG_TABLE_NAME = 'observation_revisions' THEN
            target_id := NEW.replacement_observation_id;
          ELSE
            target_id := NEW.output_observation_id;
          END IF;
          SELECT
            (SELECT count(*) FROM observation_extraction_links
             WHERE observation_id = target_id)
            + (SELECT count(*) FROM observation_revisions
               WHERE replacement_observation_id = target_id)
            + (SELECT count(*) FROM calculation_runs
               WHERE output_observation_id = target_id)
          INTO origin_count;
          IF origin_count > 1 THEN
            RAISE EXCEPTION 'observation % has multiple origin records', target_id;
          END IF;
          RETURN NULL;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    postgresql.ENUM(name="v2_conversion_kind").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="v2_uncertainty_state").drop(op.get_bind(), checkfirst=True)
