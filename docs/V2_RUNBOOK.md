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

Web startup runs `alembic upgrade head`. That is safe for a new local install,
but an existing populated database must be backed up before an upgraded web
container is allowed to start.

### Fresh disposable gate

Use an explicit disposable database for migration and full integration tests:

```bash
docker compose exec -T postgres createdb -U postgres autoprism_v2_m6_gate
docker compose run --rm \
  -e DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres:5432/autoprism_v2_m6_gate \
  -e DATABASE_SYNC_URL=postgresql://postgres:postgres@postgres:5432/autoprism_v2_m6_gate \
  web alembic upgrade head
docker compose run --rm \
  -e AUTOPRISM_RUN_DB_TESTS=1 \
  -e DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres:5432/autoprism_v2_m6_gate \
  -e DATABASE_SYNC_URL=postgresql://postgres:postgres@postgres:5432/autoprism_v2_m6_gate \
  web python -m unittest discover -s tests -v
docker compose run --rm \
  -e DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres:5432/autoprism_v2_m6_gate \
  -e DATABASE_SYNC_URL=postgresql://postgres:postgres@postgres:5432/autoprism_v2_m6_gate \
  web alembic check
```

The 2026-08-09 final M6 gate passed 39/39 tests from a database created at zero
migrations. Never point this command at the populated development database.

### Populated database gate

1. Stop `web` and `worker` so no writer races the backup or migration.
2. Back up PostgreSQL and the artifact volume; record the actual paths,
   timestamps, sizes and SHA-256 values in the operator log.
3. Verify the PostgreSQL dump can be listed/read and the artifact archive is
   non-empty before continuing.
4. Run `alembic upgrade head` and `alembic check` against the populated
   database.
5. Query the immutable M6 audit and reconcile its counts with the unchanged
   historical observations.
6. Start the new `web` and `worker` only after these checks pass.

Manual migration checks:

```bash
docker compose exec web alembic current
docker compose exec web alembic upgrade head
docker compose exec web alembic check
```

Never test downgrades on the development or production database. Migration
`0005_v2_observation_lineage` deliberately rejects downgrade once immutable
lineage/manifest history exists. Use an empty disposable database and supply
both `DATABASE_URL` and `DATABASE_SYNC_URL` for any downgrade exercise.

### M6 lineage audit

```bash
docker compose exec -T postgres psql -U postgres -d autoprism -c \
  "SELECT key, details FROM lineage_backfill_audits WHERE key = '0005_observation_extraction_backfill';"
docker compose exec -T postgres psql -U postgres -d autoprism -c \
  "SELECT match_method, count(*) FROM observation_extraction_links GROUP BY match_method ORDER BY match_method;"
```

The backed-up 2026-08-09 database reported six historical target observations,
three `backfill_exact` links and three unresolved observations. The audit method
is `exact_output_match_only`. If panel, snapshot, model, prompt, time, numeric
value, citation or uniqueness does not match, the row must remain unresolved;
never hand-pick a likely extraction run.

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

The 2026-08-09 M6 operator record contains a pre-migration PostgreSQL dump at
`/private/tmp/autoprism_v2_pre_0005_20260809.dump` (841 KiB, SHA-256
`158de9f3543bbb82bdb1dfb23e26a666c8a67d8ca0050d598ea1830eb1e67cdd`)
and an archive of the unchanged artifact volume at
`/private/tmp/autoprism_v2_artifacts_20260809.tar.gz` (126 KiB, SHA-256
`adf89817cc8f347b88cc3639973be9a383b8982296380664e5eae5adfe90e469`).
The artifact archive was created after the database migration and was verified
to contain the three expected content-addressed files; this timing is recorded
explicitly rather than represented as a pre-migration artifact snapshot. These
local files are not committed. Future operators must record their own exact
backup evidence before upgrading.

## Release verification

```bash
cd frontend
npm ci
npm run typecheck
npm run build
npm audit
```

The M6 frontend typecheck, build and audit passed with zero reported
vulnerabilities. The full disposable-database backend suite passed 39/39.

Browser evidence is a separate required gate. If no browser runtime is
available, mark current screenshots, console inspection, responsive layout and
visual/interaction smoke as **pending**. Do not reuse an earlier screenshot or
console record as proof for the current worktree.

## API surface

- `/api/v2/sources`: pools, definitions, jobs, manual collection, human actions.
- `/api/v2/evidence`: snapshots, fragments, normalized multi-claim observation
  evidence, exact extraction lineage, audited revisions and original artifacts.
- `/api/v2/extractions`: model or deterministic schema-bound extraction;
  `evidence-extraction-v3` freezes the ordered input manifest.
- `/api/v2/verification`: calculations, source/artifact/publisher comparisons,
  review cases/decisions, trust assessments and current eligibility.
- `/api/v2/dashboards`: proposals, immutable versions and view payloads.
- `/api/v2/insights`: stored-input-only L2 creation and history.

OpenAPI documentation is served at `/docs`.
