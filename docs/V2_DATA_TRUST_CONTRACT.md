# AutoPrism V2 Data Trust Contract

This contract defines when AutoPrism may display, calculate, validate or use a
value in an L2 insight. It is deliberately stricter than successful collection
or JSON Schema validation.

## State boundaries

These states are independent and must never be collapsed into one badge:

1. `schema_valid`: an extraction payload conforms to the frozen panel Schema.
2. `evidence_cited`: each extracted field cites an exact fragment in the input
   snapshot.
3. `calculation_replayable`: deterministic code can reproduce a calculation
   from immutable observation IDs and the frozen plan.
4. `cross_source_validated`: comparable observations from at least two
   independent source definitions satisfy explicit tolerances.
5. `human_approved`: an append-only review decision records a rationale and
   actor. Until authentication is connected, the actor is explicitly
   self-asserted and is not identity-verified.
6. `trusted_eligible`: a future append-only trust assessment confirms every
   policy prerequisite. V2 does not infer this state from Schema validity.
7. `legacy_unverified`: preserved V1 data excluded from V2 trusted
   calculations, maps and L2 generation unless it is re-collected through V2.

## L1: immutable source evidence

Every authoritative input must resolve to:

`SourceDefinition → SourceSnapshot → EvidenceArtifact → EvidenceFragment`

Required audit fields are the canonical source URL, retrieval timestamp,
optional source-provided publication timestamp, HTTP status, artifact byte
size/media type/SHA-256 and a reproducible locator. Supported locators are
one-based PDF pages, sheet/cell locations, JSON Pointers, CSS selectors,
XPath and text spans. Collection validates the locator before persistence and
stores a SHA-256 of extracted text.

`NULL` means “the source did not provide this field” only where the API labels
that meaning. It is never converted to zero, `NA`, a random value or a model
guess.

Artifacts, snapshots and fragments are append-only at both ORM and database
trigger layers. A changed source creates a new snapshot linked to its
predecessor. Artifact bytes and database metadata must be backed up together.

## INFO: structured observations

An INFO metric is an immutable `MetricObservation` bound to a frozen panel
version, Schema version and exact evidence fragment. It records raw and
normalized values, unit/currency, time period, geography, dimensions, extraction
model/prompt version and trust state.

Extraction may only return facts present in supplied fragments. It may not
browse, calculate, estimate or fill missing fields. Numeric authority is never
delegated to a language model.

Corrections create a new UNVERIFIED observation with `supersedes_id` plus an
`ObservationRevision`; the original stays unchanged. Database uniqueness
constraints prevent two replacements of the same observation. A migration
halts and reports existing forks rather than deleting or choosing historical
rows.

Known limitation: observations do not yet have a direct `extraction_run_id`
foreign key or a many-to-many evidence relation. Until that migration is
implemented, extraction lineage is reconstructed from panel, snapshot and
fragment records and this limitation remains visible.

## Deterministic calculations

The only calculation engine is versioned Decimal code. Inputs are database
observation IDs; callers cannot submit fact values. Runs freeze operation,
ordered inputs, parameters, output, engine version and replay hash.

- duplicate or differently scoped inputs are rejected;
- add/subtract/weighted-average require identical input/output units;
- percent change requires the explicit `percent` output unit;
- multiply/divide require an explicit output unit and unit plan;
- currency, period, geography, dimensions, panel and Schema scope must match;
- output remains UNVERIFIED and identifies itself as a deterministic
  calculation.

Unit conversion, currency conversion, rounding/error propagation and a
standalone replay-verification endpoint are not yet implemented and must not be
presented as complete.

## Cross-source validation

Tolerances are mandatory request fields. Validation rejects duplicate IDs and
non-comparable panel, Schema, metric, unit, currency, period, geography or
dimension scopes. A run can pass only when at least two independent
`SourceDefinition` identities are present. Repeated observations from one
source create `NEEDS_REVIEW`, never `PASSED`.

The run freezes source identities, independent-source count, tolerances,
minimum/maximum/spread, rule version and result. Conflict or insufficient
independence creates an immutable review case.

A passed validation does not mutate an observation to VERIFIED. A later
milestone must add append-only trust assessments before `trusted_eligible`
exists.

## Human review and revision history

Review cases and decisions are append-only. A case has one root decision; each
later decision must supersede the current head. Database uniqueness and API
conflict handling reject concurrent forks. Every decision requires an outcome,
non-empty rationale payload and actor.

Authentication is not yet part of V2. `decided_by` and `revised_by` are
self-asserted audit labels, clearly identified as such in the UI; they are not
cryptographic identity proof.

## L2 use policy

L2 may analyze only database content and must persist the complete set of input
observation/revision/calculation/validation IDs, input hash, model/prompt
versions and supersession relationship. No current V2 endpoint is allowed to
claim trusted L2 output until the trust-assessment and L2 lineage models exist.

All V1 intelligence, time-series, vehicle and strategic-insight tables remain
`legacy_unverified` as a namespace even where a legacy evidence link exists.
Their historical default scores are never accepted by V2 as verified facts.

## Acquisition compliance status

| Control | Current status |
| --- | --- |
| Disabled source, declared auth requirement and missing credential reference | Enforced by backend gate |
| Configured robots URL and disallow result | Enforced by backend gate |
| CAPTCHA/auth/robots restriction human-action queue | Enforced for detected gates |
| User authorization confirmation | UI gate only; immutable authorization attestation pending |
| Terms/legal review | Metadata/manual only; not an automated legal determination |
| Rate limiting and scheduled refresh policy | Deferred |
| Redirect-domain re-authorization | Deferred |
| Encrypted credential vault | Deferred; repository credentials are prohibited |

When any external permission, legal interpretation, credential or destructive
historical reconciliation is required, automation stops and requests human
action. It must never bypass access controls or erase history to proceed.
