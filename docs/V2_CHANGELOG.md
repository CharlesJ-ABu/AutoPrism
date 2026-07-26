# AutoPrism V2 Changelog

All entries apply only to the `v2` branch. `main` remains the frozen V1 local
edition and is not a merge target.

## Unreleased

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
