# AutoPrism V2 / SaaS TODO

## Completed closeout

The M6 current-worktree browser gate and the `trusted-insight-map-v1` dual-map
follow-up passed on 2026-08-10. Baselines and exact results are recorded under
`docs/visual-baselines/2026-08-10/` and `V2_TESTING.md`.

## M7 — Units, currency and uncertainty

- General deterministic unit, currency and time-basis conversion registry.
- Explicit conversion-run lineage that freezes source/target units, rates,
  effective timestamps, formulas and code/engine versions.
- Deterministic precision and rounding policies.
- Error bounds, propagation plans and reproducible error checks.
- A trusted deterministic calculation engine version and policy allowlist only
  after unit/conversion/error replay is complete.
- Migration, API, Trust, L2 and UI tests proving conversions cannot silently
  change comparison scope or introduce default values.

Until M7 is complete, Decimal calculation runs are stored as UNVERIFIED and no
unit/currency/error capability is represented as trusted.

## V2 next

- Google programmable search discovery with user-supplied configuration.
- Scheduler UI and refresh-policy execution.
- Expand safe UI DSL beyond metric/table/provenance to chart, timeline, map,
  heatmap, radar, ticker, and network components.
- Isolated custom React compile/preview/runtime with dependency allowlist,
  CSP, resource limits, and no ambient credentials.
- Source-pool editing and deletion (creation/registration/collection are connected).
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
