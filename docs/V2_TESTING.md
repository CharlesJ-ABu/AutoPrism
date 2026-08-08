# AutoPrism V2 Test Record

Last full validation: 2026-08-09 (Asia/Shanghai).

## Automated backend

The final M6 gate ran from a zero-migration disposable PostgreSQL database and
passed 39/39 backend tests. The final count supersedes the earlier 35/35 and
37/37 intermediate results after boolean-JSON-Schema, NaN/Infinity,
deterministic source-path and malformed historical model-settings fail-closed
regressions were added.

Coverage includes:

- HTML CSS selectors, RSS XPath, PDF pages, CSV/XLSX cells and JSON Pointers;
- streaming size limits and acquisition policy decisions;
- content-addressed artifact bytes, fragment hashes and locator replay;
- immutable ORM guards and PostgreSQL UPDATE/DELETE/TRUNCATE rejection;
- `evidence-extraction-v3` ordered input sets, header/entry hashes and exact
  input-hash replay;
- normalized multi-claim observation evidence sets and direct extraction-run
  origin links;
- deterministic mapping replay, rejection of constants, non-finite values and
  non-deterministic extraction eligibility;
- strict revision numeric/Schema/scope/evidence contracts and single-head
  supersession;
- exact calculation parameter shapes and malformed historical JSON
  fail-closed behavior;
- `numeric-v2-source-artifact-publisher` comparison scope, independent source,
  artifact and snapshot-frozen publisher identities;
- validation result/rule replay and current-head/evidence/origin checks for
  every peer;
- `trust-eligibility-v3-validation-replay`, dynamic current eligibility,
  `trusted_only` reads and stale-assessment rejection;
- eligible stored-input L2 behavior and immutable historical inputs.

The fast non-database command remains useful during development; database tests
are explicitly gated by `AUTOPRISM_RUN_DB_TESTS=1`. The 39/39 release evidence
comes from the full disposable-PostgreSQL run, not the skipped fast run.

## Database migrations

Current revision: `0005_v2_observation_lineage`.

Fresh-database gate:

- created a new disposable PostgreSQL database from zero migrations;
- upgraded the complete V1-compatible and V2 migration graph to `head`;
- ran `alembic check` with no drift;
- ran the final backend suite: 39/39 passed.

Populated-database gate:

- completed a real PostgreSQL backup before migration at
  `/private/tmp/autoprism_v2_pre_0005_20260809.dump` (841 KiB, SHA-256
  `158de9f3543bbb82bdb1dfb23e26a666c8a67d8ca0050d598ea1830eb1e67cdd`);
- archived the unchanged content-addressed artifact volume after the migration
  at `/private/tmp/autoprism_v2_artifacts_20260809.tar.gz` (126 KiB, SHA-256
  `adf89817cc8f347b88cc3639973be9a383b8982296380664e5eae5adfe90e469`),
  and listed all three expected artifact hashes from the archive;
- upgraded the preserved populated database non-destructively to `0005`;
- retained all six historical target observations;
- created three `backfill_exact` observation-to-run links where one unique
  panel/snapshot/model/prompt/time/value/citation match existed;
- left three observations unresolved rather than choosing a likely run;
- recorded `method=exact_output_match_only` in the immutable lineage backfill
  audit;
- completed the populated migration/drift gate without deleting or rewriting
  real history.

`0005` intentionally refuses a downgrade when the new immutable lineage or
manifest tables contain data. Downgrade/re-upgrade exercises belong only on an
empty disposable database; a rejection on a populated database is the expected
fail-closed result.

## Real data end-to-end

The existing reference seed captured three NHTSA official API responses:

| Panel | Result | Artifact SHA-256 |
|---|---:|---|
| US vehicle makes | 12,306 records | `fd57cf33710b3e1db51f2840bfcd31d1699d2e561e89b34cfbf9372cdf1ae0d0` |
| Tesla MY2024 models | 6 records | `61b8535b63d89d34b5018f81df62ca4d6fb9d625ddd114d97ab4771fdaeb4f96` |
| Tesla Model 3 MY2024 rating variants | 2 records | `1c81cfbffbb3085688892860846bb9fe8092f509ef3391ef25ffec02e3bdd245` |

These are historical real-source artifacts and Schema-valid deterministic
outputs, not a claim that every observation is currently trust eligible. The
M6 populated migration audit is the authoritative record for the six legacy
observation rows: three exact links and three unresolved.

## Frontend and dependency gates

The 2026-08-09 M6 code gates passed:

- `npm run typecheck`;
- `npm run build` (TypeScript plus Vite production build);
- `npm audit` with zero reported vulnerabilities.

Previous Compose, 1440×800 desktop, 390×844 responsive, evidence drawer and
clean-console results dated 2026-07-27 remain historical M1–M5 evidence. They
are not relabeled as M6 validation.

## M6 visual and browser gate

**Not run.** The current execution environment has no available browser
runtime. Therefore the following current-worktree evidence is still required:

- same-size V1/V2 desktop screenshots;
- 390×844 responsive screenshots and horizontal-overflow inspection;
- current-bundle browser console inspection;
- loading, empty, error and dangerous-action interaction smoke;
- evidence drawer, dynamic panel, revision, validation and trust-state smoke.

An older screenshot or clean console record must not be substituted for this
gate. M6 can be described as backend/data/frontend-build complete, but its
visual release check remains pending.

## Known non-blocking warnings

BeautifulSoup/lxml currently emits an upstream `strip_cdata` deprecation
warning in the HTML parser test. It does not affect output.
