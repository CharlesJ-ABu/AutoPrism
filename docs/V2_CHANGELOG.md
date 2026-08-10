# AutoPrism V2 Changelog

All entries apply only to the `v2` branch. `main` remains the frozen V1 local
edition and is not a merge target.

## Unreleased

### M15 — panel-level trusted map UI DSL (2026-08-10)

- Added the bounded `trusted_map` DSL node, requiring an executable
  `geo-scope-v1` Panel Schema, one node per panel, 1–100 `max_features`, a
  boolean index flag and no unknown properties.
- Wired panel maps only to current replayed `trusted-insight-map-v1` features
  whose frozen panel keys include the displayed PanelVersion. Added explicit
  loading/error/empty/truncation states, feature selection and evidence entry.
- Fitted the 2D tactical camera from immutable returned geometry so narrow
  panels do not open on an unrelated fixed world center. No coordinates or
  trust state are derived or changed.
- Passed fresh zero-to-head migration, 73/73 database suite, `alembic check`,
  frontend type/build, zero-vulnerability audit, rebuilt Compose and clean
  desktop/390px browser gates. QA features remained isolated and were removed.

### M14 — safe multi-series analysis and trusted-map navigation (2026-08-10)

- Extended the safe chart DSL with optional Schema-bound `series_field` and a
  2–12 `max_series` bound. Invalid/missing grouping fields, unsupported limits
  and standalone `max_series` declarations fail closed at version save.
- Added deterministic multi-series line, area and grouped-bar rendering from
  stored row order. The renderer discloses truncation and never aggregates,
  interpolates or creates missing points.
- Added client-side search, display-type filtering, no-match recovery and a
  keyboard-accessible index for already replayed trusted map features. These
  controls cannot create, geocode, modify or promote a feature.
- Passed a fresh zero-to-head disposable database and the 72/72 suite, frontend
  type/build and zero-vulnerability audit. Real-empty plus isolated non-empty
  desktop/390px browser gates had no console errors or horizontal overflow;
  no QA feature was written to the real database.

### M13 — V2 release regression and handoff (2026-08-10)

- Re-ran the 72/72 disposable-PostgreSQL suite, final frontend type/build,
  production dependency audit, container dependency check and real-database
  Alembic drift gate.
- Confirmed all six Compose services healthy, eight core read paths returned
  HTTP 200, recent web/worker/scheduler/frontend logs contained no error,
  exception, traceback or fatal entry, and real history remained unchanged.
- Captured final V1/V2 same-size 1440×800 cockpit and AI Research records plus
  the 390×844 no-overflow gate. The sidebar/overlay fix and clean console held.
- Release remains `v2`-only. No PR or merge to the frozen unauthenticated V1
  `main` branch was created.

### M12 — isolated custom runtime and evidence-bound interpretation (2026-08-10)

- Added `custom-react-sandbox-v1`: source/hash verification, worker compilation,
  opaque-origin iframe, no imports/network, safe virtual DOM and 250 ms execution
  termination. Browser gates proved READY, blocked fetch and killed infinite loop.
- Added migration `0013_v2_evidence_interpretations` with immutable narratives
  and ordered observation/assessment inputs, deferred pair/cardinality checks,
  hash integrity and populated downgrade refusal.
- Added strict structured interpretation: current eligible inputs only, exact
  claim citations, no uncited/new numeric values, request-only credentials and
  dynamic `currently_grounded` replay without changing trust state.
- Passed 72/72 V2 backend tests, migration cycle/drift, frontend type/build,
  zero-vulnerability audit, real backed-up additive migration and desktop/mobile
  browser gates. Existing 6 observations and 1 dashboard were unchanged.

### M11 — LLM trustworthy research orchestration (2026-08-10)

- Added migration `0012_v2_llm_research_runs` with immutable research runs,
  frozen model plans, allowlisted discovery/collection actions and append-only
  single-chain action events. Deferred checks freeze action count and ordinals;
  UPDATE/DELETE/TRUNCATE and populated downgrade fail closed.
- Added a provider-neutral planner. It receives only a credential-free database
  source inventory and may propose bounded search queries, exact registered
  source keys, analysis targets, interpretation questions and limitations. It
  cannot claim tool execution or establish factual findings.
- Froze prompt/system hash, canonical input manifest, output hash,
  provider/model metadata and action specifications. API reads rebuild the
  actions; an altered or incomplete chain is integrity-failed and cannot run.
- Reused Google discovery and the collection queue behind explicit per-action
  authorization. Ephemeral model/search credentials are not stored and
  compliance blocks remain human-action states.
- Added the cockpit AI Research workspace with plan-vs-fact copy, hashes,
  targets/limitations, per-action gates and responsive sidebar-safe layout.
- Passed 67/67 backend tests, migration/static/dependency gates and real-empty/
  isolated-nonempty desktop/390px browser smoke. A readable backup preceded
  the additive real migration; 6 observations and 1 dashboard were unchanged.

### M10 — Auditable refresh scheduling (2026-08-10)

- Added migrations `0010_v2_refresh_scheduler` and
  `0011_v2_schedule_source_guard` with append-only, single-head refresh-policy
  revisions, immutable per-interval dispatch history and database-enforced
  same-source schedule/job/dispatch references.
- Added a dedicated Scheduler service. Interval mode requires an explicit local
  authorization attestation, enforces a 15-minute minimum, dispatches only the
  current bucket and never backfills missed runs.
- Reused the ordinary collection queue and policy checks; disabled sources and
  in-flight jobs produce explicit skipped dispatches instead of duplicate work.
- Hardened worker claiming with a database row lock so duplicate Redis delivery
  cannot execute the same running/succeeded/blocked job twice.
- Added API and cockpit schedule version/history workflows with manual mode,
  authorization-gated interval mode and honest empty states.
- Full-screen composer and drawer workflows now retract and deactivate the
  cockpit sidebar, lock background scrolling and restore the shell cleanly on
  close, preventing the navigation from covering forms.
- Passed 62/62 backend tests twice, including a fresh zero-to-0011 database;
  fresh/cycle/populated downgrade gates, frontend type/build,
  zero-vulnerability audit, real backed-up migration, six-service Compose and
  desktop/390px browser smoke passed with no console warning/error.

### M9 — Compliant source discovery (2026-08-10)

- Added Google Programmable Search as the first bounded discovery provider.
  The API key and raw search-engine ID are request-only; only a one-way
  configuration hash, query and normalized results enter immutable history.
- Added append-only discovery runs and candidate tables under migrations
  `0008_v2_source_discovery` and `0009_v2_discovery_cardinality`, including
  database guards against update, delete, truncate and late candidate inserts.
  Populated downgrade fails instead of erasing discovery history.
- Normalized candidates to credential-free HTTP(S) URLs, rejected user-info
  and credential-like query parameters, de-duplicated results, and treated file
  type as an untrusted registration suggestion.
- Added a cockpit discovery workspace with explicit authorization, password
  input, honest zero-result states and a manual “bring to registration form”
  action. Discovery never auto-registers or auto-collects a source.
- Passed 59/59 tests on disposable PostgreSQL, fresh/cycle/populated migration
  gates, frontend type/build, zero-vulnerability production dependency audit,
  Compose smoke and 390×844 responsive inspection.

### M8 — Safe chart and timeline UI DSL (2026-08-10)

- Expanded the non-executable UI DSL with Schema-bound line/bar/area charts and
  evidence-date timelines. Unknown properties, invalid fields and misleading
  metric units fail validation instead of being silently ignored.
- Added dedicated responsive dashboard renderers with explicit no-data states.
  They consume only stored array rows, reject non-finite chart values and never
  synthesize points, trends, dates or events.
- Passed the 55/55 disposable-PostgreSQL suite, frontend type/build and isolated
  non-empty desktop/mobile browser smoke; restored Compose to the unchanged
  real one-dashboard database after the visual check.
- Kept multi-series, panel-level map and executable custom React outside the
  accepted contract until their runtime and evidence semantics are complete.

### M7 — Bounded numeric, unit and currency replay (2026-08-10)

- Added migration `0007_v2_numeric_conversion` with immutable canonical numeric
  values, uncertainty evidence, normalized calculation inputs and conversion runs.
  Historical observations are not backfilled with invented values or error bounds.
- Added `unit-registry-v1`: exact fixed Decimal scales, dimension and semantic-kind
  checks, and no free-form aliases or caller-provided conversion factors.
- Added `decimal-v2-bounded` with isolated 50-digit HALF_EVEN arithmetic,
  explicit output quantum and conservative interval propagation. Unknown error
  fails closed instead of becoming zero.
- Preserved JSON decimals end to end with exact Decimal parsing and database
  serialization; high-precision source values no longer pass through binary floats.
- Added `time-scope-v1` so instant, period-end and period-average authority comes
  from required cited ISO timestamps with explicit offsets, never retrieval time.
- Added evidence-bound direct/inverse FX conversion. Rates must be existing,
  current eligible `currency_ratio` observations with exact matching instant,
  period-end or period-average scope; live, closest and triangular rates are absent.
- Upgraded cross-source validation to
  `numeric-v3-bounded-source-artifact-publisher` and Trust to
  `trust-eligibility-v4-bounded-conversion-replay`. Calculation and conversion
  eligibility independently replays every frozen current input assessment.
- Added unit-registry/conversion APIs and an operational cockpit conversion tab.
  The UI never accepts a numeric factor or rate from the user.
- Kept dimensional multiply/divide unavailable until a versioned algebra exists.
  No unsupported operation is represented as trusted.

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
