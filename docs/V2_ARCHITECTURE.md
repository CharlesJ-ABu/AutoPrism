# AutoPrism V2 Architecture

## Product boundary

AutoPrism V2 is a local-first intelligence evidence platform. The fixed
27-panel automotive dashboard remains the first template, but the platform is
not defined by that template.

A future main dashboard is a versioned research design containing:

- versioned child-panel definitions;
- a JSON Schema data contract for every child panel;
- a visualization contract;
- a source pool and refresh policy;
- versioned extraction prompts and model settings;
- either a safe UI DSL template or an isolated custom React component.

The V2 implementation order is:

1. reliable acquisition and evidence lineage;
2. deterministic normalization, calculation, and cross-validation;
3. review workflow and immutable correction history;
4. dynamic dashboard and panel design;
5. isolated custom visualization templates.

Browser automation and authenticated Playwright collection are explicitly
deferred. Current collectors target HTML, PDF, CSV/Excel, RSS, and JSON APIs.

## Data levels

- **L1**: immutable acquired source material and its capture metadata.
- **INFO**: structured observations extracted according to a versioned panel
  JSON Schema. Every material value links to exact evidence.
- **L2**: strategic insights generated only from stored, eligible L1/INFO
  records. L2 does not browse or silently add external facts.

Existing V1 records are retained as `legacy_unverified` and are excluded from
trusted calculations and L2 by default.

## Evidence chain

```text
Source
  -> SourceSnapshot (one retrieval event)
  -> EvidenceArtifact (content-addressed immutable bytes)
  -> EvidenceFragment (page/cell/selector/text-span locator)
  -> MetricObservation (raw and normalized value)
  -> CalculationRun (deterministic, replayable operation)
  -> ValidationRun (cross-source agreement)
  -> ReviewCase (only when automation cannot resolve)
```

Corrections never overwrite observations. A correction creates a new
observation whose `supersedes_id` points at the previous observation and an
`ObservationRevision` audit record captures the reason and actor. ORM guards
reject accidental mutation in application code, while PostgreSQL triggers
reject direct `UPDATE` and `DELETE` operations on evidence and version tables.

## Trust rules

A core metric is not trusted unless:

- the original artifact is retained and its SHA-256 matches;
- its source URL and retrieval time are known;
- its publication or observation time is known or explicitly marked unknown;
- a locator can reproduce the evidence fragment;
- units, currencies, time basis, and geographic scope are explicit;
- calculations are performed by deterministic code and can be replayed;
- cross-source validation passes, or a human review approves it.

LLMs may discover sources, extract candidates, propose formulas, and explain
results. LLMs do not execute authoritative arithmetic or invent missing values.

## Storage and deployment

V2 local mode uses PostgreSQL for metadata, a local content-addressed
filesystem for artifacts, and Redis plus an independent worker for jobs.

The SaaS branch will use S3-compatible object storage and one database per
organization. It adds authentication, authorization, encrypted organization
credentials, quotas, and billing without changing evidence-domain semantics.

Collection must respect authorization, applicable terms, robots policy, rate
limits, and legal constraints. CAPTCHA or an explicit access block pauses the
task and creates a human-action request.

## Branch policy

- `main`: frozen V1 local edition.
- `v2`: V2 local-first core and real end-to-end acquisition.
- `saas`: long-lived SaaS edition. It will adopt a stable V2 foundation before
  SaaS-only work begins.

## First milestone acceptance

- HTML, PDF, CSV/Excel, and RSS collector interfaces.
- Immutable raw artifacts stored by SHA-256.
- Reproducible evidence locators for every core observation.
- Deterministic and replayable normalization/calculation.
- Cross-source validation and a human review queue.
- Append-only correction history.
- Test coverage for the evidence chain and Docker-based local startup.
- At least three automotive panels running on real end-to-end data.

This milestone is complete on `v2`. The reference dashboard uses three NHTSA
public APIs. Every response is retained as an artifact, represented by a root
JSON Pointer, mapped deterministically, validated against a frozen schema, and
shown through the provenance UI.

## Runtime topology

```text
Browser :5173
  -> Nginx frontend
       -> FastAPI :8000
            -> PostgreSQL :5432
            -> Redis :6379 -> independent Worker
            -> content-addressed artifact volume
```

FastAPI serves V2 only. V1 runtime code remains available from the frozen
`main` branch; V1 database tables are preserved during Alembic comparison and
classified as legacy data.

## Dynamic dashboard contract

A saved `DashboardVersion` is append-only. Its child `PanelVersion` freezes:

- JSON Schema plus AutoPrism time, geography, aggregation, and visualization metadata;
- safe UI DSL, or custom React source and its SHA-256;
- extraction instructions, prompt version, model settings, and source-pool binding.

The current UI renders the safe `metric`, `table`, and `provenance` subset.
Custom React source can be stored but isolated compilation and runtime remain a
documented follow-up.

## Visual continuity

V2 keeps the V1 product identity: a dark intelligence cockpit, translucent
glass surfaces, purple/cyan status accents, dense operational telemetry and
terminal-like evidence inspection. This visual layer is independent from the
V2 data contracts. Dynamic dashboards, frozen Schema/UI DSL definitions and
the provenance workflow remain the authoritative behavior underneath it.

Engineering metadata is summarized in the cockpit and expanded only through
the evidence trace terminal, so the primary surface remains suitable for
research and decision work rather than looking like a database administration
screen.
