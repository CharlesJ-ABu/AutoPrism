"""Disabled legacy L2 reset entry point.

Historical legacy and V2 insights must not be dropped to apply schema changes.
"""


if __name__ == "__main__":
    raise SystemExit(
        "L2 reset is disabled in AutoPrism V2. "
        "Apply non-destructive Alembic migrations instead."
    )
