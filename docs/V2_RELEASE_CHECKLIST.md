# AutoPrism V2 Release Checklist

Release scope: local-first V2 evidence cockpit on branch `v2`. Branch `main`
remains the unmodified, unauthenticated V1 local edition and is not a merge
target.

Current state on 2026-08-10: M6 lineage and its visual closeout pass. The
evidence-bound dual-map follow-up and M7 bounded numeric/conversion milestone
pass backend, migration, frontend, Compose and browser gates. M8 safe charts/
timelines and M9 compliant discovery also pass their scoped gates. Historical
M1–M5 screenshots were not reused as current acceptance evidence.

## Required gates

- [x] V1/V2 frontend, backend, migrations, tests and documentation audited.
- [x] V1 visual identity retained in code through shared tokens, cockpit Shell,
  role perspectives, situation layer, dense panels, drawers and feedback states.
- [x] Main dashboard creation, immutable versions, Schema/UI DSL editing,
  source registration, collection jobs, extraction and evidence viewing use
  live V2 APIs.
- [x] `evidence-extraction-v3` freezes a non-empty ordered input manifest,
  input/entry/text hashes, prompt/model/panel contract and output.
- [x] Every new `evidence-extraction-v3` direct INFO observation has a normalized evidence set and exact
  extraction-run/record/field association; claim links support multiple
  fragments without changing historical rows.
- [x] Every displayed reference metric can resolve to source URL, retrieval
  time, artifact SHA-256, text hash and locator.
- [x] Observation revisions and review decisions are append-only and protected
  against lineage forks; human approval does not replace replayable trust proof.
- [x] Validation rule `numeric-v3-bounded-source-artifact-publisher` requires explicit
  tolerances plus independent source, artifact and snapshot-frozen publisher
  identities.
- [x] Trust policy `trust-eligibility-v4-bounded-conversion-replay` replays every peer's
  current-head, evidence and origin integrity and rejects old rules,
  non-deterministic extraction and unsupported calculation/revision authority.
- [x] Trust eligibility is append-only and dynamically rechecked; it does not
  mutate observations or confuse Schema validity with fact trust.
- [x] L2 accepts only current ELIGIBLE observation heads and persists normalized
  observation/assessment references plus an input hash.
- [x] Legacy reset scripts cannot drop preserved data.
- [x] Fresh disposable database upgraded to `0005_v2_observation_lineage` with
  no drift and the final full backend suite passed 39/39.
- [x] The real populated database was backed up and upgraded non-destructively;
  all six target observations remain, with 3 exact links and 3 unresolved.
- [x] No unresolved row was matched by proximity, ordering, a default value or
  other guess; the immutable audit records `exact_output_match_only`.
- [x] Frontend `npm run typecheck`, `npm run build` and `npm audit` passed with
  zero reported vulnerabilities.
- [x] Captured current-worktree same-size V1/V2 desktop screenshots and
  completed desktop/mobile, console, responsive and interaction smoke.
- [x] Migration `0006_v2_trusted_insight_map` passed fresh, empty
  downgrade/re-upgrade and backed-up populated-copy gates without inferring any
  legacy coordinates.
- [x] `trusted-insight-map-v1` exposes only current assessment/geography replay;
  a stale assessment removes a feature while preserving immutable L2 history.
- [x] Migration `0007_v2_numeric_conversion` preserves legacy observations
  without inventing numeric/error rows and adds immutable numeric, calculation
  input and conversion histories.
- [x] `unit-registry-v1`, `decimal-v2-bounded` and `conversion-v1-bounded`
  enforce fixed units, explicit HALF_EVEN quantum and conservative uncertainty.
- [x] `numeric-v3-bounded-source-artifact-publisher` compares intervals and
  `trust-eligibility-v4-bounded-conversion-replay` dynamically replays all
  direct and derived input assessments.
- [x] Currency conversion references a current eligible database rate with an
  exact time basis; no caller factor, live/closest lookup or triangular path exists.
- [x] Final M7 suite passed 55/55 on disposable PostgreSQL; zero-to-head,
  empty downgrade/re-upgrade, populated-copy and drift gates passed.
- [x] Real Compose database upgraded to `0007` after a readable backup; six
  observations and their digest were unchanged, with zero inferred M7 rows.
- [x] Desktop/mobile conversion-workspace smoke passed with no horizontal
  overflow and no browser console warning/error.
- [x] Safe UI DSL chart/timeline contracts reject invalid fields, units,
  unsupported properties and multi-series declarations; the complete backend
  suite remains 55/55.
- [x] Non-empty chart/timeline rendering passed desktop and 390×844 browser
  smoke using only the isolated integration database. Compose was restored to
  the real one-dashboard database after the check.
- [x] Migrations `0008_v2_source_discovery` and
  `0009_v2_discovery_cardinality` add immutable credential-free discovery
  runs/candidates and freeze candidate cardinality; populated downgrade refuses
  to erase history.
- [x] Google discovery keeps the API key and raw CX out of persistence, rejects
  credential-bearing result URLs and never auto-registers or auto-collects.
- [x] Final M9 suite passed 59/59 on disposable PostgreSQL; fresh, empty cycle,
  populated-copy and drift gates passed. The real observation digest and single
  dashboard were unchanged after the backed-up upgrade.
- [x] M9 frontend type/build and production dependency audit passed; desktop
  and 390×844 discovery empty-state smoke showed no horizontal overflow.
- [x] Recorded M6 implementation commit `2b9bd54`; immediately before the
  release-record commit, `origin/v2...HEAD` was `0 1` and the remote head
  `ccb30e9` was an ancestor. Push only by fast-forward; do not create a PR or
  merge from `v2` to `main`.

## Truthful current reference state

The populated database contains six historical target observations. Migration
`0005` could prove exact direct extraction lineage for three and preserved the
other three as unresolved. Unresolved records retain compatibility evidence but
are not assigned a guessed run or upgraded to current `evidence-extraction-v3`.

The bundled NHTSA dashboard contains real snapshots and Schema-valid
deterministic outputs. Schema-valid, validation-PASSED and trust-eligible remain
separate states. Same-source or otherwise incomplete provenance correctly
leaves zero eligible inputs and L2 unavailable rather than producing a false
insight.

## Known limitations

- No authentication, RBAC or identity-backed reviewer actor in the local
  edition.
- User authorization confirmation is a UI gate; immutable authorization
  attestations are pending.
- Terms/legal review, rate scheduling and redirect-domain re-authorization are
  manual/deferred.
- Authenticated browser collection, CAPTCHA continuation and credential vault
  are deferred product capabilities.
- Local Google discovery requires the user to provide the API key and CX for
  every request. Saved/encrypted provider credentials are not implemented.
- Three historical observations remain intentionally unresolved; pre-v3
  extraction runs cannot be retroactively promoted by attaching a new manifest.
- Dimensional multiply/divide, compound units, triangular FX and derived
  geography remain unavailable; current code rejects rather than approximates them.
- Manual revisions remain ineligible until an evidence-bound human-attestation
  contract can be replayed.
- Safe UI DSL supports stack, metric, table, bounded single-series chart,
  evidence-date timeline and provenance. Map and multi-series panel nodes are
  still unavailable; custom React source is stored but not executed.
- L2 is a deterministic stored-input evidence summary, not predictive or
  externally augmented analysis.
- General panel-level `map` remains outside the safe UI DSL; the implemented
  Shell map has its own `trusted-insight-map-v1` contract.
- Multi-series charts remain outside the current safe contract; unsupported
  declarations are rejected rather than silently rendered as one series.

None of these limitations is represented as complete in the UI or release
record.
