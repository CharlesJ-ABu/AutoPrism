# AutoPrism V2 Release Checklist

Release scope: local-first V2 evidence cockpit on branch `v2`. Branch `main`
remains the unmodified, unauthenticated V1 local edition and is not a merge
target.

Current M6 state on 2026-08-09: backend, data migration and frontend static
gates pass. The current browser/visual gate has not run because this execution
environment has no browser runtime. M6 release closeout is therefore pending;
historical M1–M5 screenshots are not current acceptance evidence.

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
- [x] Validation rule `numeric-v2-source-artifact-publisher` requires explicit
  tolerances plus independent source, artifact and snapshot-frozen publisher
  identities.
- [x] Trust policy `trust-eligibility-v3-validation-replay` replays every peer's
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
- [ ] Capture current-worktree same-size V1/V2 desktop screenshots and complete
  desktop/mobile, console, responsive and interaction smoke. Browser runtime is
  currently unavailable.
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
- Three historical observations remain intentionally unresolved; pre-v3
  extraction runs cannot be retroactively promoted by attaching a new manifest.
- M7 still must implement the general unit/currency/time-basis conversion
  registry, deterministic rounding/error propagation and a trusted calculation
  engine policy. Decimal calculation runs remain UNVERIFIED in M6.
- Manual revisions remain ineligible until an evidence-bound human-attestation
  contract can be replayed.
- Safe UI DSL currently supports stack, metric, table and provenance; custom
  React source is stored but not executed.
- L2 is a deterministic stored-input evidence summary, not predictive or
  externally augmented analysis.
- M6's new browser screenshots, console inspection and visual/interaction smoke
  are pending because no browser runtime is available in the current
  environment.

None of these limitations is represented as complete in the UI or release
record.
