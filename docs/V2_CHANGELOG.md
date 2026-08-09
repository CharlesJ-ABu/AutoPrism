# AutoPrism V2 Changelog

All entries apply only to the `v2` branch. `main` remains the frozen V1 local
edition and is not a merge target.

## Unreleased

### M6.1 — Trusted dual insight map (2026-08-10)

- Added `geo-scope-v1` Schema metadata for evidence-bound point, line and zone
  geometry. Coordinates must be required source fields with explicit
  `degree_latitude`/`degree_longitude` units; no geocoding or default location
  is inferred.
- Added migration `0006_v2_trusted_insight_map` and immutable
  `ObservationGeography`/`ObservationGeographyEvidence` histories with
  deferred extraction-output, citation, field-path and manifest constraints.
- Added independent Trust replay for the frozen geographic scope and citations.
  Existing non-empty pre-contract geography causes migration to stop for
  reviewed handling rather than being promoted automatically.
- Bumped deterministic stored-input L2 to the map-aware v2 contract and froze
  `trusted-insight-map-v1` features. Current reads dynamically replay every
  referenced assessment and geography; a newer ineligible assessment removes
  the feature without erasing historical L2.
- Restored a real 3D globe plus DeckGL 2D tactical view with industrial/cyber/
  ghost modes, selected-feature evidence entry, and explicit loading/error/
  empty states. The local grid texture contains no synthetic country or event
  data.
- Passed 44/44 disposable-PostgreSQL backend tests, fresh and populated `0006`
  migration gates, empty downgrade/re-upgrade, frontend typecheck/build and
  zero-vulnerability dependency audit.
- Captured new 1440×800 V1/V2 and 390×844 V2 baselines; 3D/2D, evidence drawer,
  acquisition drawer and mobile overflow smoke passed with no console warning
  or error.

### M6 — Exact observation lineage and fail-closed trust replay (2026-08-09)

- Added migration `0005_v2_observation_lineage` with normalized
  `ObservationEvidenceSet`/`ObservationEvidenceLink` claims and exact
  `ObservationExtractionLink` run, record ordinal and field-path origins.
- Added `evidence-extraction-v3`. Every new run freezes an ordered
  `ExtractionRunInputSet`/`ExtractionRunInput` manifest, text and entry hashes,
  manifest count/hash and complete input payload hash in the same transaction.
- Added deferred database constraints for evidence cardinality, contiguous
  ordinals, complete metric/dimension claims, extraction-output agreement,
  revision consistency and at most one stored extraction/revision/calculation
  origin. Current Trust separately requires exactly one replayable origin.
  Immutable history now rejects UPDATE, DELETE and TRUNCATE.
- Made migration backfill exact-only. The backed-up populated database retained
  all six target observations: three unique matches became `backfill_exact` and
  three stayed unresolved. The audit records `exact_output_match_only`; no run,
  value or evidence was guessed or rewritten.
- Added `numeric-v2-source-artifact-publisher` validation with independent
  source-definition, artifact and snapshot-frozen publisher identities.
  Validation replay recomputes comparison key, rule result/state and every
  peer's current-head/evidence/origin integrity.
- Added `trust-eligibility-v3-validation-replay` and dynamic current semantics
  for assessment APIs, `trusted_only` observations and L2. Old rules and stale
  peers fail closed.
- Limited trusted extraction authority to exact deterministic v3 replay.
  Non-deterministic model output remains an explicit unverified candidate;
  manual revisions and Decimal calculations also remain ineligible until their
  future attestation/unit/error contracts exist.
- Hardened malformed historical JSON, boolean Schema, NaN/Infinity,
  calculation parameter, revision scope, citation and snapshot-state paths so
  they return explicit ineligible/422 outcomes instead of becoming trusted or
  raising unhandled errors.
- Passed both fresh and populated migration gates. The final disposable
  PostgreSQL backend suite passed 39/39; frontend typecheck, production build
  and dependency audit passed with zero reported vulnerabilities.
- Browser runtime was unavailable in the current environment. New M6 same-size
  V1/V2 screenshots, responsive/console inspection and visual interaction smoke
  remain an explicit release-closeout gate; older screenshots were not reused
  as current evidence.
- Deferred general unit/currency/time conversion, rounding and error
  propagation, and trusted calculation-engine enablement to M7.

### M1 — Intelligence cockpit foundation

- Added a read-only V1/V2 gap and acceptance ledger.
- Split the frontend monolith into Cockpit Shell, dashboard panel, verified
  situation map, evidence drawer, dashboard composer and reusable UI
  primitives.
- Added shared color, spacing, radius, shadow and transition tokens.
- Restored the V1 role/view-switching language while keeping views honest:
  filters only select stored panels and never generate filler content.
- Added a globe-like evidence situation layer that plots only coordinates
  explicitly stored in evidence locators. Missing coordinates now produce a
  clear no-evidence state.
- Replaced ambiguous `NA`/zero fallbacks with “未提供” or explicit no-data
  states.
- Expanded the evidence terminal from one fragment to every fragment returned
  by the dashboard view.
- Corrected the LLM composer lifecycle wording: it saves a draft version and no
  longer claims that the draft is frozen.
- Added V1 migration revision compatibility to V2, allowing preserved local
  databases at `0002_backfill_legacy_evidence` to start without reset or
  stamping.
- Aligned V2 legacy ORM metadata with the preserved V1 evidence columns and
  indexes; migration autogeneration now reports no drift.

### M2 — Immutable dashboard lifecycle

- Added ordered dashboard-version history and complete version-detail API
  coverage.
- Added a version manager that opens any historical version and reconstructs a
  complete editable contract.
- Added separate append-only actions for saving a new draft and publishing a
  new frozen version. Publication requires explicit acknowledgement.
- Preserved and exposed component source/hash, JSON Schema, UI DSL,
  visualization contract, extraction prompt/version, model settings and source
  pool binding in revision payloads.
- Added executable safe UI DSL validation bound to the panel JSON Schema.
- Updated the dynamic renderer to resolve metric and table fields from the
  frozen UI DSL instead of assuming `record_count` and `records`.
- Documented the supported safe subset and the isolated custom React boundary.

### M3 — Compliant acquisition workspace

- Connected source-pool, source registration, collection-job and human-action
  APIs to a cockpit operations drawer.
- Added an explicit authorization/compliance acknowledgement before collection
  controls become available.
- Removed implicit `0.5` source-reputation and topic-authority defaults; both
  values are now required human inputs.
- Added job status, snapshot IDs, failure/policy details and a Schema-bound
  extraction action for successful snapshots.
- Kept declared login requirements, configured robots restrictions and access
  blocks in the pause-for-human path; no bypass path was added. Terms/legal
  review and scheduling remain explicitly manual/deferred.

### M4 — Auditable trust workspace

- Added panel-scoped observation, revision, calculation, validation and review
  history APIs and connected them to the evidence terminal.
- Added append-only observation corrections, deterministic calculation plans,
  explicit-tolerance validation and superseding human-review decisions.
- Prevented false cross-source passes by requiring independent source
  definitions and complete metric/unit/currency/time/geography/dimension scope.
- Added non-destructive database constraints that reject observation and
  review-decision lineage forks; migrations halt on pre-existing conflicts
  instead of choosing or deleting history.
- Required explicit validation tolerances and calculation output units/unit
  plans; duplicate and incompatible inputs are rejected.
- Added the normative data-trust contract and separated Schema validity from
  evidence, validation, human approval and future trusted eligibility.
- Added accessible dialog semantics, Escape closing and desktop/mobile trust
  workspace states.

### M5 — Trust eligibility and stored-input L2

- Added append-only trust assessments that replay artifact/text integrity,
  current revision status, independent-source validation and calculation
  lineage without mutating observations.
- Added immutable, normalized L2 input references to eligible observations and
  assessments, plus deterministic input hashes and engine/contract versions.
- Added a stored-input-only L2 evidence summary. It never browses, predicts,
  fills missing values or delegates mathematics to a model.
- Added truthful eligibility/L2 UI. The real reference dashboard remains at
  zero eligible inputs and exposes a disabled unavailable state.
- Added integration coverage for eligibility, ineligible same-source data,
  idempotent L2 creation and invalidation after observation revision.
- Disabled legacy destructive reset scripts and added the release checklist.
