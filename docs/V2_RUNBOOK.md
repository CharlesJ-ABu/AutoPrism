# AutoPrism V2 Runbook

## Local Docker startup

```bash
cp backend/.env.example backend/.env
docker compose up -d --build
docker compose ps
```

Expected services: `frontend`, `web`, `worker`, `postgres`, and `redis`.
Frontend, web, PostgreSQL, and Redis expose health checks. The worker is a
long-running queue consumer.

```bash
curl http://localhost:8000/health
curl http://localhost:8000/ready
```

`/ready` checks both PostgreSQL and Redis. The frontend proxies `/api/*` to the
web service.

## Load the automotive reference dashboard

```bash
docker compose exec web python -m app.seeds.automotive --collect
```

The command is definition-idempotent: it reuses the dashboard, version,
panels, source pool, and sources. Each `--collect` run deliberately creates new
collection jobs and immutable snapshots so historical captures are never
overwritten.

## Database migrations

Web startup runs `alembic upgrade head`. For manual operation:

```bash
docker compose exec web alembic current
docker compose exec web alembic upgrade head
docker compose exec web alembic check
```

Never test downgrades on the development or production database. Use an
explicit disposable database and supply both `DATABASE_URL` and
`DATABASE_SYNC_URL`.

## Collection worker

The API writes collection job IDs to `autoprism:v2:collection` in Redis. The
worker dequeues one ID at a time and runs:

1. static authorization/policy checks;
2. optional robots evaluation;
3. bounded streaming fetch;
4. content-addressed artifact persistence;
5. parser and evidence-fragment persistence;
6. success, failure, or human-action state.

A missing credential, access block, or policy rejection does not retry around
the restriction; it creates a human-action request.

## Backup

Back up both:

- PostgreSQL, which stores metadata, contracts, observations, hashes, and history;
- the `artifact_data` Docker volume, which stores original bytes by SHA-256.

Neither side is sufficient alone. Verify restored artifacts by calling the
download endpoint, which recomputes the file hash.

## API surface

- `/api/v2/sources`: pools, definitions, jobs, manual collection, human actions.
- `/api/v2/evidence`: snapshots, fragments, observations, audited observation
  revisions, and original artifacts.
- `/api/v2/extractions`: model or deterministic schema-bound extraction.
- `/api/v2/verification`: calculations, comparisons, review cases and decisions.
- `/api/v2/dashboards`: proposals, immutable versions and view payloads.

OpenAPI documentation is served at `/docs`.
