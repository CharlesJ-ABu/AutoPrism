# AutoPrism V2 Data Trust Contract

This contract defines when AutoPrism may display, calculate, validate or use a
value in an L2 insight. It is deliberately stricter than successful collection
or JSON Schema validation. Current policy versions are:

- extraction contract: `evidence-extraction-v3`;
- validation rule: `numeric-v3-bounded-source-artifact-publisher`;
- trust policy: `trust-eligibility-v4-bounded-conversion-replay`;
- unit registry: `unit-registry-v1`;
- numeric engine: `decimal-v2-bounded`;
- conversion engine: `conversion-v1-bounded`.

Older policy labels remain immutable history but are not accepted as current
eligibility proof.

## Research orchestration is not evidence

`research-plan-v1` is an orchestration contract, not a trust policy. The model
may propose research questions, Google queries, exact registered-source keys,
analysis targets and interpretation questions using only the supplied database
inventory. It may not assert that a source was searched/read/collected, output
authoritative facts or measurements, create default/NA values, execute
arithmetic or decide trust.

Each plan freezes a canonical credential-free input manifest, system-prompt
hash, provider/model identity, structured output hash and exact action set.
Actions are inert until individually authorized. Their only executors are the
existing discovery provider and policy-checked collection queue. Resulting
candidates remain unregistered; resulting snapshots begin at L1 and still
traverse the ordinary INFO, validation and assessment contracts.

The Shell insight-map contracts frozen on 2026-08-10 are:

- observation geography: `geo-scope-v1`;
- L2 map output: `trusted-insight-map-v1`;
- L2 engine/prompt: `deterministic-stored-summary-v2-map` /
  `stored-input-contract-v2-map`.

## State boundaries

These states are independent and must never be collapsed into one badge:

1. `schema_valid`: an extraction payload conforms to the frozen panel Schema.
2. `evidence_cited`: each extracted field cites an exact fragment in the input
   snapshot.
3. `calculation_replayable`: deterministic code can reproduce a calculation
   from immutable observation IDs, bounded numeric records, current input
   assessments and the frozen plan. Replayability alone is still not the same
   as `trusted_eligible`.
4. `cross_source_validated`: comparable observations from at least two
   independent source definitions, artifacts and frozen publisher identities
   satisfy explicit tolerances.
5. `human_approved`: an append-only review decision records a rationale and
   actor. Until authentication is connected, the actor is explicitly
   self-asserted and is not identity-verified.
6. `trusted_eligible`: an append-only trust assessment confirms every current
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
predecessor. Publisher identity is normalized into immutable snapshot metadata
at collection time; validation never reinterprets an old snapshot from a later
mutable source-definition configuration. Artifact bytes and database metadata
must be backed up together.

## INFO: structured observations

An INFO metric is an immutable `MetricObservation` bound to a frozen panel
version, Schema version and exact evidence fragment. It records raw and
normalized values, unit/currency, time period, geography, dimensions, extraction
model/prompt version and trust state.

Extraction may only return facts present in supplied fragments. It may not
browse, calculate, estimate or fill missing fields. Numeric authority is never
delegated to a language model.

For `evidence-extraction-v3`, every run freezes a non-empty ordered input set.
Each `ExtractionRunInput` binds its ordinal, fragment ID, text SHA-256 and
manifest-entry hash; the run binds the manifest count/hash and complete input
payload hash. Trust replays the artifact bytes, parser locator, fragment text,
manifest entries, prompt/panel/model contract and deterministic mapping output.
A non-deterministic model response may be retained as an UNVERIFIED candidate,
but M6 will not promote it to trusted eligibility without a future attestation
mechanism.

Every observation has a frozen `ObservationEvidenceSet` and ordered
`ObservationEvidenceLink` rows. Links identify the metric or dimension claim,
role, exact run-output field path and supporting fragment; the same physical
fragment may legitimately support multiple claims. `ObservationExtractionLink`
binds a direct observation to one extraction run, record ordinal and field
path. Database constraints require one primary claim, contiguous cardinality
and complete claim coverage, and permit at most one stored origin across
extraction, revision or calculation. Current trust eligibility is stricter: it
requires exactly one replayable origin.

Corrections create a new UNVERIFIED observation with `supersedes_id` plus an
`ObservationRevision`; the original stays unchanged. Database uniqueness
constraints prevent two replacements of the same observation. A migration
halts and reports existing forks rather than deleting or choosing historical
rows.

Migration `0005_v2_observation_lineage` never guesses historical direct
lineage. On the backed-up populated database it audited six observations,
created three unique `backfill_exact` links and left three unresolved. The
unresolved rows preserve their compatibility evidence and remain visibly
unreplayable; no old observation, value or extraction run is rewritten.

Migration `0006_v2_trusted_insight_map` adds an optional immutable
`ObservationGeography` plus ordered `ObservationGeographyEvidence` claims.
Non-empty historical `geographic_scope` without that contract stops migration
for explicit review; empty legacy scopes remain empty. New geography must
replay from the exact direct extraction record, required Schema fields,
citations and frozen input manifest. A descriptive geography label, source URL
hostname or evidence locator alone is not a coordinate authority.

## Frozen numeric and uncertainty contract

Every new numeric observation has exactly one immutable numeric record with a
canonical Decimal value and one of `exact`, `bounded` or `unknown`. Exact means
zero error by contract; bounded requires a non-negative absolute error and its
claim evidence; unknown never becomes zero and cannot enter validation,
conversion, calculation or trust eligibility. Migration `0007` deliberately
does not infer these records for historical observations.

All arithmetic uses a local 50-digit Decimal context with ROUND_HALF_EVEN and
explicit positive output quantum. JSON source parsing, PostgreSQL JSON
serialization and hashes preserve Decimal values rather than routing them
through binary floats. Inputs and hashes use canonical decimal strings;
booleans, null, NaN, Infinity and malformed historic JSON fail closed.

## Deterministic calculations and conversions

The implemented calculation engine is versioned Decimal code. Inputs are database
observation IDs; callers cannot submit fact values. Runs freeze operation,
ordered inputs, parameters, output, engine version and replay hash.

- duplicate or differently scoped inputs are rejected;
- add/subtract/weighted-average require identical input/output units;
- percent change requires the explicit `percent` output unit;
- multiply/divide are rejected until a versioned dimensional-algebra contract exists;
- currency, period, geography, dimensions, panel and Schema scope must match;
- output remains UNVERIFIED and identifies itself as a deterministic
  calculation.

`decimal-v2-bounded` may become eligible only when normalized input rows freeze
each current eligible assessment and Trust independently replays the operation,
interval bounds, quantum, output Schema, evidence union and replay hash. Older
engines remain immutable but ineligible.

Unit conversion is restricted to codes in `unit-registry-v1` with identical
dimension and semantic kind. Currency conversion accepts no numeric rate from
the caller: it references an existing current eligible `currency_ratio`
observation with explicit base/quote and `instant`, `period_end` or
`period_average` basis. Time scope must match exactly. Direct and inverse pairs
are supported; live lookup, nearest-rate selection and triangular FX are not.
Every conversion freezes input assessment IDs, plan, input snapshot, result,
engine/registry versions and replay hash, and is dynamically invalidated when
an input assessment ceases to be current.

Executable time authority uses `time-scope-v1`. Its required Schema fields are
ISO-8601 strings with explicit UTC offsets; extraction freezes the resulting
instant or period on every observation and Trust rebuilds it from the cited
output. Retrieval time and “nearest available” time are never substituted.

## Cross-source validation

Tolerances are mandatory request fields. Validation rejects duplicate IDs and
non-comparable panel, Schema, metric, unit, currency, period, geography or
dimension scopes. Under `numeric-v3-bounded-source-artifact-publisher`, a run can pass
only when at least two independent `SourceDefinition` IDs, artifact SHA-256
identities and snapshot-frozen publisher identities are present. Repeated
sources, repeated artifacts, repeated publishers or missing publisher identity
create `NEEDS_REVIEW`, never `PASSED`.

The run freezes source/artifact/publisher identities, their independent counts, tolerances,
minimum/maximum/spread, rule version and result. Conflict or insufficient
independence creates an immutable review case.

A passed validation does not mutate an observation to VERIFIED. The
`trust-eligibility-v4-bounded-conversion-replay` assessment separately recomputes the
comparison key, expected result/state and current rule. It also requires every
validation peer to remain a current head and pass artifact bytes, fragment
hash, parser locator, snapshot state, frozen evidence-set and unambiguous-origin
replay. Superseding any peer immediately makes an old eligible assessment stale
for `trusted_only` reads and new L2 creation.

## Trust eligibility

`TrustAssessment` is immutable historical evidence, not a mutable status flag.
Current eligibility is recalculated dynamically from its observation and
origin. Direct observations require a current PASSED validation and every peer;
derived observations instead require a supported calculation/conversion run
whose frozen input assessments all remain current.

Direct extraction eligibility additionally requires exact deterministic
`evidence-extraction-v3` replay, panel/Schema/unit/claim agreement and a valid
frozen input manifest. Historical v2 extraction contracts, legacy rows,
unsupported validation rules, non-deterministic extraction, manual revision
attestation and calculation/conversion engines outside the current allowlists fail closed
with explicit reason codes. A human decision is never silently treated as a
substitute for these proofs.

## Human review and revision history

Review cases and decisions are append-only. A case has one root decision; each
later decision must supersede the current head. Database uniqueness and API
conflict handling reject concurrent forks. Every decision requires an outcome,
non-empty rationale payload and actor.

Authentication is not yet part of V2. `decided_by` and `revised_by` are
self-asserted audit labels, clearly identified as such in the UI; they are not
cryptographic identity proof.

Manual revisions require finite schema-valid numeric values, unchanged
unit/currency/time/geography/dimension scope and explicit evidence claims when
the value changes. The revision chain remains fully visible, but M6 intentionally
does not mark a manual semantic correction trusted because it has no replayable
human-attestation contract yet.

## L2 use policy

L2 may analyze only database content. The current deterministic stored-input
summary accepts only current observation heads whose latest assessment is
ELIGIBLE. It persists normalized observation and assessment foreign keys,
ordered inputs, an input hash, engine/contract versions and immutable output.
It does not browse, predict, fill missing facts or execute model mathematics.

Historical L2 rows remain immutable if an input is later revised; attempting to
create a new current L2 summary with the superseded input is rejected.

Map features are a deterministic subset of L2 output. The
`trusted-insight-map-v1` read model dynamically requires every stored input
assessment to remain current, independently replays `geo-scope-v1`, and
rebuilds the exact frozen feature list. A mismatch or stale peer returns no
feature; it never edits the historical L2 row. Empty current results are a
normal trust outcome and are rendered without filler locations.

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
| Fixed-interval scheduled refresh policy | Implemented with explicit authorization, 15-minute floor, current-bucket-only dispatch and immutable outcomes |
| Shared per-domain rate budgets and calendar/cron windows | Deferred |
| Redirect-domain re-authorization | Deferred |
| Encrypted credential vault | Deferred; repository credentials are prohibited |

When any external permission, legal interpretation, credential or destructive
historical reconciliation is required, automation stops and requests human
action. It must never bypass access controls or erase history to proceed.
