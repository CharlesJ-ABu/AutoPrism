# AutoPrism V2 / SaaS TODO

## Completed closeout

The M6 current-worktree browser gate and the `trusted-insight-map-v1` dual-map
follow-up passed on 2026-08-10. Baselines and exact results are recorded under
`docs/visual-baselines/2026-08-10/` and `V2_TESTING.md`.

M11 research orchestration is complete: the LLM plans bounded discovery and
registered-source collection from a frozen database inventory, while every
tool action remains individually authorized and all facts still enter through
the ordinary evidence chain.

M12 is complete: evidence-bound model narratives consume only current eligible
observations and preserve exact citations/hashes without changing trust state;
custom React presentation runs in the bounded opaque-origin sandbox.

M13 release regression is complete: the final database/static/Compose/API/
browser/log gates and same-size V1/V2 visual comparison passed. Further work
below is deliberate post-V2 or SaaS scope.

M14 is complete: safe charts accept a bounded Schema-backed grouping field and
the trusted Shell map now has local search, type filters and an accessible
feature index. Neither path adds calculation, geocoding or trust authority.

M15 is complete: a frozen panel may declare one bounded `trusted_map` only when
its Schema carries executable `geo-scope-v1`. It consumes the existing current
trusted L2 read model and adds no panel-data coordinate shortcut.

## M7 follow-ups

M7's fixed registry, bounded Decimal engine, direct/inverse evidence-bound FX,
immutable conversion lineage and Trust replay are implemented. Remaining scope
is deliberately separate:

- dimensional algebra for multiply/divide and compound units;
- triangular FX, if a future policy can freeze and replay every rate leg;
- a reviewed FX-rate discovery/import workflow (never automatic nearest-rate use);
- derived geography propagation under its own evidence contract;
- standalone replay-report endpoints for external auditors.

## V2 next

- No unacknowledged V2 release blocker remains. New capability work must begin
  as a separately scoped milestone and preserve the current trust boundaries.

- Additional discovery providers only after they implement the same ephemeral
  credential, normalized URL, immutable result and manual-registration boundary.
- Encrypted saved search-provider credentials remain SaaS-only; local V2 asks
  for the Google API key and CX on each discovery request.
- Expand safe UI DSL beyond the implemented metric/table/bounded multi-series-
  chart/timeline/trusted-map/provenance subset to heatmap, radar, ticker and
  network components. Mixed-unit/multi-axis charts require a separate contract.
- Expand the custom runtime beyond its current empty dependency allowlist only
  after each library has a reviewed immutable version and security contract.
- Source-pool editing and deletion (creation/registration/collection are connected).
- Calendar/cron schedules, maintenance windows and per-domain shared rate
  budgets; M10 intentionally supports bounded fixed intervals only.
- Identity-backed reviewer/reviser principals; current actor labels are
  explicitly self-asserted.
- Evidence-bound manual-revision attestation; current revisions remain
  append-only and visible but cannot become trusted eligible.
- Optional evidence-bound narrative L2 provider after authentication and model
  governance; deterministic stored-input L2 is implemented.
- Artifact garbage-collection report for files left orphaned by failed
  transactions; never delete without an explicit reviewed policy.
- Remove transitional V1-development columns from `review_cases` only after a
  data migration and compatibility audit.

## Explicitly deferred

- Playwright/authenticated browser collection.
- CAPTCHA continuation. CAPTCHA always pauses for human action.
- Automatic handling of anti-bot challenges.

## SaaS branch

- Authentication, organization/team membership, RBAC, and dashboard visibility.
- One PostgreSQL database per organization.
- Encrypted per-organization credential vault.
- S3-compatible immutable artifact storage and retention policies.
- Organization model-provider and search-provider configuration.
- Quotas, billing, audit logs, abuse controls, backups, disaster recovery.
- Secure public publishing and isolated execution of user component code.
