# AutoPrism V2 Delivery Roadmap

## V2.0 release status

The M5 local-first V2 release and M6 exact-lineage release are complete on
branch `v2`. On 2026-08-10 the current browser runtime closed the outstanding
M6 visual gate with new same-size V1/V2 screenshots, responsive/console checks
and interaction smoke. Historical screenshots were not substituted.

M6 includes the V1-continuity cockpit, immutable dashboard lifecycle, compliant
direct-source operations, exact observation/extraction lineage, auditable
INFO/validation/review workflows, append-only dynamically replayed trust
eligibility and stored-input-only deterministic L2. See
[V2_RELEASE_CHECKLIST.md](V2_RELEASE_CHECKLIST.md) for the open visual gate and
known limitations. The trusted-map follow-up and the bounded numeric M7
milestone are complete. The safe UI DSL now includes bounded single-series
charts and evidence-date timelines. M9 adds credential-ephemeral Google source
discovery with immutable candidate history and a mandatory manual registration
gate. Scheduling, additional visual types and isolated custom-component
execution remain the next V2 work.

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

Google discovery and direct registered sources are operational. Discovery
candidates remain unregistered until a human supplies the source trust and
compliance contract; no discovery result triggers collection automatically.

## M9 — Compliant source discovery (complete)

- Added request-only Google Programmable Search credentials and bounded result
  paging (one to ten candidates per run).
- Froze credential-free discovery runs and normalized candidate results under
  migrations `0008_v2_source_discovery` and
  `0009_v2_discovery_cardinality`; candidate sets cannot be appended later.
- Rejected unsafe/credential-bearing result URLs and sanitized upstream errors.
- Added explicit authorization, zero-result and manual-registration states in
  the operations drawer.
- Passed fresh, empty cycle and populated-copy migration gates, 59/59 backend
  tests, frontend static/dependency gates and desktop/mobile browser smoke.

Exit: discovery produces only an auditable shortlist. Registration, policy
review and collection remain separate human-authorized steps.

## Phase 2 — Extraction and verification (core complete)

- Define versioned panel JSON Schema extensions for units, enums, required
  fields, time/geography, aggregation, and visualization mappings.
- Introduce provider-neutral model adapters and structured-output validation.
- Require every extracted core field to carry an evidence locator.
- Freeze explicit unit, currency and time-basis scope and reject implicit
  conversion. M7 now supplies the deterministic registry and evidence-bound
  conversion runs.
- Execute model-proposed calculations with a restricted calculation engine.
- Add cross-source comparison policies and human review queues.
- Preserve corrections through `supersedes_id`.

Exit: every number admitted by the current trust policy can be traced,
replayed and independently validated.

Deterministic decimal calculations, bounded tolerance checks, unit/currency
conversion runs, review cases, append-only decisions, and schema-bound
extraction are operational. Triangular FX and dimensional multiply/divide are
still deliberately unsupported.

## Phase 3 — Automotive proof (complete)

- Select three automotive panels with authoritative public sources.
- Rebuild their INFO contracts and visualizations against real-source,
  evidence-backed, Schema-valid data.
- Ensure L2 analyzes only eligible stored data and never browses.
- Add historical snapshot labels and provenance UI.

Exit: three panels run end-to-end on real data in Docker.

Completed with three live NHTSA API panels and a provenance UI. Their outputs
are real-source and Schema-valid, not automatically trusted. The L2 service
now accepts only current ELIGIBLE observation heads. The current reference
dataset lacks independent-source validation, so its UI truthfully reports L2
unavailable instead of generating an unverified insight.

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
switching, and metric/table/chart/timeline/provenance rendering are
operational. Additional allowlisted visual types and the isolated custom React
runtime remain pending.

## M6 — Exact lineage and trust replay (complete)

- Add normalized multi-claim/multi-fragment observation evidence sets.
- Bind direct observations to exact extraction run, record ordinal and field
  path.
- Freeze `evidence-extraction-v3` ordered input manifests and replay hashes.
- Require deterministic extraction replay for trust eligibility.
- Validate independent source, artifact and snapshot-frozen publisher identity
  under `numeric-v2-source-artifact-publisher`.
- Dynamically recheck every validation peer and assessment under
  `trust-eligibility-v3-validation-replay`.
- Upgrade both fresh and backed-up populated databases through migration `0005`.
- Backfill only unique exact matches; preserve the real six-observation result
  as 3 `backfill_exact` and 3 unresolved without guessing.
- Pass the final disposable-PostgreSQL backend suite 39/39 and frontend
  typecheck/build/dependency audit.

Exit status: implementation/data/static gates pass. The 2026-08-10 browser run
also passed desktop/mobile screenshots, console inspection, 3D/2D switching,
evidence/operations drawers and horizontal-overflow inspection.

## M6.1 — Evidence-bound dual insight map (complete)

- Added `geo-scope-v1`, binding point/flow/zone geometry to required frozen
  Schema fields with explicit latitude/longitude units.
- Added immutable observation-geography and ordered claim-evidence tables under
  migration `0006_v2_trusted_insight_map`.
- Added `trusted-insight-map-v1` to deterministic L2 output and a current-only
  replaying map read model.
- Replaced the decorative map with lazy-loaded `react-globe.gl` and DeckGL
  3D/2D views, three visual modes, honest empty/error/loading states and an
  evidence-chain entry point.
- Passed fresh and populated migration gates, 44/44 backend tests, frontend
  static/dependency gates and current browser visual/interaction smoke.

Exit: no map feature is returned when its L2 input assessment becomes stale or
when geography, citations, extraction manifest or frozen output cannot replay.

## M7 — Units, currency and error semantics (complete)

- Added `unit-registry-v1` with fixed dimensions, semantic kinds and exact
  Decimal scale factors; arbitrary aliases and user-provided factors are rejected.
- Added immutable conversion runs that freeze input observations and current
  assessments, direct/inverse evidence-bound FX rates, exact time basis, plan,
  result, quantum and replay hash.
- Added `decimal-v2-bounded` with an isolated 50-digit HALF_EVEN context and
  conservative interval propagation. Unknown uncertainty fails closed.
- Added `numeric-v3-bounded-source-artifact-publisher` and
  `trust-eligibility-v4-bounded-conversion-replay`; derived observations become
  eligible only after independent replay of all current input assessments.
- Added migration `0007_v2_numeric_conversion`, API/UI conversion workflows,
  strict Schema extensions and fresh/populated database regression gates.

Exit: derived observations can become trust eligible without implicit
conversion, hidden rounding or unverifiable uncertainty.

Explicit boundary: v1 does not implement triangular FX, live-rate discovery,
“closest” rate selection, or dimensional algebra for multiply/divide. These
paths return an unavailable/validation state instead of guessing.

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
