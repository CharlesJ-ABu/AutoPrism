"""Compatibility marker for databases previously opened by the V2 branch.

The V2 migration with this revision has already applied its own schema changes.
V1 does not replay or reverse those changes; it only uses this marker as a safe
parent for the V1 evidence-chain migration.
"""

revision = "8a9c3d4e5f60"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
