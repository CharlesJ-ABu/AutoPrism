# AutoPrism V1 → V2 Gap and Acceptance Matrix

Audit date: 2026-07-27 (Asia/Shanghai)

This document is the working acceptance ledger for the `v2` branch. `main`
remains the frozen, unauthenticated V1 local edition and is used only as a
read-only comparison source.

## Audited baseline

| Area | V1 evidence | V2 evidence at `85a4597` | Conclusion |
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
| Documentation | V1 PRD/architecture plus screenshots | V2 architecture, roadmap, security, testing and runbook | Strong foundation; UI DSL, trust contract and current release checklist need dedicated documents |

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
| M4 Trust workspace | All evidence fragments, observations, calculations, validation runs, corrections and review decisions connected in UI | Migration/domain/API tests plus end-to-end provenance replay | Pending |
| M5 Trusted L2 and release | Stored-input-only L2 or explicit unavailable state, full regression, docs/changelog/release gate and fast-forward push | Compose run, migration cycle, frontend audit/build, visual comparison and release checklist | Pending |

## Feature acceptance ledger

Status meanings: **done** is proven in the current implementation; **partial**
has a real path with missing required behavior; **missing** has no usable path;
**deferred** is visibly unavailable and must not be represented as complete.

| Requirement | Backend | UI | Tests | Overall |
|---|---:|---:|---:|---:|
| Main dashboard list and switch | done | done | partial | partial |
| Create main dashboard | done | done | partial | partial |
| LLM child-panel design | done | done | partial | partial |
| JSON Schema and UI DSL | done with field-bound DSL validation | structured JSON editor | done | done for safe subset |
| Manual edit and save new version | done | done | done | done |
| Freeze component/Schema/prompt/model | done | explicit draft/publish workflow | done | done |
| Import/collection | done for direct URL/API sources | connected with compliance gate | done | done for supported collectors |
| Evidence viewing | done | first fragment only | partial | partial |
| Revision history | done for observations | missing | done | partial |
| Cross-source validation | done | missing | done | partial |
| Human review | done | missing | partial | partial |
| L1 → INFO lineage | done for reference panels | partial | done | partial |
| Deterministic calculations | done | missing | done | partial |
| Unit conversion registry | missing | missing | missing | missing |
| L2 stored-data-only analysis | contract only | missing | missing | missing |
| Authenticated collection | deferred | explicit TODO required | policy tests only | deferred |
| Encrypted credential vault | SaaS-only deferred | explicit TODO required | missing | deferred |
| Isolated custom React runtime | source storage only | explicit TODO required | hash test only | deferred |

## Baseline observations requiring correction

1. The existing Compose project was still serving the V1 frontend image when
   first inspected from this worktree. Runtime validation must always rebuild
   from the exact `v2` source before screenshots are accepted. The M1 V2
   baseline was captured only after an exact-source rebuild.
2. The V1 baseline visibly contains `NA` and values without reproducible
   evidence. Those screenshots are visual references only, never data fixtures.
3. The current V2 audit strip counts panels with evidence, not evidence items,
   and labels all results as an “完整证据链”. This overstates trust and must be
   replaced with precise states.
4. The composer label “保存冻结版本” sends `state: draft`. UI wording and the
   persisted state conflict and must be separated into draft save versus
   explicit frozen publication.
5. The current drawer exposes the first evidence fragment only and therefore
   cannot prove field-level lineage for multi-field/multi-source records.
   M1 now renders every evidence fragment returned by the view API; M4 still
   needs field-to-fragment mappings, observations, calculations and validation
   history in the same workflow.

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
- Login, terms, robots, rate-limit and access restrictions remain backend
  policy gates; the UI states that CAPTCHA and access blocks cannot be bypassed.
- Successful jobs expose a real Schema-bound extraction action targeting an
  existing frozen panel version. Deterministic mappings run in code; missing
  model credentials return an explicit error.
- Browser smoke loaded 3 registered official sources, 6 historical jobs and
  zero open human actions. All 3 collection buttons were disabled before the
  compliance acknowledgement and enabled only after it. No test collection was
  added to the real database.
- Local file upload, authenticated browser collection, CAPTCHA continuation,
  scheduler execution and encrypted credential storage remain explicit TODOs.
