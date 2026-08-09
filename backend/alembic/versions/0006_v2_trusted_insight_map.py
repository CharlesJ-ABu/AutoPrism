"""Add evidence-bound observation geography for the trusted insight map.

Revision ID: 0006_v2_trusted_insight_map
Revises: 0005_v2_observation_lineage
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0006_v2_trusted_insight_map"
down_revision = "0005_v2_observation_lineage"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # A geographic scope written before this contract cannot be proven from a
    # frozen field/citation set. Refuse to infer or silently bless it.
    bind = op.get_bind()
    historical_scope_count = bind.execute(
        sa.text(
            """
            SELECT count(*)
            FROM metric_observations
            WHERE geographic_scope IS DISTINCT FROM '{}'::jsonb
            """
        )
    ).scalar_one()
    if historical_scope_count:
        raise RuntimeError(
            "historical geographic_scope rows lack geo-scope-v1 evidence; "
            "preserve them and migrate through an explicit reviewed contract"
        )

    op.create_table(
        "observation_geographies",
        sa.Column("observation_id", sa.UUID(), nullable=False),
        sa.Column("scope", postgresql.JSONB(), nullable=False),
        sa.Column("evidence_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "jsonb_typeof(scope) = 'object'",
            name="ck_observation_geography_scope_object",
        ),
        sa.CheckConstraint(
            "scope ->> 'contract_version' = 'geo-scope-v1'",
            name="ck_observation_geography_contract",
        ),
        sa.CheckConstraint(
            "evidence_count > 0",
            name="ck_observation_geography_evidence_count",
        ),
        sa.ForeignKeyConstraint(
            ["observation_id"],
            ["metric_observations.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("observation_id"),
    )
    op.create_table(
        "observation_geography_evidence",
        sa.Column("observation_id", sa.UUID(), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("evidence_fragment_id", sa.UUID(), nullable=False),
        sa.Column("claim_key", sa.String(length=255), nullable=False),
        sa.Column("field_path", sa.String(length=500), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "ordinal >= 0",
            name="ck_observation_geography_evidence_ordinal",
        ),
        sa.ForeignKeyConstraint(
            ["evidence_fragment_id"],
            ["evidence_fragments.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["observation_id"],
            ["observation_geographies.observation_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("observation_id", "ordinal"),
        sa.UniqueConstraint(
            "observation_id",
            "evidence_fragment_id",
            "field_path",
            name="uq_observation_geography_claim_fragment",
        ),
    )
    op.create_index(
        op.f("ix_observation_geography_evidence_evidence_fragment_id"),
        "observation_geography_evidence",
        ["evidence_fragment_id"],
    )

    op.execute(
        """
        CREATE FUNCTION v2_validate_observation_geography()
        RETURNS trigger AS $$
        DECLARE
          target_id uuid;
          observation metric_observations%ROWTYPE;
          geography observation_geographies%ROWTYPE;
          geography_count integer;
          link_count integer;
          distinct_ordinal_count integer;
          minimum_ordinal integer;
          maximum_ordinal integer;
          extraction_link observation_extraction_links%ROWTYPE;
          run extraction_runs%ROWTYPE;
          output_record jsonb;
          linked_claim RECORD;
          citation jsonb;
          citation_array jsonb;
        BEGIN
          IF TG_TABLE_NAME = 'metric_observations' THEN
            target_id := NEW.id;
          ELSE
            target_id := NEW.observation_id;
          END IF;

          SELECT * INTO observation
          FROM metric_observations
          WHERE id = target_id;
          IF NOT FOUND THEN
            RAISE EXCEPTION 'geographic observation % does not exist', target_id;
          END IF;

          SELECT count(*) INTO geography_count
          FROM observation_geographies
          WHERE observation_id = target_id;
          IF observation.geographic_scope = '{}'::jsonb THEN
            IF geography_count <> 0 THEN
              RAISE EXCEPTION 'observation % has unexpected geography rows', target_id;
            END IF;
            RETURN NULL;
          END IF;
          IF geography_count <> 1 THEN
            RAISE EXCEPTION 'observation % requires one frozen geography row', target_id;
          END IF;

          SELECT * INTO STRICT geography
          FROM observation_geographies
          WHERE observation_id = target_id;
          IF observation.geographic_scope IS DISTINCT FROM geography.scope THEN
            RAISE EXCEPTION 'observation % geographic scope does not match', target_id;
          END IF;
          IF jsonb_typeof(geography.scope) <> 'object'
             OR geography.scope ->> 'contract_version' <> 'geo-scope-v1'
             OR geography.scope ->> 'display_type' NOT IN
                ('MARKER', 'HOTSPOT', 'RIPPLE', 'FLOW', 'COMPARISON', 'SHIELD_UP', 'ZONE')
             OR jsonb_typeof(geography.scope -> 'geometry') <> 'object'
             OR jsonb_typeof(geography.scope -> 'source_fields') <> 'object'
             OR coalesce(geography.scope ->> 'label', '') = '' THEN
            RAISE EXCEPTION 'observation % geographic scope header is invalid', target_id;
          END IF;

          SELECT count(*), count(DISTINCT ordinal), min(ordinal), max(ordinal)
          INTO link_count, distinct_ordinal_count, minimum_ordinal, maximum_ordinal
          FROM observation_geography_evidence
          WHERE observation_id = target_id;
          IF link_count <> geography.evidence_count
             OR distinct_ordinal_count <> link_count
             OR minimum_ordinal <> 0
             OR maximum_ordinal <> link_count - 1 THEN
            RAISE EXCEPTION 'observation % geography evidence is incomplete', target_id;
          END IF;

          SELECT * INTO extraction_link
          FROM observation_extraction_links
          WHERE observation_id = target_id;
          IF NOT FOUND OR extraction_link.match_method <> 'direct_write' THEN
            RAISE EXCEPTION 'observation % geography requires a direct extraction', target_id;
          END IF;
          SELECT * INTO STRICT run
          FROM extraction_runs
          WHERE id = extraction_link.extraction_run_id;
          output_record := run.output -> 'records' -> extraction_link.output_record_ordinal;
          IF jsonb_typeof(output_record) <> 'object'
             OR jsonb_typeof(output_record -> 'data') <> 'object'
             OR jsonb_typeof(output_record -> 'evidence') <> 'object' THEN
            RAISE EXCEPTION 'observation % geography output record is invalid', target_id;
          END IF;

          FOR linked_claim IN
            SELECT claim_key, count(*) AS claim_count
            FROM observation_geography_evidence
            WHERE observation_id = target_id
            GROUP BY claim_key
          LOOP
            IF NOT EXISTS (
              SELECT 1
              FROM jsonb_each_text(geography.scope -> 'source_fields') AS source_field
              WHERE source_field.value = linked_claim.claim_key
            ) THEN
              RAISE EXCEPTION
                'observation % geography claim % is not frozen in source_fields',
                target_id, linked_claim.claim_key;
            END IF;
            IF NOT ((output_record -> 'data') ? linked_claim.claim_key) THEN
              RAISE EXCEPTION
                'observation % geography output lacks claim %',
                target_id, linked_claim.claim_key;
            END IF;
            citation := output_record -> 'evidence' -> linked_claim.claim_key;
            IF jsonb_typeof(citation) = 'string' THEN
              citation_array := jsonb_build_array(citation);
            ELSIF jsonb_typeof(citation) = 'array' THEN
              citation_array := citation;
            ELSE
              RAISE EXCEPTION
                'observation % geography citation % is invalid',
                target_id, linked_claim.claim_key;
            END IF;
            IF jsonb_array_length(citation_array) <> linked_claim.claim_count
               OR EXISTS (
                 SELECT 1
                 FROM observation_geography_evidence AS link
                 WHERE link.observation_id = target_id
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
                   FROM observation_geography_evidence AS link
                   WHERE link.observation_id = target_id
                     AND link.claim_key = linked_claim.claim_key
                     AND link.evidence_fragment_id::text = item.value
                 )
               ) THEN
              RAISE EXCEPTION
                'observation % geography citation set differs for %',
                target_id, linked_claim.claim_key;
            END IF;
          END LOOP;

          IF (
            SELECT count(DISTINCT source_field.value)
            FROM jsonb_each_text(geography.scope -> 'source_fields') AS source_field
          ) <> (
            SELECT count(DISTINCT claim_key)
            FROM observation_geography_evidence
            WHERE observation_id = target_id
          ) THEN
            RAISE EXCEPTION 'observation % geography claim set is incomplete', target_id;
          END IF;

          IF EXISTS (
            SELECT 1
            FROM observation_geography_evidence AS link
            JOIN evidence_fragments AS fragment
              ON fragment.id = link.evidence_fragment_id
            WHERE link.observation_id = target_id
              AND (
                fragment.snapshot_id <> run.snapshot_id
                OR link.field_path IS DISTINCT FROM format(
                  '$.records[%s].data.%s',
                  extraction_link.output_record_ordinal,
                  link.claim_key
                )
                OR NOT EXISTS (
                  SELECT 1
                  FROM extraction_run_inputs AS input
                  WHERE input.extraction_run_id = run.id
                    AND input.evidence_fragment_id = link.evidence_fragment_id
                )
              )
          ) THEN
            RAISE EXCEPTION 'observation % geography evidence lineage is invalid', target_id;
          END IF;
          RETURN NULL;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    for table in (
        "metric_observations",
        "observation_extraction_links",
        "observation_geographies",
        "observation_geography_evidence",
    ):
        op.execute(
            f"""
            CREATE CONSTRAINT TRIGGER trg_{table}_geography_valid
            AFTER INSERT OR UPDATE ON {table}
            DEFERRABLE INITIALLY DEFERRED
            FOR EACH ROW EXECUTE FUNCTION v2_validate_observation_geography();
            """
        )

    for table in (
        "observation_geographies",
        "observation_geography_evidence",
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
    bind = op.get_bind()
    geography_count = bind.execute(
        sa.text("SELECT count(*) FROM observation_geographies")
    ).scalar_one()
    if geography_count:
        raise RuntimeError(
            "downgrade would erase frozen observation geography; refusing"
        )
    for table in (
        "metric_observations",
        "observation_extraction_links",
        "observation_geographies",
        "observation_geography_evidence",
    ):
        op.execute(f"DROP TRIGGER trg_{table}_geography_valid ON {table}")
    for table in (
        "observation_geographies",
        "observation_geography_evidence",
    ):
        op.execute(f"DROP TRIGGER trg_{table}_immutable ON {table}")
        op.execute(f"DROP TRIGGER trg_{table}_immutable_truncate ON {table}")
    op.execute("DROP FUNCTION v2_validate_observation_geography()")
    op.drop_index(
        op.f("ix_observation_geography_evidence_evidence_fragment_id"),
        table_name="observation_geography_evidence",
    )
    op.drop_table("observation_geography_evidence")
    op.drop_table("observation_geographies")
