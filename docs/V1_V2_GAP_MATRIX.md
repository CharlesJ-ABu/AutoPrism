# AutoPrism V1 → V2 Gap and Acceptance Matrix

Current review date: 2026-08-10 (Asia/Shanghai)

This document is the working acceptance ledger for the `v2` branch. `main`
remains the frozen, unauthenticated V1 local edition and is used only as a
read-only comparison source.

## Audited baseline

The table below is the historical pre-M1 snapshot recorded on 2026-07-27. It is
retained to show the original gap and must not be read as current M6 status.

| Area | V1 evidence | Historical V2 evidence at `85a4597` | Historical conclusion |
|---|---|---|---|
| Product identity | Fixed top cockpit navigation, role switcher, globe/tactical map, dense four-column specialist panels, purple/cyan glass system | Purple/cyan palette and evidence terminal restored, but layout is a left-nav administration shell with no role switcher or situation map | Partial; V2 does not yet read as an unmistakable V1 upgrade |
| Frontend structure | Many specialized map/panel components, but tightly coupled to prototype stores and `/api/v1` | `App.tsx` contains application state, shell, panel rendering, evidence drawer and composer in one 387-line file | Fails component-system acceptance |
| Data presentation | Rich charts and domain-specific panels, but includes `NA`, fabricated/default values and weak lineage | Three real NHTSA panels, frozen Schema/UI DSL, artifact hashes and JSON Pointer evidence | V2 is materially more trustworthy but visually much less expressive |
| Dashboard lifecycle | Fixed single dashboard | List/switch/create/propose/create-version/view APIs and UI exist | Partial; revision browsing, editing and explicit draft/frozen lifecycle UI are missing |
| Dynamic panels | Fixed React components | Versioned `PanelDefinition`/`PanelVersion`, JSON Schema, UI DSL and optional custom source storage | Partial; current safe renderer only handles tables and custom React execution is explicitly unavailable |
| Acquisition | Prototype crawler and manual triggers; missing/incomplete paths | Source pools, policy checks, jobs, worker, immutable artifacts, HTML/PDF/CSV/XLSX/RSS/JSON parsing | Backend present; no user-facing source-pool/job/action workspace |
| Evidence | V1 INFO lineage can group outputs under the wrong L1 input | Snapshot → artifact → fragment → extraction is persisted and shown | Core path passes; drawer shows only the first evidence item and omits observation/calculation/validation/revision history |
| Corrections and review | No reliable append-only workflow | Immutable models/triggers, observation revisions, validation runs and review decisions | Backend present; UI absent |
| L2 | Prototype endpoint and unverified model output | Contract says stored eligible data only | Service/UI not implemented; must remain an explicit unavailable state |
| Compliance | Prototype crawler has no complete policy boundary | authorization/robots/terms/rate-limit preflight and human-action blocking | Core backend present; authenticated browser collection and credential vault intentionally unavailable |
| Tests | V1 build and crawler gaps are documented | 23 backend tests, migration checks, frontend build, Compose and browser record dated 2026-07-25 | Historical evidence only until re-run in the current worktree |
| Documentation | V1 PRD/architecture plus screenshots | V2 architecture, roadmap, security, testing and runbook | Historical gap; dedicated Schema/UI DSL, trust, testing and release documents now exist |

### Current delta through M9

- The V1-continuity cockpit and split component system remain implemented.
- `evidence-extraction-v3` now freezes exact ordered extraction inputs.
- Normalized observation evidence sets support multiple claims and fragments;
  direct observations use exact run/record/field associations.
- `numeric-v3-bounded-source-artifact-publisher` and
  `trust-eligibility-v4-bounded-conversion-replay` replace the earlier source-only and
  v1-era policy descriptions.
- Fresh and backed-up populated migration gates passed. The real six-observation
  audit produced 3 exact links and 3 unresolved without guessed backfill.
- The M6 disposable-PostgreSQL backend suite passed 39/39; the map milestone
  increased the current complete suite to 44/44.
- `geo-scope-v1`, immutable coordinate claims and `trusted-insight-map-v1`
  now power real 3D/2D maps without decorative database facts.
- `unit-registry-v1`, bounded Decimal values and immutable conversion runs now
  support replayable unit/direct-FX conversion and derived eligibility without
  default uncertainty or caller-supplied rates.
- New 1440×800 V1/V2 and 390×844 V2 baselines, console, responsive and
  visual/interaction smoke passed on the current bundle.
- The safe UI DSL now validates and renders bounded single-series charts and
  evidence-date timelines without synthetic points or placeholder events.
- Google source discovery now freezes credential-free normalized candidates;
  every result remains visibly unregistered until a human completes the trust
  and compliance registration form.

## Non-negotiable trust findings

- V1 values are not acceptable as V2 fixtures. Existing V1 content stays
  `legacy_unverified` and is excluded from trusted calculations and L2.
- A V2 map may render only geocoded database evidence. It must show an honest
  empty state when no verified coordinates exist; it may not infer or scatter
  decorative source markers.
- Missing values remain missing. The UI must not turn them into zero, `NA`,
  random values or apparently measured placeholders.
- Custom React source can be frozen and hashed, but must not be presented as
  executable until the isolated allowlisted runtime exists.
- Credentials remain ephemeral environment/request inputs. No credential is
  persisted in a dashboard version, repository file, log or screenshot.

## Phased delivery and gates

| Milestone | Deliverable | Acceptance evidence | Status |
|---|---|---|---|
| M0 Baseline | Full audit, V1/V2 same-size desktop baseline, responsive/console baseline, executable gap ledger | This document, 1440×800 browser captures, clean `v2` status, baseline test logs | Complete |
| M1 Cockpit foundation | Tokens, reusable Shell/Panel/Button/Status/Drawer/AsyncState, role/view switcher, truthful situation map, split feature modules | Type check/build, 1440×800 and 390×844 screenshots, current-bundle console clean, full evidence drawer smoke | Complete |
| M2 Dashboard lifecycle | Version history, clone/edit as new immutable version, explicit draft/frozen states, structured Schema/UI DSL editor and validation feedback | API integration tests, browser history/edit/confirmation smoke, Schema-bound DSL unit tests | Complete |
| M3 Operations workspace | Source pools, source registration, compliant collection jobs, human-action queue, extraction trigger and clear unavailable states | Collector integration tests and browser source/compliance/job/action smoke | Complete |
| M4 Trust workspace | All evidence fragments, observations, calculations, validation runs, corrections and review decisions connected in UI | Migration/domain/API tests plus end-to-end provenance replay | Complete for current trust contract; eligibility/L2 remains M5 |
| M5 Trusted L2 and release | Stored-input-only L2 or explicit unavailable state, full regression, docs/changelog/release gate and fast-forward push | Compose run, migration cycle, frontend audit/build, visual comparison and release checklist | Complete |
| M6 Exact lineage and trust replay | v3 input manifest, normalized claim evidence, exact origins, three-axis validation and dynamic peer replay | `0005`, fresh/populated gates, 6/3/3 audit, 39/39 backend plus 2026-08-10 current visual closeout | Complete |
| M6.1 Trusted dual insight map | Schema-bound geography, immutable coordinate citations, current-only L2 map contract and 3D/2D engines | `0006`, fresh/populated gates, 44/44 backend, frontend/Compose/browser baselines | Complete |
| M7 Units/currency/error semantics | Deterministic conversions, precision/rounding, error propagation and trusted calculation policy | Replay, migration, API/Trust/L2 and browser evidence | Complete; dimensional multiply/divide and triangular FX explicitly deferred |
| M8 Safe visual DSL | Schema-bound single-series line/bar/area charts and evidence-date timelines with truthful empty states | 55/55 backend, frontend type/build, isolated non-empty desktop/mobile smoke | Complete; multi-series/map remain explicitly unsupported |
| M9 Compliant discovery | Ephemeral Google credentials, immutable normalized candidates and manual registration gate | `0008`/`0009`, fresh/cycle/populated gates, 59/59 backend, frontend audit/build and responsive smoke | Complete; no saved key and no automatic collection |

## Feature acceptance ledger

Status meanings: **done** is proven in the current implementation; **partial**
has a real path with missing required behavior; **missing** has no usable path;
**deferred** is visibly unavailable and must not be represented as complete.

| Requirement | Backend | UI | Tests | Overall |
|---|---:|---:|---:|---:|
| Main dashboard list and switch | done | done | partial | partial |
| Create main dashboard | done | done | partial | partial |
| LLM child-panel design | done | done | partial | partial |
| JSON Schema and UI DSL | done with field-bound chart/timeline validation | structured editor plus safe renderers | done | done for current safe subset |
| Manual edit and save new version | done | done | done | done |
| Freeze component/Schema/prompt/model | done | explicit draft/publish workflow | done | done |
| Import/collection | done for direct URL/API sources | connected with compliance gate | done | done for supported collectors |
| Search discovery | request-only Google provider plus immutable normalized candidates | explicit authorization and manual registration handoff | done | done for first provider; candidates are never auto-collected |
| Evidence viewing | all fragments plus INFO provenance | connected cockpit drawer | done | done |
| Revision history | append-only with DB fork prevention | view and create replacement | done | done |
| Cross-source validation | explicit tolerances plus independent source/artifact/frozen-publisher rule | view and run | done | done |
| Human review | append-only single-head decisions | queue and superseding decisions | done | done; actor identity remains deferred |
| L1 → INFO lineage | normalized claim evidence plus exact extraction association for new v3 rows | complete trace; unresolved history is explicit | done | done for v3; 3 historical rows intentionally unresolved |
| Deterministic calculations | bounded Decimal engine, normalized trusted inputs and replay records | view and run eligible plans | done | add/subtract/percent/weighted-average eligible after full replay |
| Unit conversion registry | fixed versioned dimension/semantic registry | compatible-target selection and conversion history | done | no free aliases or caller factors |
| L2 stored-data-only analysis | normalized eligible inputs and immutable hash | connected with explicit unavailable state | done | done for deterministic evidence summary |
| V1-style insight map | immutable `geo-scope-v1` plus current `trusted-insight-map-v1` replay | real 3D globe/2D tactical engines and honest states | done | done; reference data correctly has zero qualified features |
| Authenticated collection | deferred | explicit TODO required | policy tests only | deferred |
| Encrypted credential vault | SaaS-only deferred | explicit TODO required | missing | deferred |
| Isolated custom React runtime | source storage only | explicit TODO required | hash test only | deferred |

## Historical baseline findings and resolution

1. The existing Compose project was still serving the V1 frontend image when
   first inspected from this worktree. Runtime validation must always rebuild
   from the exact `v2` source before screenshots are accepted. The M1 V2
   baseline was captured only after an exact-source rebuild.
2. The V1 baseline visibly contains `NA` and values without reproducible
   evidence. Those screenshots are visual references only, never data fixtures.
3. The original V2 audit strip counted panels with evidence, not evidence
   items, and labeled all results as an “完整证据链”. M1 replaced this with
   precise Schema/provenance states.
4. The original composer label “保存冻结版本” sent `state: draft`. M2 separated
   draft save from explicit acknowledged frozen publication.
5. The original V2 drawer exposed only the first fragment. M1 expanded it to
   every returned fragment and M4 added field observations, revision chains,
   calculation runs, validation runs and review decisions. M6 added normalized
   multi-claim evidence and exact observation-to-extraction associations. Three
   historical observations remain unresolved because no unique exact match
   exists; this is an explicit truthful state, not pending guessed backfill.

## M1 verification record

- Frontend `npm run typecheck`: passed.
- Frontend production build: passed; 1,585 modules transformed.
- Locked dependency install inside the frontend image: 75 packages audited,
  zero vulnerabilities.
- Backend fast suite: 23 tests passed, 5 database tests skipped as designed.
- Disposable database full suite: 23/23 passed, including all 5 integration
  tests.
- Empty disposable database upgrade: baseline through
  `0002_backfill_legacy_evidence` passed.
- Disposable downgrade to `8a9c3d4e5f60`, re-upgrade and `alembic check`:
  passed with no drift.
- Preserved real database at `0002_backfill_legacy_evidence`: Web startup and
  `alembic check` passed without deleting or rewriting history.
- Browser desktop 1440×800: 3 panels, 3 Schema-valid extractions, no horizontal
  overflow, all-evidence drawer rendered, no current-bundle warnings/errors.
- Browser mobile 390×844: body width 384 px, 3 panels, 4 perspective controls,
  no error state, no horizontal overflow.

## M2 verification record

- Dashboard history API returns ordered immutable versions with panel counts.
- Version detail API returns complete child-panel contracts.
- Version editor reconstructs full Schema, UI DSL, optional component source,
  visualization contract, prompt version, model settings and source-pool binding.
- Draft save and frozen publication both create new versions; no update endpoint
  or UI path mutates an existing version.
- Publication remains disabled until the user acknowledges append-only behavior.
- Browser smoke loaded a 10,175-character historical version payload, displayed
  the custom-runtime limitation, and verified the publish control changed from
  disabled to enabled only after confirmation. It did not create test history
  in the real database.
- Safe UI DSL validation rejects unknown node types, nonexistent fields,
  non-array table fields and columns absent from the array-item Schema.
- Frontend type check/build passed; full disposable-database suite passed 24/24.

## M3 verification record

- UI lists real source pools, registered sources, collection jobs and
  human-action requests from V2 APIs.
- Users can register HTML, PDF, CSV, Excel, RSS and JSON API sources and must
  explicitly enter both global reputation and topic authority. The backend no
  longer supplies an unverified `0.5` default.
- Creating a collection job is disabled until the user confirms authorization
  and accepts the pause-on-restriction policy.
- Declared auth requirements and configured robots restrictions remain backend
  policy gates. Terms/legal review and rate scheduling are explicitly marked
  metadata/manual or deferred; the UI states that CAPTCHA and access blocks
  cannot be bypassed.
- Successful jobs expose a real Schema-bound extraction action targeting an
  existing frozen panel version. Deterministic mappings run in code; missing
  model credentials return an explicit error.
- Browser smoke loaded 3 registered official sources, 6 historical jobs and
  zero open human actions. All 3 collection buttons were disabled before the
  compliance acknowledgement and enabled only after it. No test collection was
  added to the real database.
- Local file upload, authenticated browser collection, CAPTCHA continuation,
  scheduler execution and encrypted credential storage remain explicit TODOs.

## M4 verification record

- Evidence terminal now loads real INFO observations, immutable corrections,
  deterministic calculation runs, validation runs and complete review-decision
  chains filtered by the current frozen panel version.
- Schema validity is displayed separately from fact trust. Existing reference
  observations remain truthfully UNVERIFIED; the UI does not infer eligibility.
- Validation tolerances are mandatory. Duplicate inputs and mismatched panel,
  Schema, unit, currency, period, geography or dimensions are rejected.
- A validation can pass only with at least two independent source definitions;
  repeated observations from one source create NEEDS_REVIEW.
- Calculation APIs reject duplicate or incompatible scope, require explicit
  output units, and require a unit plan for multiply/divide.
- Migration `0003_v2_lineage_uniqueness` adds observation/revision/review
  single-chain constraints and halts instead of rewriting any pre-existing
  fork.
- Real preserved database upgrade and `alembic check` passed. Disposable
  downgrade/re-upgrade/check passed. Full integration suite passed 24/24.
- Browser desktop and 390×844 mobile smoke displayed the trust state boundary,
  2 real UNVERIFIED observations, source hosts, hashes, explicit tolerances and
  zero validation/review runs without horizontal overflow or real-data writes.

## M5 verification record

- Added append-only `TrustAssessment`, `L2Insight` and normalized
  `L2InsightInput` records with database immutability triggers.
- Eligibility replays stored artifact bytes and fragment text hashes, rejects
  superseded/legacy/rejected observations, requires a PASSED independent-source
  validation and checks deterministic calculation lineage where applicable.
- L2 accepts only current heads whose latest assessment is ELIGIBLE. It freezes
  observation and assessment foreign keys, input hash, deterministic engine and
  contract versions; duplicate input sets are idempotent.
- Integration tests prove a passed two-source observation can produce an
  eligible assessment and L2 record, a one-source validation cannot, and
  revising the eligible input makes the old assessment stale and blocks a new
  current L2 run.
- Preserved real database upgraded to `0004_v2_trust_assessments_l2` without
  data deletion; disposable downgrade/re-upgrade and drift checks passed.
- Real reference UI shows 0 ELIGIBLE, two NOT ASSESSED observations and a
  disabled “L2 当前不可用” state. No production assessment or insight was
  written during browser smoke.
- Legacy `reset.py` and `reset_l2.py` now refuse destructive resets and direct
  operators to Alembic plus disposable test databases.

## M6 verification record

- Added migration `0005_v2_observation_lineage`, normalized observation evidence
  sets/links, exact extraction associations and `evidence-extraction-v3` frozen
  input manifests.
- Database constraints reject incomplete evidence cardinality, multiple stored
  origins, inconsistent revision pairs and UPDATE/DELETE/TRUNCATE of immutable
  history. Trust eligibility separately requires exactly one replayable origin.
- Validation now freezes and replays independent source-definition, artifact
  and snapshot publisher identities under
  `numeric-v2-source-artifact-publisher`.
- Trust assessments use `trust-eligibility-v3-validation-replay`; every peer is
  dynamically rechecked for current-head, evidence, artifact/locator and origin
  integrity. Old rules and stale peers cannot power `trusted_only` or L2.
- The real PostgreSQL database was backed up before non-destructive upgrade.
  All six target observations remain: 3 unique `backfill_exact`, 3 unresolved,
  with `exact_output_match_only` audit and no guessed run assignment.
- A fresh database upgraded through the entire graph and passed drift checks.
  The final full disposable-PostgreSQL backend suite passed 39/39; frontend
  typecheck, production build and dependency audit passed.
- Current browser verification completed on 2026-08-10. New same-size desktop
  screenshots, 390×844 no-overflow checks, console inspection, 3D/2D switching
  and evidence/acquisition drawer smoke passed. Artifacts are stored under
  `docs/visual-baselines/2026-08-10/`.
- General unit/currency/time conversion, precision/rounding, error propagation
  and trusted calculation-engine enablement remain M7.

## M6.1 trusted-map verification record

- Migration `0006_v2_trusted_insight_map` passed zero-to-head, empty
  downgrade/re-upgrade and `alembic check`.
- A restored copy of the real six-observation `0005` database upgraded without
  changing the observation count or normalized-value digest; no legacy
  coordinate was inferred.
- The complete disposable-PostgreSQL backend suite passed 44/44.
- The integration path proves two independent source/artifact/publisher inputs,
  exact coordinate citations, Trust geography replay, deterministic L2 map
  creation and immediate feature removal after a newer failed assessment.
- Frontend typecheck/build and production dependency audit passed; DeckGL and
  globe chunks are lazy-loaded and the audit reported zero vulnerabilities.
