"""Add frozen multi-evidence sets and exact extraction-run lineage.

Revision ID: 0005_v2_observation_lineage
Revises: 0004_v2_trust_assessments_l2
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0005_v2_observation_lineage"
down_revision = "0004_v2_trust_assessments_l2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Historical V1-compatible databases created this column through the live
    # ORM before its server default was frozen. Align only the schema default;
    # no rows are rewritten and the existing non-null locator values remain.
    op.alter_column(
        "intelligence_info_evidence",
        "locator",
        existing_type=postgresql.JSONB(),
        existing_nullable=False,
        server_default=sa.text("'{}'::jsonb"),
    )
    # Keep the historical snapshot stable while the conservative backfill and
    # deferred integrity triggers are installed. Deployment also stops the web
    # and worker processes, but the database lock is the final fail-closed guard
    # against an old writer racing this migration.
    op.execute(
        """
        LOCK TABLE
          metric_observations,
          observation_revisions,
          calculation_runs,
          extraction_runs,
          evidence_fragments
        IN SHARE ROW EXCLUSIVE MODE
        """
    )
    op.create_table(
        "observation_evidence_sets",
        sa.Column("observation_id", sa.UUID(), nullable=False),
        sa.Column("citation_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "citation_count > 0",
            name="ck_observation_evidence_set_count",
        ),
        sa.ForeignKeyConstraint(
            ["observation_id"],
            ["metric_observations.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("observation_id"),
    )
    op.create_table(
        "observation_evidence_links",
        sa.Column("observation_id", sa.UUID(), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("evidence_fragment_id", sa.UUID(), nullable=False),
        sa.Column("role", sa.String(length=50), nullable=False),
        sa.Column("claim_key", sa.String(length=255), nullable=False),
        sa.Column("field_path", sa.String(length=500), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "ordinal >= 0",
            name="ck_observation_evidence_ordinal",
        ),
        sa.CheckConstraint(
            "role IN ('primary', 'supporting', 'dimension', 'calculation_input')",
            name="ck_observation_evidence_role",
        ),
        sa.ForeignKeyConstraint(
            ["evidence_fragment_id"],
            ["evidence_fragments.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["observation_id"],
            ["observation_evidence_sets.observation_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("observation_id", "ordinal"),
        sa.UniqueConstraint(
            "observation_id",
            "evidence_fragment_id",
            "field_path",
            name="uq_observation_evidence_claim_fragment",
        ),
    )
    op.create_index(
        op.f("ix_observation_evidence_links_evidence_fragment_id"),
        "observation_evidence_links",
        ["evidence_fragment_id"],
    )
    op.create_index(
        "uq_observation_evidence_primary",
        "observation_evidence_links",
        ["observation_id"],
        unique=True,
        postgresql_where="role = 'primary'",
    )
    op.create_table(
        "extraction_run_input_sets",
        sa.Column("extraction_run_id", sa.UUID(), nullable=False),
        sa.Column("input_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "input_count >= 0",
            name="ck_extraction_run_input_set_count",
        ),
        sa.ForeignKeyConstraint(
            ["extraction_run_id"],
            ["extraction_runs.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("extraction_run_id"),
    )
    op.create_table(
        "extraction_run_inputs",
        sa.Column("extraction_run_id", sa.UUID(), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("evidence_fragment_id", sa.UUID(), nullable=False),
        sa.Column("extracted_text_sha256", sa.String(length=64), nullable=False),
        sa.Column("manifest_entry_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "ordinal >= 0",
            name="ck_extraction_run_input_ordinal",
        ),
        sa.CheckConstraint(
            "extracted_text_sha256 ~ '^[0-9a-f]{64}$'",
            name="ck_extraction_run_input_text_hash_hex",
        ),
        sa.CheckConstraint(
            "manifest_entry_hash ~ '^[0-9a-f]{64}$'",
            name="ck_extraction_run_input_entry_hash_hex",
        ),
        sa.ForeignKeyConstraint(
            ["evidence_fragment_id"],
            ["evidence_fragments.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["extraction_run_id"],
            ["extraction_run_input_sets.extraction_run_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("extraction_run_id", "ordinal"),
        sa.UniqueConstraint(
            "extraction_run_id",
            "evidence_fragment_id",
            name="uq_extraction_run_input_fragment",
        ),
    )
    op.create_index(
        op.f("ix_extraction_run_inputs_evidence_fragment_id"),
        "extraction_run_inputs",
        ["evidence_fragment_id"],
    )
    op.create_table(
        "observation_extraction_links",
        sa.Column("observation_id", sa.UUID(), nullable=False),
        sa.Column("extraction_run_id", sa.UUID(), nullable=False),
        sa.Column("output_record_ordinal", sa.Integer(), nullable=False),
        sa.Column("field_path", sa.String(length=500), nullable=False),
        sa.Column("match_method", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "output_record_ordinal >= 0",
            name="ck_observation_extraction_record_ordinal",
        ),
        sa.CheckConstraint(
            "match_method IN ('direct_write', 'backfill_exact')",
            name="ck_observation_extraction_match_method",
        ),
        sa.ForeignKeyConstraint(
            ["extraction_run_id"],
            ["extraction_runs.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["observation_id"],
            ["metric_observations.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("observation_id"),
        sa.UniqueConstraint(
            "extraction_run_id",
            "output_record_ordinal",
            "field_path",
            name="uq_observation_extraction_output_field",
        ),
    )
    op.create_index(
        op.f("ix_observation_extraction_links_extraction_run_id"),
        "observation_extraction_links",
        ["extraction_run_id"],
    )
    op.create_table(
        "lineage_backfill_audits",
        sa.Column("key", sa.String(length=100), nullable=False),
        sa.Column("details", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("key"),
    )

    # Every historical observation already has one non-null, FK-protected primary
    # fragment. Preserve that exact claim without changing the immutable row.
    op.execute(
        """
        INSERT INTO observation_evidence_sets (
          observation_id, citation_count, created_at
        )
        SELECT id, 1, CURRENT_TIMESTAMP
        FROM metric_observations
        """
    )
    op.execute(
        """
        INSERT INTO observation_evidence_links (
          observation_id,
          ordinal,
          evidence_fragment_id,
          role,
          claim_key,
          field_path,
          created_at
        )
        SELECT
          id,
          0,
          evidence_fragment_id,
          'primary',
          metric_key,
          format('$.%s', metric_key),
          CURRENT_TIMESTAMP
        FROM metric_observations
        """
    )

    # Candidate matching is deliberately exact. Repeated extraction runs remain
    # unresolved unless one output record uniquely matches the frozen value,
    # dimensions, primary citation, panel, snapshot, model and prompt version.
    op.execute(
        """
        CREATE TEMPORARY TABLE v2_observation_extraction_candidates
        ON COMMIT DROP AS
        SELECT
          observation_id,
          extraction_run_id,
          output_record_ordinal,
          metric_key,
          count(*) OVER (PARTITION BY observation_id) AS candidate_count,
          count(*) OVER (
            PARTITION BY extraction_run_id, output_record_ordinal, metric_key
          ) AS output_claim_count
        FROM (
          SELECT
            observation.id AS observation_id,
            run.id AS extraction_run_id,
            (record.ordinality - 1)::integer AS output_record_ordinal,
            observation.metric_key AS metric_key
          FROM metric_observations AS observation
          JOIN evidence_fragments AS fragment
            ON fragment.id = observation.evidence_fragment_id
          JOIN extraction_runs AS run
            ON run.panel_version_id::text = observation.panel_version_key
           AND run.snapshot_id = fragment.snapshot_id
           AND run.model = observation.extraction_model
           AND run.prompt_version = observation.extraction_prompt_version
           AND run.created_at <= observation.created_at
          JOIN panel_versions AS panel
            ON panel.id = run.panel_version_id
           AND panel.version::text = observation.schema_version
           AND panel.extraction_prompt_version = run.prompt_version
          CROSS JOIN LATERAL jsonb_array_elements(
            CASE
              WHEN jsonb_typeof(run.output -> 'records') = 'array'
                THEN run.output -> 'records'
              ELSE '[]'::jsonb
            END
          )
            WITH ORDINALITY AS record(item, ordinality)
          WHERE observation.extraction_model IS NOT NULL
            AND observation.supersedes_id IS NULL
            -- Historical rows froze only one compatibility fragment. A row
            -- with dimensions or a multi-fragment output cannot be upgraded
            -- to exact direct lineage without inventing missing claim links.
            AND observation.dimensions = '{}'::jsonb
            AND jsonb_typeof(observation.raw_value) = 'object'
            AND jsonb_typeof(observation.normalized_value) = 'object'
            AND jsonb_typeof(observation.dimensions) = 'object'
            AND jsonb_typeof(run.output -> 'records') = 'array'
            AND run.validation ->> 'valid' = 'true'
            AND NOT EXISTS (
              SELECT 1
              FROM calculation_runs AS calculation
              WHERE calculation.output_observation_id = observation.id
            )
            AND jsonb_typeof(record.item) = 'object'
            AND jsonb_typeof(record.item -> 'data') = 'object'
            AND jsonb_typeof(record.item -> 'evidence') = 'object'
            AND observation.raw_value ? 'value'
            AND observation.normalized_value ? 'value'
            AND (record.item -> 'data') ? observation.metric_key
            AND record.item -> 'data' -> observation.metric_key
                = observation.raw_value -> 'value'
            AND record.item -> 'data' -> observation.metric_key
                = observation.normalized_value -> 'value'
            AND jsonb_typeof(
                  record.item -> 'data' -> observation.metric_key
                ) = 'number'
            AND jsonb_typeof(observation.raw_value -> 'value') = 'number'
            AND jsonb_typeof(observation.normalized_value -> 'value') = 'number'
            AND (record.item -> 'data') @> observation.dimensions
            AND (
              record.item -> 'evidence' -> observation.metric_key
                = to_jsonb(observation.evidence_fragment_id::text)
              OR (
                jsonb_typeof(
                  record.item -> 'evidence' -> observation.metric_key
                ) = 'array'
                AND jsonb_array_length(
                  record.item -> 'evidence' -> observation.metric_key
                ) = 1
                AND record.item -> 'evidence' -> observation.metric_key
                  @> jsonb_build_array(observation.evidence_fragment_id::text)
              )
            )
        ) AS exact_candidates
        """
    )
    op.execute(
        """
        INSERT INTO observation_extraction_links (
          observation_id,
          extraction_run_id,
          output_record_ordinal,
          field_path,
          match_method,
          created_at
        )
        SELECT
          observation_id,
          extraction_run_id,
          output_record_ordinal,
          format(
            '$.records[%s].data.%s',
            output_record_ordinal,
            observation.metric_key
          ),
          'backfill_exact',
          CURRENT_TIMESTAMP
        FROM v2_observation_extraction_candidates AS candidate
        JOIN metric_observations AS observation
          ON observation.id = candidate.observation_id
        WHERE candidate_count = 1
          AND output_claim_count = 1
        """
    )
    # The generic compatibility path remains truthful for unresolved history.
    # Exact backfill candidates can safely receive the exact run/output path in
    # the new association table before it is frozen.
    op.execute(
        """
        UPDATE observation_evidence_links AS link
        SET field_path = extraction.field_path
        FROM observation_extraction_links AS extraction
        WHERE extraction.observation_id = link.observation_id
          AND link.claim_key = (
            SELECT metric_key
            FROM metric_observations
            WHERE id = link.observation_id
          )
        """
    )
    op.execute(
        """
        INSERT INTO lineage_backfill_audits (key, details, created_at)
        SELECT
          '0005_observation_extraction_backfill',
          jsonb_build_object(
            'target_observation_count', count(*),
            'linked_observation_count', count(*) FILTER (
              WHERE coalesce(candidate.candidate_count, 0) = 1
                AND coalesce(candidate.output_claim_count, 0) = 1
            ),
            'unresolved_zero_candidate_count', count(*) FILTER (
              WHERE coalesce(candidate.candidate_count, 0) = 0
            ),
            'unresolved_ambiguous_candidate_count', count(*) FILTER (
              WHERE candidate.candidate_count > 1
            ),
            'unresolved_output_claim_collision_count', count(*) FILTER (
              WHERE candidate.candidate_count = 1
                AND candidate.output_claim_count > 1
            ),
            'method', 'exact_output_match_only'
          ),
          CURRENT_TIMESTAMP
        FROM metric_observations AS observation
        LEFT JOIN (
          SELECT
            observation_id,
            max(candidate_count) AS candidate_count,
            max(output_claim_count) AS output_claim_count
          FROM v2_observation_extraction_candidates
          GROUP BY observation_id
        ) AS candidate ON candidate.observation_id = observation.id
        WHERE observation.extraction_model IS NOT NULL
          AND observation.supersedes_id IS NULL
          AND NOT EXISTS (
            SELECT 1
            FROM calculation_runs AS calculation
            WHERE calculation.output_observation_id = observation.id
          )
        """
    )

    # Freeze each evidence set at commit time. UPDATE/DELETE guards alone are not
    # enough because a later INSERT would silently change historical provenance.
    op.execute(
        """
        CREATE FUNCTION v2_validate_observation_evidence_set()
        RETURNS trigger AS $$
        DECLARE
          target_id uuid;
          expected_count integer;
          actual_count integer;
          primary_count integer;
          minimum_ordinal integer;
          maximum_ordinal integer;
          legacy_primary uuid;
          linked_primary uuid;
        BEGIN
          IF TG_TABLE_NAME = 'metric_observations' THEN
            target_id := coalesce(NEW.id, OLD.id);
          ELSE
            target_id := coalesce(NEW.observation_id, OLD.observation_id);
          END IF;
          SELECT citation_count
          INTO expected_count
          FROM observation_evidence_sets
          WHERE observation_id = target_id;

          IF expected_count IS NULL THEN
            RAISE EXCEPTION 'observation % is missing its frozen evidence set', target_id;
          END IF;

          SELECT
            count(*),
            count(*) FILTER (WHERE role = 'primary' AND ordinal = 0),
            min(ordinal),
            max(ordinal),
            (array_agg(evidence_fragment_id) FILTER (
              WHERE role = 'primary' AND ordinal = 0
            ))[1]
          INTO
            actual_count,
            primary_count,
            minimum_ordinal,
            maximum_ordinal,
            linked_primary
          FROM observation_evidence_links
          WHERE observation_id = target_id;

          SELECT evidence_fragment_id
          INTO legacy_primary
          FROM metric_observations
          WHERE id = target_id;

          IF actual_count <> expected_count THEN
            RAISE EXCEPTION
              'observation % evidence count is %, expected %',
              target_id, actual_count, expected_count;
          END IF;
          IF minimum_ordinal <> 0 OR maximum_ordinal <> actual_count - 1 THEN
            RAISE EXCEPTION
              'observation % evidence ordinals are not contiguous', target_id;
          END IF;
          IF primary_count <> 1 OR linked_primary IS DISTINCT FROM legacy_primary THEN
            RAISE EXCEPTION
              'observation % primary evidence does not match its frozen compatibility reference',
              target_id;
          END IF;
          RETURN NULL;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    for table in (
        "metric_observations",
        "observation_evidence_sets",
        "observation_evidence_links",
    ):
        op.execute(
            f"""
            CREATE CONSTRAINT TRIGGER trg_{table}_evidence_complete
            AFTER INSERT OR UPDATE OR DELETE ON {table}
            DEFERRABLE INITIALLY DEFERRED
            FOR EACH ROW EXECUTE FUNCTION v2_validate_observation_evidence_set();
            """
        )

    op.execute(
        """
        CREATE FUNCTION v2_validate_extraction_run_input_set()
        RETURNS trigger AS $$
        DECLARE
          target_id uuid;
          run extraction_runs%ROWTYPE;
          expected_count integer;
          frozen_count integer;
          actual_count integer;
          minimum_ordinal integer;
          maximum_ordinal integer;
        BEGIN
          IF TG_TABLE_NAME = 'extraction_runs' THEN
            target_id := coalesce(NEW.id, OLD.id);
          ELSE
            target_id := coalesce(NEW.extraction_run_id, OLD.extraction_run_id);
          END IF;
          SELECT * INTO run FROM extraction_runs WHERE id = target_id;
          SELECT input_count
          INTO expected_count
          FROM extraction_run_input_sets
          WHERE extraction_run_id = target_id;

          IF run.validation ->> 'extraction_contract_version'
               = 'evidence-extraction-v3' THEN
            IF expected_count IS NULL THEN
              RAISE EXCEPTION 'extraction run % lacks its frozen input set', target_id;
            END IF;
            IF run.validation ->> 'input_manifest_count' IS NULL
               OR run.validation ->> 'input_manifest_count' !~ '^[0-9]+$'
               OR run.validation ->> 'input_manifest_hash' IS NULL
               OR run.validation ->> 'input_manifest_hash' !~ '^[0-9a-f]{64}$' THEN
              RAISE EXCEPTION 'extraction run % lacks a frozen manifest header', target_id;
            END IF;
            frozen_count := (run.validation ->> 'input_manifest_count')::integer;
            IF expected_count IS DISTINCT FROM frozen_count OR expected_count < 1 THEN
              RAISE EXCEPTION
                'extraction run % input set count does not match its frozen header',
                target_id;
            END IF;
          END IF;
          IF expected_count IS NULL THEN
            RETURN NULL;
          END IF;

          SELECT count(*), min(ordinal), max(ordinal)
          INTO actual_count, minimum_ordinal, maximum_ordinal
          FROM extraction_run_inputs
          WHERE extraction_run_id = target_id;
          IF actual_count <> expected_count THEN
            RAISE EXCEPTION
              'extraction run % input count is %, expected %',
              target_id, actual_count, expected_count;
          END IF;
          IF actual_count > 0
             AND (minimum_ordinal <> 0 OR maximum_ordinal <> actual_count - 1) THEN
            RAISE EXCEPTION 'extraction run % input ordinals are not contiguous', target_id;
          END IF;
          IF EXISTS (
            SELECT 1
            FROM extraction_run_inputs AS input
            JOIN evidence_fragments AS fragment
              ON fragment.id = input.evidence_fragment_id
            WHERE input.extraction_run_id = target_id
              AND (
                fragment.snapshot_id IS DISTINCT FROM run.snapshot_id
                OR fragment.extracted_text_sha256
                     IS DISTINCT FROM input.extracted_text_sha256
                OR fragment.created_at > run.created_at
              )
          ) THEN
            RAISE EXCEPTION 'extraction run % input manifest is inconsistent', target_id;
          END IF;
          RETURN NULL;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    for table in (
        "extraction_runs",
        "extraction_run_input_sets",
        "extraction_run_inputs",
    ):
        op.execute(
            f"""
            CREATE CONSTRAINT TRIGGER trg_{table}_input_complete
            AFTER INSERT OR UPDATE OR DELETE ON {table}
            DEFERRABLE INITIALLY DEFERRED
            FOR EACH ROW EXECUTE FUNCTION v2_validate_extraction_run_input_set();
            """
        )

    op.execute(
        """
        CREATE FUNCTION v2_validate_observation_extraction_link()
        RETURNS trigger AS $$
        DECLARE
          observation metric_observations%ROWTYPE;
          run extraction_runs%ROWTYPE;
          panel panel_versions%ROWTYPE;
          output_record jsonb;
          citation jsonb;
          citation_array jsonb;
          metric_definition jsonb;
          linked_claim record;
          linked_fragment record;
          dimension_contract record;
          distinct_claim_count integer;
          expected_claim_count integer;
        BEGIN
          SELECT * INTO observation
          FROM metric_observations
          WHERE id = NEW.observation_id;
          SELECT * INTO run
          FROM extraction_runs
          WHERE id = NEW.extraction_run_id;
          SELECT * INTO panel
          FROM panel_versions
          WHERE id = run.panel_version_id;

          IF TG_OP = 'INSERT' AND NEW.match_method = 'backfill_exact' THEN
            RAISE EXCEPTION 'backfill_exact is reserved for migration-time lineage only';
          END IF;
          IF observation.supersedes_id IS NOT NULL THEN
            RAISE EXCEPTION 'revision observation % cannot claim direct extraction origin', observation.id;
          END IF;
          IF EXISTS (
            SELECT 1 FROM calculation_runs
            WHERE output_observation_id = observation.id
          ) THEN
            RAISE EXCEPTION 'calculation observation % cannot claim direct extraction origin', observation.id;
          END IF;
          IF run.validation ->> 'valid' IS DISTINCT FROM 'true' THEN
            RAISE EXCEPTION 'observation % cannot link to invalid extraction run %', observation.id, run.id;
          END IF;
          IF NEW.match_method = 'direct_write'
             AND run.validation ->> 'extraction_contract_version'
                   IS DISTINCT FROM 'evidence-extraction-v3' THEN
            RAISE EXCEPTION 'direct extraction run % lacks the current frozen input contract', run.id;
          END IF;
          IF NEW.match_method = 'direct_write' AND NOT EXISTS (
            SELECT 1
            FROM extraction_run_inputs
            WHERE extraction_run_id = run.id
          ) THEN
            RAISE EXCEPTION 'direct extraction run % lacks a frozen input manifest', run.id;
          END IF;
          IF run.created_at > observation.created_at THEN
            RAISE EXCEPTION 'future extraction run % cannot originate observation %', run.id, observation.id;
          END IF;
          IF run.panel_version_id::text IS DISTINCT FROM observation.panel_version_key
             OR panel.id IS NULL
             OR panel.version::text IS DISTINCT FROM observation.schema_version
             OR run.prompt_version IS DISTINCT FROM panel.extraction_prompt_version
             OR run.model IS DISTINCT FROM observation.extraction_model
             OR run.prompt_version IS DISTINCT FROM observation.extraction_prompt_version THEN
            RAISE EXCEPTION 'observation % extraction metadata does not match run %', observation.id, run.id;
          END IF;

          metric_definition := panel.data_schema -> 'properties' -> observation.metric_key;
          IF jsonb_typeof(panel.data_schema) IS DISTINCT FROM 'object'
             OR jsonb_typeof(panel.data_schema -> 'properties') IS DISTINCT FROM 'object'
             OR jsonb_typeof(metric_definition) IS DISTINCT FROM 'object'
             OR metric_definition ->> 'type' NOT IN ('number', 'integer') THEN
            RAISE EXCEPTION
              'observation % metric is not numeric in frozen panel schema',
              observation.id;
          END IF;
          IF metric_definition ? 'x-unit' THEN
            IF jsonb_typeof(metric_definition -> 'x-unit') IS DISTINCT FROM 'string'
               OR observation.unit IS DISTINCT FROM metric_definition ->> 'x-unit' THEN
              RAISE EXCEPTION
                'observation % unit does not match frozen panel schema',
                observation.id;
            END IF;
          ELSIF metric_definition ->> 'x-unitless' = 'true' THEN
            IF observation.unit IS NOT NULL THEN
              RAISE EXCEPTION
                'unitless observation % declares a unit', observation.id;
            END IF;
          ELSE
            RAISE EXCEPTION
              'observation % lacks a valid frozen unit contract', observation.id;
          END IF;

          output_record := run.output -> 'records' -> NEW.output_record_ordinal;
          IF jsonb_typeof(output_record) IS DISTINCT FROM 'object'
             OR jsonb_typeof(output_record -> 'data') IS DISTINCT FROM 'object'
             OR jsonb_typeof(output_record -> 'evidence') IS DISTINCT FROM 'object'
             OR jsonb_typeof(observation.raw_value) IS DISTINCT FROM 'object'
             OR jsonb_typeof(observation.normalized_value) IS DISTINCT FROM 'object'
             OR jsonb_typeof(observation.dimensions) IS DISTINCT FROM 'object'
             OR NOT (observation.raw_value ? 'value')
             OR NOT (observation.normalized_value ? 'value')
             OR NOT ((output_record -> 'data') ? observation.metric_key)
             OR jsonb_typeof(output_record -> 'data' -> observation.metric_key)
                  IS DISTINCT FROM 'number'
             OR jsonb_typeof(observation.raw_value -> 'value')
                  IS DISTINCT FROM 'number'
             OR jsonb_typeof(observation.normalized_value -> 'value')
                  IS DISTINCT FROM 'number'
             OR (
               metric_definition ->> 'type' = 'integer'
               AND (observation.raw_value ->> 'value')::numeric
                     <> trunc((observation.raw_value ->> 'value')::numeric)
             )
             OR output_record -> 'data' -> observation.metric_key
                IS DISTINCT FROM observation.raw_value -> 'value'
             OR output_record -> 'data' -> observation.metric_key
                IS DISTINCT FROM observation.normalized_value -> 'value'
             OR NOT ((output_record -> 'data') @> observation.dimensions)
             OR EXISTS (
               SELECT 1
               FROM jsonb_each(observation.dimensions) AS dimension(key, value)
               WHERE dimension.value = 'null'::jsonb
                  OR NOT ((output_record -> 'data') ? dimension.key)
             )
             OR NEW.field_path IS DISTINCT FROM format(
                  '$.records[%s].data.%s',
                  NEW.output_record_ordinal,
                  observation.metric_key
                ) THEN
            RAISE EXCEPTION 'observation % does not match extraction output field', observation.id;
          END IF;

          FOR dimension_contract IN
            SELECT key, value
            FROM jsonb_each(observation.dimensions)
          LOOP
            IF panel.data_schema -> 'properties' -> dimension_contract.key ->> 'type'
                 = 'string' THEN
              IF jsonb_typeof(dimension_contract.value) IS DISTINCT FROM 'string' THEN
                RAISE EXCEPTION
                  'observation % dimension % violates string schema',
                  observation.id, dimension_contract.key;
              END IF;
            ELSIF panel.data_schema -> 'properties' -> dimension_contract.key ->> 'type'
                    = 'boolean' THEN
              IF jsonb_typeof(dimension_contract.value) IS DISTINCT FROM 'boolean' THEN
                RAISE EXCEPTION
                  'observation % dimension % violates boolean schema',
                  observation.id, dimension_contract.key;
              END IF;
            ELSE
              RAISE EXCEPTION
                'observation % dimension % is not declared by frozen panel schema',
                observation.id, dimension_contract.key;
            END IF;
          END LOOP;

          SELECT count(DISTINCT claim_key)
          INTO distinct_claim_count
          FROM observation_evidence_links
          WHERE observation_id = observation.id;
          IF jsonb_typeof(observation.dimensions) IS DISTINCT FROM 'object' THEN
            RAISE EXCEPTION 'observation % dimensions must be a JSON object', observation.id;
          END IF;
          SELECT 1 + count(*)
          INTO expected_claim_count
          FROM jsonb_object_keys(observation.dimensions);
          IF distinct_claim_count IS DISTINCT FROM expected_claim_count THEN
            RAISE EXCEPTION
              'observation % evidence claims are incomplete: found %, expected %',
              observation.id, distinct_claim_count, expected_claim_count;
          END IF;

          FOR linked_claim IN
            SELECT claim_key, count(*) AS link_count
            FROM observation_evidence_links
            WHERE observation_id = observation.id
            GROUP BY claim_key
          LOOP
            IF linked_claim.claim_key <> observation.metric_key
               AND NOT (observation.dimensions ? linked_claim.claim_key) THEN
              RAISE EXCEPTION
                'observation % contains evidence for unknown claim %',
                observation.id, linked_claim.claim_key;
            END IF;
            IF linked_claim.claim_key = observation.metric_key THEN
              IF output_record -> 'data' -> linked_claim.claim_key
                   IS DISTINCT FROM observation.raw_value -> 'value'
                 OR output_record -> 'data' -> linked_claim.claim_key
                   IS DISTINCT FROM observation.normalized_value -> 'value' THEN
                RAISE EXCEPTION
                  'observation % metric claim does not match extraction output',
                  observation.id;
              END IF;
            ELSIF output_record -> 'data' -> linked_claim.claim_key
                    IS DISTINCT FROM observation.dimensions -> linked_claim.claim_key THEN
              RAISE EXCEPTION
                'observation % dimension claim % does not match extraction output',
                observation.id, linked_claim.claim_key;
            END IF;

            citation := output_record -> 'evidence' -> linked_claim.claim_key;
            IF jsonb_typeof(citation) = 'string' THEN
              citation_array := jsonb_build_array(citation);
            ELSIF jsonb_typeof(citation) = 'array' THEN
              citation_array := citation;
            ELSE
              RAISE EXCEPTION
                'observation % claim % has no valid extraction citation',
                observation.id, linked_claim.claim_key;
            END IF;
            IF jsonb_array_length(citation_array) <> linked_claim.link_count
               OR EXISTS (
                 SELECT 1
                 FROM observation_evidence_links AS link
                 WHERE link.observation_id = observation.id
                   AND link.claim_key = linked_claim.claim_key
                   AND NOT EXISTS (
                     SELECT 1
                     FROM jsonb_array_elements_text(citation_array) AS item(value)
                     WHERE item.value = link.evidence_fragment_id::text
                   )
               )
               OR EXISTS (
                 SELECT 1
                 FROM jsonb_array_elements_text(citation_array) AS item(value)
                 WHERE NOT EXISTS (
                   SELECT 1
                   FROM observation_evidence_links AS link
                   WHERE link.observation_id = observation.id
                     AND link.claim_key = linked_claim.claim_key
                     AND link.evidence_fragment_id::text = item.value
                 )
               ) THEN
              RAISE EXCEPTION
                'observation % claim % citations do not exactly match frozen evidence',
                observation.id, linked_claim.claim_key;
            END IF;
          END LOOP;

          FOR linked_fragment IN
            SELECT
              link.evidence_fragment_id,
              link.role,
              link.claim_key,
              link.field_path,
              fragment.snapshot_id
            FROM observation_evidence_links AS link
            JOIN evidence_fragments AS fragment
              ON fragment.id = link.evidence_fragment_id
            WHERE link.observation_id = observation.id
          LOOP
            IF linked_fragment.snapshot_id <> run.snapshot_id THEN
              RAISE EXCEPTION 'observation % cites evidence outside extraction snapshot', observation.id;
            END IF;
            IF NEW.match_method = 'direct_write' AND NOT EXISTS (
              SELECT 1
              FROM extraction_run_inputs AS input
              WHERE input.extraction_run_id = run.id
                AND input.evidence_fragment_id = linked_fragment.evidence_fragment_id
            ) THEN
              RAISE EXCEPTION
                'observation % cites a fragment absent from extraction input manifest',
                observation.id;
            END IF;
            IF linked_fragment.field_path IS DISTINCT FROM format(
                 '$.records[%s].data.%s',
                 NEW.output_record_ordinal,
                 linked_fragment.claim_key
               ) THEN
              RAISE EXCEPTION 'observation % evidence field path is inconsistent', observation.id;
            END IF;
            IF linked_fragment.claim_key = observation.metric_key
               AND linked_fragment.role NOT IN ('primary', 'supporting') THEN
              RAISE EXCEPTION 'observation % metric evidence role is invalid', observation.id;
            END IF;
            IF linked_fragment.claim_key <> observation.metric_key
               AND linked_fragment.role <> 'dimension' THEN
              RAISE EXCEPTION 'observation % dimension evidence role is invalid', observation.id;
            END IF;
          END LOOP;
          RETURN NULL;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE CONSTRAINT TRIGGER trg_observation_extraction_links_valid
        AFTER INSERT OR UPDATE ON observation_extraction_links
        DEFERRABLE INITIALLY DEFERRED
        FOR EACH ROW EXECUTE FUNCTION v2_validate_observation_extraction_link();
        """
    )
    # Constraint triggers are not retroactive. Schedule every conservative
    # backfill row for validation so an invariant mismatch aborts the migration.
    op.execute(
        "UPDATE observation_extraction_links SET field_path = field_path"
    )

    # Direct extraction, revision and deterministic calculation are mutually
    # exclusive origins. Check every origin table so a later append cannot turn
    # a previously valid observation into an ambiguous record.
    op.execute(
        """
        DO $$
        BEGIN
          IF EXISTS (
            SELECT 1
            FROM observation_revisions AS revision
            JOIN metric_observations AS replacement
              ON replacement.id = revision.replacement_observation_id
            WHERE replacement.supersedes_id
                    IS DISTINCT FROM revision.original_observation_id
          ) THEN
            RAISE EXCEPTION
              'historical revision lineage is inconsistent; refusing automatic repair';
          END IF;
          IF EXISTS (
            SELECT 1
            FROM metric_observations AS replacement
            LEFT JOIN observation_revisions AS revision
              ON revision.replacement_observation_id = replacement.id
            WHERE replacement.supersedes_id IS NOT NULL
            GROUP BY replacement.id, replacement.supersedes_id
            HAVING replacement.id = replacement.supersedes_id
               OR count(revision.id) <> 1
               OR (array_agg(revision.original_observation_id))[1]
                    IS DISTINCT FROM replacement.supersedes_id
          ) THEN
            RAISE EXCEPTION
              'historical revision lineage is inconsistent; refusing automatic repair';
          END IF;
          IF EXISTS (
            SELECT observation_id
            FROM (
              SELECT observation_id, 'extraction' AS origin
              FROM observation_extraction_links
              UNION ALL
              SELECT replacement_observation_id, 'revision'
              FROM observation_revisions
              UNION ALL
              SELECT output_observation_id, 'calculation'
              FROM calculation_runs
            ) AS origins
            GROUP BY observation_id
            HAVING count(*) > 1
          ) THEN
            RAISE EXCEPTION 'historical observation contains multiple origin records';
          END IF;
        END
        $$;
        """
    )
    op.execute(
        """
        CREATE FUNCTION v2_validate_observation_revision_consistency()
        RETURNS trigger AS $$
        DECLARE
          target_id uuid;
          superseded_id uuid;
          revision_count integer;
          revision_original_id uuid;
        BEGIN
          IF TG_TABLE_NAME = 'metric_observations' THEN
            target_id := NEW.id;
          ELSE
            target_id := NEW.replacement_observation_id;
          END IF;
          SELECT supersedes_id
          INTO superseded_id
          FROM metric_observations
          WHERE id = target_id;
          SELECT count(*), (array_agg(original_observation_id))[1]
          INTO revision_count, revision_original_id
          FROM observation_revisions
          WHERE replacement_observation_id = target_id;
          IF superseded_id IS NULL AND revision_count = 0 THEN
            RETURN NULL;
          END IF;
          IF target_id = superseded_id
             OR revision_count <> 1
             OR superseded_id IS DISTINCT FROM revision_original_id THEN
            RAISE EXCEPTION
              'observation % revision relation is missing, self-referential, or inconsistent',
              target_id;
          END IF;
          RETURN NULL;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE CONSTRAINT TRIGGER trg_observation_revisions_consistent
        AFTER INSERT OR UPDATE ON observation_revisions
        DEFERRABLE INITIALLY DEFERRED
        FOR EACH ROW EXECUTE FUNCTION v2_validate_observation_revision_consistency();
        """
    )
    op.execute(
        """
        CREATE CONSTRAINT TRIGGER trg_metric_observations_revision_consistent
        AFTER INSERT OR UPDATE ON metric_observations
        DEFERRABLE INITIALLY DEFERRED
        FOR EACH ROW EXECUTE FUNCTION v2_validate_observation_revision_consistency();
        """
    )
    op.execute(
        """
        CREATE FUNCTION v2_validate_observation_origin_exclusive()
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
    for table in (
        "observation_extraction_links",
        "observation_revisions",
        "calculation_runs",
    ):
        op.execute(
            f"""
            CREATE CONSTRAINT TRIGGER trg_{table}_origin_exclusive
            AFTER INSERT OR UPDATE ON {table}
            DEFERRABLE INITIALLY DEFERRED
            FOR EACH ROW EXECUTE FUNCTION v2_validate_observation_origin_exclusive();
            """
        )

    for table in (
        "observation_evidence_sets",
        "observation_evidence_links",
        "observation_extraction_links",
        "lineage_backfill_audits",
        "extraction_run_input_sets",
        "extraction_run_inputs",
    ):
        op.execute(
            f"""
            CREATE TRIGGER trg_{table}_immutable
            BEFORE UPDATE OR DELETE ON {table}
            FOR EACH ROW EXECUTE FUNCTION v2_reject_immutable_mutation();
            """
        )

    # Row-level UPDATE/DELETE guards do not fire for TRUNCATE. Refuse it for
    # every append-only V2 history table, including those introduced earlier.
    immutable_tables = (
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
        "trust_assessments",
        "l2_insights",
        "l2_insight_inputs",
        "observation_evidence_sets",
        "observation_evidence_links",
        "observation_extraction_links",
        "lineage_backfill_audits",
        "extraction_run_input_sets",
        "extraction_run_inputs",
    )
    for table in immutable_tables:
        op.execute(
            f"""
            CREATE TRIGGER trg_{table}_immutable_truncate
            BEFORE TRUNCATE ON {table}
            FOR EACH STATEMENT EXECUTE FUNCTION v2_reject_immutable_mutation();
            """
        )


def downgrade() -> None:
    # A populated evidence set is new immutable history. Refuse to erase it from
    # a real database; downgrade/re-upgrade tests must use a disposable empty DB.
    op.execute(
        """
        DO $$
        BEGIN
          IF EXISTS (SELECT 1 FROM observation_evidence_sets)
             OR EXISTS (SELECT 1 FROM extraction_run_input_sets) THEN
            RAISE EXCEPTION
              'downgrade would erase frozen observation lineage or extraction manifests; use a disposable empty database';
          END IF;
        END
        $$;
        """
    )
    immutable_tables = (
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
        "trust_assessments",
        "l2_insights",
        "l2_insight_inputs",
        "observation_evidence_sets",
        "observation_evidence_links",
        "observation_extraction_links",
        "lineage_backfill_audits",
        "extraction_run_input_sets",
        "extraction_run_inputs",
    )
    for table in immutable_tables:
        op.execute(
            f"DROP TRIGGER IF EXISTS trg_{table}_immutable_truncate ON {table}"
        )
    for table in (
        "extraction_run_inputs",
        "extraction_run_input_sets",
        "lineage_backfill_audits",
        "observation_extraction_links",
        "observation_evidence_links",
        "observation_evidence_sets",
    ):
        op.execute(f"DROP TRIGGER IF EXISTS trg_{table}_immutable ON {table}")
    op.execute(
        "DROP TRIGGER IF EXISTS trg_observation_extraction_links_valid "
        "ON observation_extraction_links"
    )
    for table in (
        "extraction_run_inputs",
        "extraction_run_input_sets",
        "extraction_runs",
    ):
        op.execute(
            f"DROP TRIGGER IF EXISTS trg_{table}_input_complete ON {table}"
        )
    op.execute(
        "DROP TRIGGER IF EXISTS trg_observation_revisions_consistent "
        "ON observation_revisions"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS trg_metric_observations_revision_consistent "
        "ON metric_observations"
    )
    for table in (
        "calculation_runs",
        "observation_revisions",
        "observation_extraction_links",
    ):
        op.execute(
            f"DROP TRIGGER IF EXISTS trg_{table}_origin_exclusive ON {table}"
        )
    op.execute(
        "DROP TRIGGER IF EXISTS trg_metric_observations_evidence_complete "
        "ON metric_observations"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS trg_observation_evidence_links_evidence_complete "
        "ON observation_evidence_links"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS trg_observation_evidence_sets_evidence_complete "
        "ON observation_evidence_sets"
    )
    op.execute("DROP FUNCTION IF EXISTS v2_validate_observation_extraction_link()")
    op.execute("DROP FUNCTION IF EXISTS v2_validate_extraction_run_input_set()")
    op.execute("DROP FUNCTION IF EXISTS v2_validate_observation_revision_consistency()")
    op.execute("DROP FUNCTION IF EXISTS v2_validate_observation_origin_exclusive()")
    op.execute("DROP FUNCTION IF EXISTS v2_validate_observation_evidence_set()")
    op.drop_table("lineage_backfill_audits")
    op.drop_index(
        op.f("ix_observation_extraction_links_extraction_run_id"),
        table_name="observation_extraction_links",
    )
    op.drop_table("observation_extraction_links")
    op.drop_index(
        op.f("ix_extraction_run_inputs_evidence_fragment_id"),
        table_name="extraction_run_inputs",
    )
    op.drop_table("extraction_run_inputs")
    op.drop_table("extraction_run_input_sets")
    op.drop_index(
        "uq_observation_evidence_primary",
        table_name="observation_evidence_links",
    )
    op.drop_index(
        op.f("ix_observation_evidence_links_evidence_fragment_id"),
        table_name="observation_evidence_links",
    )
    op.drop_table("observation_evidence_links")
    op.drop_table("observation_evidence_sets")
