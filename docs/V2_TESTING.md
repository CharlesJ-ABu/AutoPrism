# AutoPrism V2 Test Record

Last full validation: 2026-08-10 (Asia/Shanghai).

## M8 safe chart/timeline milestone result

The full disposable-PostgreSQL backend suite remains 55/55 after extending the
dashboard save API and collection/extraction integration path with Schema-bound
chart and timeline nodes. Contract coverage rejects unknown node properties,
non-array data sources, invalid axes, free-form metric units, non-date timeline
fields and unsupported multi-series declarations.

Frontend typecheck and production build passed with 2,889 modules, and the
production dependency audit reported zero vulnerabilities. The current
Compose bundle was exercised first against the unchanged real NHTSA database,
then temporarily against the isolated integration database to verify a non-empty
area chart (2 stored numeric points) and timeline (2 stored events). At 390×844,
`innerWidth=390`, `scrollWidth=384`, and both visual components were 330 px wide;
there was no Vite error overlay, incomplete image or rendered error state. The
Compose web service was then restored to `autoprism`; the real database still
contained exactly one dashboard and the original API returned only the
published automotive dashboard. No synthetic test record entered the real
database.

## M7 bounded numeric milestone result

The final disposable PostgreSQL suite passed 55/55 tests with database tests
enabled. New coverage includes fixed-context Decimal arithmetic, semantic unit
compatibility, direct/inverse FX interval propagation, unknown-uncertainty
rejection, frozen calculation/conversion inputs, dynamic derived-assessment
replay, exact JSON Decimal persistence, cited `time-scope-v1`, strict output
Schema/quantum contracts and conversion API validation. The full integration
path proves a current eligible USD amount plus current eligible USD/CNY rate
produces and independently replays the frozen CNY observation.

Migration `0007_v2_numeric_conversion` passed zero-to-head, downgrade to
`0006`, re-upgrade to `0007`, and `alembic check` on a new empty database. A
restored copy of the real six-observation database upgraded with the original
count/digest unchanged and zero inferred numeric, calculation-input or
conversion rows. Frontend typecheck/build passed (2,887 modules) and the
production dependency audit reported zero vulnerabilities.

Current Compose/browser smoke passed after the real database upgrade:

- `/health`, `/ready`, unit-registry and conversion-history endpoints returned 200;
- all five services were healthy/running and recent logs contained no failures;
- the evidence drawer loaded `unit-registry-v1` and the M7 conversion tab from
  real APIs; with zero eligible legacy inputs it disabled execution and showed
  the contractual empty state;
- historical rows displayed `LEGACY / 未冻结`, not zero uncertainty;
- 1440×800 desktop and 390×844 mobile baselines were captured as
  `v2-m7-conversion-1440x800.png` and `v2-m7-conversion-390x844.png`;
- mobile `scrollWidth=384` at `innerWidth=390`, with the drawer fully inside the
  viewport; browser console warning/error count was zero.

## Trusted-map milestone result

The final disposable PostgreSQL suite passed 44/44 tests with database tests
enabled. It adds coverage for `geo-scope-v1`, immutable claim-level geography,
deterministic geography replay, current-only L2 map output and immediate map
removal after a newer ineligible assessment. The earlier 39/39 M6 result below
remains its historical release record.

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

## M9 compliant discovery gate — 2026-08-10

- Disposable databases upgraded from zero through `0008_v2_source_discovery`
  and `0009_v2_discovery_cardinality`; `alembic check` passed.
- A second empty database completed zero-to-head, downgrade to `0007` and
  re-upgrade through `0009`. Downgrade on populated M9 history stopped with the
  documented refusal instead of deleting discovery history.
- The complete backend suite passed 59/59, including credential exclusion,
  URL normalization, sanitized provider failures and database UPDATE/TRUNCATE
  rejection for discovery history.
- A readable pre-M9 backup was restored to a separate database before the real
  upgrade. Both the clone and real database retained 6 observations with digest
  `570aa8534787f6431a0bdef4fd8d9588` and 1 dashboard; discovery tables began
  empty and no historical facts were backfilled.
- Before the follow-up `0008` → `0009` upgrade, a second readable backup was
  created. The observation-ID digest remained
  `d89b6eed0d4287ec35520cbd16386ce5`, with 6 observations, 1 dashboard and zero
  discovery rows before and after; all Compose services returned healthy.
- Frontend typecheck and production build passed (2,889 modules; main JS
  246.07 kB, gzip 73.99 kB). Production dependency audit reported zero known
  vulnerabilities across 210 packages.
- Rebuilt Compose desktop and 390×844 browser smoke confirmed the live
  discovery workspace, explicit authorization/ephemeral-credential copy,
  disabled incomplete form, immutable empty state and no horizontal overflow.

## M10 refresh scheduler gate — 2026-08-10

- Fresh database `autoprism_v2_m10_release_20260810` upgraded from zero to
  `0011_v2_schedule_source_guard`; `alembic check` reported no drift.
- An empty database completed zero-to-0010, upgrade to 0011, downgrade to 0010
  and re-upgrade to 0011. A populated M10 database refused downgrade rather
  than erase schedule/dispatch history.
- The complete disposable-PostgreSQL suite passed 62/62 on both the existing
  gate and the newly migrated release database, including schedule
  authorization/version chains, current-bucket-only dispatch, idempotency,
  same-source database references, append-only database guards and
  duplicate-delivery-safe worker claims.
- Readable `/tmp/autoprism_pre_m10_20260810.dump` and
  `/tmp/autoprism_pre_m10_0011_20260810.dump` backups were verified before the
  real upgrades. The real database advanced to
  `0011_v2_schedule_source_guard`; observation-ID digest
  `d89b6eed0d4287ec35520cbd16386ce5`, 6 observations and 1 dashboard were
  unchanged, and the schedule/dispatch tables remained empty.
- Frontend typecheck/build passed (2,889 modules; main JS 250.94 kB, gzip
  75.11 kB); production dependency audit reported zero known vulnerabilities.
- Six-service Compose started the independent Scheduler without errors. Current
  desktop and 390×844 browser smoke verified the schedule workspace, disabled
  pre-authorization submit, honest empty history, no horizontal overflow and no
  console warning/error. A follow-up overlay regression verified that the
  composer and operations drawer retract the sidebar, cover the full 1280px
  viewport, lock background scroll, fit within 390×844 without horizontal
  overflow, and restore the navigation and scrolling after close.

## M11 LLM research orchestration gate — 2026-08-10

- Fresh database `autoprism_v2_m11_gate_20260810` upgraded from zero through
  `0012_v2_llm_research_runs`; `alembic check` reported no drift. A second empty
  database completed zero-to-head, downgrade to 0011, re-upgrade and drift check.
- The complete disposable-PostgreSQL suite passed 67/67. New coverage includes
  the plan system boundary, strict structured action counts, canonical prompt/
  input hashes, exact source allowlisting, append-only transitions, immutable
  database guards, deferred cardinality and fail-closed API input handling.
- Readable backup `/private/tmp/autoprism_pre_m11_20260810.dump` (963 KiB,
  SHA-256 `edc7f434d8cc62900f142d0c9875cd5ea81360c85a54529e88ad333900099c11`)
  was listed before the real additive upgrade. The real database advanced to
  0012 with 6 observations, digest `d89b6eed0d4287ec35520cbd16386ce5`,
  1 dashboard and zero research rows.
- Frontend typecheck/build passed (2,890 modules; main JS 263.01 kB, gzip
  78.12 kB); the production audit reported zero vulnerabilities.
- Real-empty and isolated-nonempty browser gates passed at 1440×800 and
  390×844. The form, HASH VERIFIED state, questions/targets/limitations,
  terminal/proposed actions and per-action authorization were exercised. The
  sidebar retracted, scroll lock restored, mobile scroll width equaled 390 px
  and no console warning/error was recorded.
- Visual records: `v2-m11-research-1440x800.png` and
  `v2-m11-research-390x844.png`.

## Database migrations

Current revision: `0012_v2_llm_research_runs`.

M11 adds only immutable research objectives, frozen LLM planning inputs and
outputs, allowlisted proposals and append-only execution events. It does not
execute a proposal, create a source, collect content or backfill history during
migration. Populated downgrade fails closed.

M10 adds only append-only schedule versions, immutable dispatch outcomes and
same-source reference constraints. It does not create a schedule for historical
sources or trigger a collection during migration. Populated 0010 downgrade
fails closed; the constraint-only 0011 migration supports empty
downgrade/re-upgrade.

The M9 migrations add only immutable discovery metadata, normalized
unregistered candidates and a deferred frozen-cardinality check. They do not
create a source, start a collection job or persist an API key/raw CX. Populated
M9 downgrade fails closed; empty disposable downgrade/re-upgrade is supported.

The M7 migration adds only new immutable numeric/uncertainty, normalized
calculation-input and conversion histories plus the Trust foreign key. It
does not backfill an uncertainty value from a historical normalized JSON
number. Empty disposable downgrade/re-upgrade is supported; any populated M7
history makes downgrade fail closed.

The 2026-08-10 `0006` gate:

- upgraded a new database from zero and passed `alembic check`;
- passed empty-database downgrade to `0005` and re-upgrade to `0006`;
- backed up the real six-observation database, restored it into a new database,
  and upgraded only that copy before starting the real Compose stack;
- preserved all six observation rows and the pre/post normalized-value digest
  `efeabae3f8044784c76bdca2e6fb73e4`;
- created no geography rows for legacy empty scopes and inferred no coordinates.

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

## Current visual and browser gate

Passed on 2026-08-10 against the current production Compose bundle:

- same-size 1440×800 V1 reference and V2 screenshots;
- 390×844 V2 screenshot and full-page responsive record;
- `scrollWidth=384`, `innerWidth=390`, no horizontal overflow;
- 3D globe and 2D tactical switching plus industrial/cyber/ghost controls;
- evidence terminal and compliant-acquisition drawer smoke;
- honest zero-feature map for the real reference database;
- no JavaScript console warning or error.

Artifacts are in `docs/visual-baselines/2026-08-10/`. The non-empty trusted-map
path is proven by the PostgreSQL service/API integration test, not by inserting
synthetic features into the real reference database.

## Known non-blocking warnings

BeautifulSoup/lxml currently emits an upstream `strip_cdata` deprecation
warning in the HTML parser test. It does not affect output.
