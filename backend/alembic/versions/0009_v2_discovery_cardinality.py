"""Freeze source discovery candidate-set cardinality.

Revision ID: 0009_v2_discovery_cardinality
Revises: 0008_v2_source_discovery
"""

from alembic import op


revision = "0009_v2_discovery_cardinality"
down_revision = "0008_v2_source_discovery"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE OR REPLACE FUNCTION v2_validate_source_discovery_cardinality()
        RETURNS trigger AS $$
        DECLARE
          target_run_id uuid;
          expected_count integer;
          actual_count integer;
          minimum_ordinal integer;
          maximum_ordinal integer;
        BEGIN
          IF TG_TABLE_NAME = 'source_discovery_runs' THEN
            target_run_id := NEW.id;
          ELSE
            target_run_id := NEW.run_id;
          END IF;

          SELECT result_count
          INTO expected_count
          FROM source_discovery_runs
          WHERE id = target_run_id;

          SELECT count(*), min(ordinal), max(ordinal)
          INTO actual_count, minimum_ordinal, maximum_ordinal
          FROM source_discovery_candidates
          WHERE run_id = target_run_id;

          IF expected_count IS NULL
             OR actual_count <> expected_count
             OR (expected_count > 0 AND (
               minimum_ordinal <> 0 OR maximum_ordinal <> expected_count - 1
             )) THEN
            RAISE EXCEPTION
              'source discovery candidate set must match its frozen run header';
          END IF;
          RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE CONSTRAINT TRIGGER trg_source_discovery_run_cardinality
        AFTER INSERT ON source_discovery_runs
        DEFERRABLE INITIALLY DEFERRED
        FOR EACH ROW EXECUTE FUNCTION v2_validate_source_discovery_cardinality();
        """
    )
    op.execute(
        """
        CREATE CONSTRAINT TRIGGER trg_source_discovery_candidate_cardinality
        AFTER INSERT ON source_discovery_candidates
        DEFERRABLE INITIALLY DEFERRED
        FOR EACH ROW EXECUTE FUNCTION v2_validate_source_discovery_cardinality();
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
          IF EXISTS (
            SELECT 1
            FROM source_discovery_runs AS run
            LEFT JOIN source_discovery_candidates AS candidate
              ON candidate.run_id = run.id
            GROUP BY run.id, run.result_count
            HAVING count(candidate.id) <> run.result_count
               OR (run.result_count > 0 AND (
                 min(candidate.ordinal) <> 0
                 OR max(candidate.ordinal) <> run.result_count - 1
               ))
          ) THEN
            RAISE EXCEPTION
              'existing source discovery candidate set violates frozen cardinality';
          END IF;
        END
        $$;
        """
    )


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER trg_source_discovery_candidate_cardinality "
        "ON source_discovery_candidates"
    )
    op.execute(
        "DROP TRIGGER trg_source_discovery_run_cardinality "
        "ON source_discovery_runs"
    )
    op.execute("DROP FUNCTION v2_validate_source_discovery_cardinality()")
