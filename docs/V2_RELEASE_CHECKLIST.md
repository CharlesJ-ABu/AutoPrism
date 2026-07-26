# AutoPrism V2 Release Checklist

Release scope: local-first V2 evidence cockpit on branch `v2`. Branch `main`
remains the unmodified, unauthenticated V1 local edition and is not a merge
target.

## Required gates

- [x] V1/V2 frontend, backend, migrations, tests and documentation audited.
- [x] V1 visual identity retained through shared tokens, cockpit Shell, role
  perspectives, situation layer, dense panels, drawers and feedback states.
- [x] Main dashboard creation, immutable versions, Schema/UI DSL editing,
  source registration, collection jobs, extraction and evidence viewing use
  live V2 APIs.
- [x] Every displayed reference metric can resolve to source URL, retrieval
  time, artifact SHA-256 and locator.
- [x] Observation revisions and review decisions are append-only and protected
  against lineage forks.
- [x] Calculation uses deterministic Decimal code with explicit units/plans.
- [x] Cross-source validation requires explicit tolerances and independent
  sources.
- [x] Trust eligibility is an append-only assessment; it does not mutate
  observations or confuse Schema validity with fact trust.
- [x] L2 accepts only current ELIGIBLE observation heads and persists normalized
  observation/assessment references plus an input hash.
- [x] Legacy reset scripts cannot drop preserved data.
- [x] Real historical database upgraded non-destructively; `alembic check`
  reports no drift.
- [x] Disposable migration downgrade/re-upgrade passed.
- [x] Backend full integration suite, frontend type check/build and Compose
  health checks passed.
- [x] Desktop and 390×844 browser smoke passed with clean console and honest
  empty/unavailable states.
- [x] Remote `v2` updates are fast-forward only. No PR or merge to `main`.

## Truthful current reference state

The bundled local reference dashboard has real NHTSA snapshots and
Schema-valid deterministic extractions. Its current duplicated observations do
not constitute two independent sources, so it has zero ELIGIBLE observations
and L2 is visibly unavailable. This is the expected trustworthy result, not a
release failure.

## Known limitations

- No authentication, RBAC or identity-backed reviewer actor in the local
  edition.
- User authorization confirmation is a UI gate; immutable authorization
  attestations are pending.
- Terms/legal review, rate scheduling and redirect-domain re-authorization are
  manual/deferred.
- Authenticated browser collection, CAPTCHA continuation and credential vault
  are deferred.
- Observation-to-extraction direct FK and multi-fragment observation evidence
  relation are pending.
- Unit/currency conversion registry and error propagation are pending.
- Safe UI DSL currently supports stack, metric, table and provenance; custom
  React source is stored but not executed.
- L2 is a deterministic stored-input evidence summary, not predictive or
  externally augmented analysis.

None of these limitations is represented as complete in the UI.
