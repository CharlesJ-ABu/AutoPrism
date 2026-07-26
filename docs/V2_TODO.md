# AutoPrism V2 / SaaS TODO

## V2 next

- Google programmable search discovery with user-supplied configuration.
- General deterministic unit, currency, and time-basis conversion registry.
- Scheduler UI and refresh-policy execution.
- Expand safe UI DSL beyond metric/table/provenance to chart, timeline, map,
  heatmap, radar, ticker, and network components.
- Isolated custom React compile/preview/runtime with dependency allowlist,
  CSP, resource limits, and no ambient credentials.
- Source-pool editing and deletion (creation/registration/collection are now connected).
- Append-only trust assessments/eligibility policy that can promote a current
  observation without mutating it; review-queue UI is now connected.
- Direct `MetricObservation → ExtractionRun` lineage and multi-fragment
  observation evidence relations.
- Identity-backed reviewer/reviser principals; current actor labels are
  explicitly self-asserted.
- L2 service that selects only eligible stored observations and records its
  complete input set.
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
