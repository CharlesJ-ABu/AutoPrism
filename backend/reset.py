"""Disabled legacy reset entry point.

V2 evidence and history are append-only. Use Alembic migrations and a separate
disposable database for tests; never reset the preserved local database.
"""


if __name__ == "__main__":
    raise SystemExit(
        "Database reset is disabled in AutoPrism V2. "
        "Use Alembic against a disposable test database."
    )
