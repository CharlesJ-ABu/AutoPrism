"""Backfill explicit evidence links for legacy INFO rows."""

from alembic import op

revision = "0002_backfill_legacy_evidence"
down_revision = "0001_v1_evidence_chain"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO intelligence_info_evidence (info_id, raw_id, locator, excerpt)
        SELECT
            info.id,
            info.raw_id,
            '{"kind": "legacy_text_snapshot"}'::jsonb,
            left(raw.raw_content, 500)
        FROM intelligence_info AS info
        JOIN raw_intelligence AS raw ON raw.id = info.raw_id
        ON CONFLICT (info_id, raw_id) DO NOTHING
        """
    )
    op.execute(
        """
        UPDATE raw_intelligence
        SET verification_status = 'legacy_unverified'
        WHERE verification_status IS DISTINCT FROM 'legacy_unverified'
           OR verification_status IS NULL
        """
    )


def downgrade() -> None:
    pass
