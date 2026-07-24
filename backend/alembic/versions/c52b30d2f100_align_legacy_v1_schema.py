"""align legacy V1 schema without deleting legacy tables

Revision ID: c52b30d2f100
Revises: a46a24af8bbf
Create Date: 2026-07-25
"""
from typing import Sequence, Union

from alembic import op


revision: str = "c52b30d2f100"
down_revision: Union[str, None] = "a46a24af8bbf"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "UPDATE raw_intelligence "
        "SET target_panel_ids = '[]'::jsonb "
        "WHERE target_panel_ids IS NULL"
    )
    op.execute(
        "ALTER TABLE raw_intelligence "
        "ALTER COLUMN target_panel_ids SET NOT NULL"
    )
    op.execute(
        "ALTER TABLE raw_intelligence "
        "ALTER COLUMN target_panel_ids DROP DEFAULT"
    )
    op.execute("DROP INDEX IF EXISTS ix_strategic_insights_role")


def downgrade() -> None:
    # Restores the legacy runtime-patch shape, but intentionally does not
    # recreate the redundant strategic-insights index.
    op.execute(
        "ALTER TABLE raw_intelligence "
        "ALTER COLUMN target_panel_ids DROP NOT NULL"
    )
    op.execute(
        "ALTER TABLE raw_intelligence "
        "ALTER COLUMN target_panel_ids SET DEFAULT '[]'::jsonb"
    )
