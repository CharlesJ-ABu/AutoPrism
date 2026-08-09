"""Bind schedule dispatch references to one source.

Revision ID: 0011_v2_schedule_source_guard
Revises: 0010_v2_refresh_scheduler
"""

from alembic import op


revision = "0011_v2_schedule_source_guard"
down_revision = "0010_v2_refresh_scheduler"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_collection_job_id_source",
        "collection_jobs",
        ["id", "source_definition_id"],
    )
    op.create_foreign_key(
        "fk_schedule_dispatch_schedule_source",
        "schedule_dispatches",
        "source_refresh_schedules",
        ["schedule_id", "source_definition_id"],
        ["id", "source_definition_id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_schedule_dispatch_job_source",
        "schedule_dispatches",
        "collection_jobs",
        ["collection_job_id", "source_definition_id"],
        ["id", "source_definition_id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_schedule_dispatch_job_source",
        "schedule_dispatches",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_schedule_dispatch_schedule_source",
        "schedule_dispatches",
        type_="foreignkey",
    )
    op.drop_constraint(
        "uq_collection_job_id_source",
        "collection_jobs",
        type_="unique",
    )
