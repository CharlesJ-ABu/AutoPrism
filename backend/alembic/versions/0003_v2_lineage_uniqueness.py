"""Prevent observation and review lineage forks.

Revision ID: 0003_v2_lineage_uniqueness
Revises: 0002_backfill_legacy_evidence
"""

from alembic import op


revision = "0003_v2_lineage_uniqueness"
down_revision = "0002_backfill_legacy_evidence"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Do not repair or delete historical rows automatically. If an old database
    # already contains a fork, stop and require an explicit human reconciliation.
    op.execute(
        """
        DO $$
        BEGIN
          IF EXISTS (
            SELECT supersedes_id
            FROM metric_observations
            WHERE supersedes_id IS NOT NULL
            GROUP BY supersedes_id
            HAVING count(*) > 1
          ) THEN
            RAISE EXCEPTION 'metric observation lineage contains a fork';
          END IF;
          IF EXISTS (
            SELECT original_observation_id
            FROM observation_revisions
            GROUP BY original_observation_id
            HAVING count(*) > 1
          ) THEN
            RAISE EXCEPTION 'observation revision lineage contains a fork';
          END IF;
          IF EXISTS (
            SELECT supersedes_id
            FROM review_decisions
            WHERE supersedes_id IS NOT NULL
            GROUP BY supersedes_id
            HAVING count(*) > 1
          ) THEN
            RAISE EXCEPTION 'review decision lineage contains a fork';
          END IF;
          IF EXISTS (
            SELECT review_case_id
            FROM review_decisions
            WHERE supersedes_id IS NULL
            GROUP BY review_case_id
            HAVING count(*) > 1
          ) THEN
            RAISE EXCEPTION 'review case contains multiple root decisions';
          END IF;
        END
        $$;
        """
    )
    op.create_index(
        "uq_metric_observation_supersedes",
        "metric_observations",
        ["supersedes_id"],
        unique=True,
        postgresql_where="supersedes_id IS NOT NULL",
    )
    op.create_unique_constraint(
        "uq_observation_revision_original",
        "observation_revisions",
        ["original_observation_id"],
    )
    op.create_index(
        "uq_review_decision_supersedes",
        "review_decisions",
        ["supersedes_id"],
        unique=True,
        postgresql_where="supersedes_id IS NOT NULL",
    )
    op.create_index(
        "uq_review_decision_root",
        "review_decisions",
        ["review_case_id"],
        unique=True,
        postgresql_where="supersedes_id IS NULL",
    )


def downgrade() -> None:
    op.drop_index("uq_review_decision_root", table_name="review_decisions")
    op.drop_index("uq_review_decision_supersedes", table_name="review_decisions")
    op.drop_constraint(
        "uq_observation_revision_original",
        "observation_revisions",
        type_="unique",
    )
    op.drop_index("uq_metric_observation_supersedes", table_name="metric_observations")
