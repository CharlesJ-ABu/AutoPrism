"""Recognize and preserve the V1 evidence chain after the V2 head.

This revision is intentionally shared with the frozen V1 branch. Keeping the
same revision identity lets a real local database move between the V1 runtime
and V2 without deleting, stamping over, or replaying historical data.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

revision = "0001_v1_evidence_chain"
down_revision = "8a9c3d4e5f60"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    # Never call the live application's full metadata from a historical
    # migration: later V2 models would be created ahead of their own revisions.
    # The baseline already creates the V1 tables; this revision only adds the
    # explicitly declared compatibility columns and evidence table below.

    inspector = inspect(bind)
    raw_columns = {
        column["name"] for column in inspector.get_columns("raw_intelligence")
    }
    additions = {
        "content_hash": sa.Column("content_hash", sa.String(64), nullable=True),
        "verification_status": sa.Column(
            "verification_status",
            sa.String(32),
            nullable=False,
            server_default="legacy_unverified",
        ),
        "fetched_at": sa.Column(
            "fetched_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        "revision": sa.Column(
            "revision",
            sa.Integer(),
            nullable=False,
            server_default="1",
        ),
        "supersedes_id": sa.Column(
            "supersedes_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("raw_intelligence.id", ondelete="SET NULL"),
            nullable=True,
        ),
        "capture_metadata": sa.Column(
            "capture_metadata",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        "processing_attempts": sa.Column(
            "processing_attempts",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        "processing_error": sa.Column(
            "processing_error",
            sa.Text(),
            nullable=True,
        ),
    }
    for name, column in additions.items():
        if name not in raw_columns:
            op.add_column("raw_intelligence", column)

    inspector = inspect(bind)
    for constraint in inspector.get_unique_constraints("raw_intelligence"):
        if constraint.get("column_names") == ["source_url"] and constraint.get("name"):
            op.drop_constraint(
                constraint["name"],
                "raw_intelligence",
                type_="unique",
            )

    index_names = {
        index["name"] for index in inspect(bind).get_indexes("raw_intelligence")
    }
    if "idx_raw_source_url" not in index_names:
        op.create_index("idx_raw_source_url", "raw_intelligence", ["source_url"])
    if "idx_raw_content_hash" not in index_names:
        op.create_index("idx_raw_content_hash", "raw_intelligence", ["content_hash"])

    if "intelligence_info_evidence" not in inspect(bind).get_table_names():
        op.create_table(
            "intelligence_info_evidence",
            sa.Column(
                "info_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("intelligence_info.id", ondelete="CASCADE"),
                primary_key=True,
            ),
            sa.Column(
                "raw_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("raw_intelligence.id", ondelete="CASCADE"),
                primary_key=True,
            ),
            sa.Column(
                "locator",
                postgresql.JSONB(),
                nullable=False,
                server_default=sa.text("'{}'::jsonb"),
            ),
            sa.Column("excerpt", sa.Text(), nullable=True),
        )

    op.execute(
        "UPDATE raw_intelligence "
        "SET verification_status = 'legacy_unverified' "
        "WHERE verification_status IS NULL"
    )


def downgrade() -> None:
    # Evidence history is intentionally not removed automatically.
    pass
