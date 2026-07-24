"""scope snapshot uniqueness to a source definition

Revision ID: 1f4c9178d220
Revises: c52b30d2f100
Create Date: 2026-07-25
"""
from typing import Sequence, Union

from alembic import op


revision: str = "1f4c9178d220"
down_revision: Union[str, None] = "c52b30d2f100"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint(
        "uq_source_snapshot_capture",
        "source_snapshots",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_source_snapshot_capture",
        "source_snapshots",
        ["source_definition_id", "retrieved_at", "artifact_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_source_snapshot_capture",
        "source_snapshots",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_source_snapshot_capture",
        "source_snapshots",
        ["source_key", "retrieved_at", "artifact_id"],
    )
