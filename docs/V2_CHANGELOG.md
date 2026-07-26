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
