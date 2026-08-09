# AutoPrism V2 / SaaS TODO

## Completed closeout

The M6 current-worktree browser gate and the `trusted-insight-map-v1` dual-map
follow-up passed on 2026-08-10. Baselines and exact results are recorded under
`docs/visual-baselines/2026-08-10/` and `V2_TESTING.md`.

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

- Additional discovery providers only after they implement the same ephemeral
  credential, normalized URL, immutable result and manual-registration boundary.
- Encrypted saved search-provider credentials remain SaaS-only; local V2 asks
  for the Google API key and CX on each discovery request.
- Expand safe UI DSL beyond the implemented metric/table/single-series-chart/
  timeline/provenance subset to map, heatmap, radar, ticker, network and
  evidence-safe multi-series components.
- Isolated custom React compile/preview/runtime with dependency allowlist,
  CSP, resource limits, and no ambient credentials.
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
