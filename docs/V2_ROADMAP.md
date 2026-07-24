# AutoPrism V2 Delivery Roadmap

## Status at branch creation

V1 is a visual prototype with one batch of legacy data. Its frontend does not
currently build, its full crawler path contains a missing method, and its INFO
lineage groups many outputs under the first L1 record. All V1 data is therefore
retained but classified as `legacy_unverified`.

## Phase 0 — Foundation (complete)

- Define stable L1 / INFO / L2 terminology.
- Add content-addressed artifact storage.
- Add snapshot, evidence-fragment, observation, calculation, validation, and
  review persistence contracts.
- Add deterministic hashing, locator validation, arithmetic, and numeric
  cross-source validation.
- Replace startup `create_all` evolution with real Alembic migrations.
- Add a V2 health/readiness surface.

Exit: the append-only evidence chain has migration and integration tests.

## Phase 1 — Real acquisition (core complete)

- Define source pool, source reputation, topic authority, and refresh policies.
- Add policy preflight: authorization, robots, terms/rate-limit metadata, and
  explicit human-action states.
- Implement collector contracts for HTML, PDF, CSV/Excel, and RSS.
- Persist original bytes before parsing.
- Add Google discovery behind a provider interface; allow user-supplied keys.
- Queue acquisition and processing through Redis and an independent worker.
- Keep authenticated browser automation as a documented TODO.

Exit: a source can be discovered, captured, hashed, parsed, and reproduced
without an LLM inventing source material.

Google discovery remains pending; direct registered sources are operational.

## Phase 2 — Extraction and verification (core complete)

- Define versioned panel JSON Schema extensions for units, enums, required
  fields, time/geography, aggregation, and visualization mappings.
- Introduce provider-neutral model adapters and structured-output validation.
- Require every extracted core field to carry an evidence locator.
- Add deterministic units, currency, and time-basis normalization.
- Execute model-proposed calculations with a restricted calculation engine.
- Add cross-source comparison policies and human review queues.
- Preserve corrections through `supersedes_id`.

Exit: every trusted number can be traced, recalculated, and independently
reviewed.

General unit/currency conversion tables remain pending. Deterministic decimal
calculations, tolerance checks, review cases, append-only decisions, and
schema-bound extraction are operational.

## Phase 3 — Automotive proof (complete)

- Select three automotive panels with authoritative public sources.
- Rebuild their INFO contracts and visualizations against verified data.
- Ensure L2 analyzes only eligible stored data and never browses.
- Add historical snapshot labels and provenance UI.

Exit: three panels run end-to-end on real data in Docker.

Completed with three live NHTSA API panels and a provenance UI.

## Phase 4 — Dynamic dashboards (foundation complete)

- Generate a dashboard proposal from a title alone.
- Allow users to edit panels, schemas, sources, refresh policies, prompts, and
  visualization choices before saving.
- Version dashboards and panels; keep historical INFO bound to its schema.
- Build a safe UI DSL and component registry.
- Support editable custom React templates in an isolated preview/runtime.
- Freeze schema and component code per saved version while allowing explicit
  prompt/model configuration revisions.

Exit: users can create, save, switch, and audit multiple research dashboards.

Title-to-proposal, editable structured JSON, immutable save, dashboard
switching, and metric/table/provenance rendering are operational. The full UI
DSL component registry and isolated custom React runtime remain pending.

## Phase 5 — SaaS branch (not started)

- Adopt the stable V2 evidence core.
- Provision one PostgreSQL database per organization.
- Add organization/user authentication and role-based authorization.
- Add encrypted credential vault and organization model/search settings.
- Replace local artifacts with S3-compatible object storage.
- Add private, organization-shared, and public dashboard visibility.
- Add quotas, billing, audit logs, abuse controls, and secure code execution.

Exit: a tenant-isolated public SaaS deployment passes security and recovery
testing.
