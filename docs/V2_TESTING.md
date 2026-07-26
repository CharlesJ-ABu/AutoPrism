# AutoPrism V2 Test Record

Last full validation: 2026-07-27 (Asia/Shanghai).

## Automated backend

`python -m unittest discover -s tests -v` passed 24/24 tests against the
disposable PostgreSQL database. The fast no-database run also passed all
19 applicable tests and skipped the 5 database tests explicitly.

Coverage includes:

- HTML CSS selectors, RSS XPath, PDF pages, CSV cells, XLSX cells, JSON Pointers;
- streaming size limits and acquisition policy decisions;
- artifact SHA-256 storage and verification;
- immutable ORM and PostgreSQL trigger guards;
- audited observation revision creation and duplicate-revision rejection;
- source and dashboard REST API contracts;
- source pool, snapshot, artifact, and fragment persistence;
- missing credential blocking and human-action creation;
- frozen Schema extraction with per-field evidence IDs;
- ordered dashboard history, complete version detail and append-only version creation;
- safe UI DSL nodes bound to fields and table columns in the frozen Schema;
- provider-neutral adapters and deterministic JSON mapping;
- deterministic decimal calculation and replay hash;
- numeric cross-source tolerance and review routing;
- independent-source enforcement, complete trust-history APIs, single-head
  review decisions and duplicate correction rejection;
- artifact/fragment eligibility replay, normalized L2 inputs, idempotent
  stored-input summaries and stale-assessment rejection after revision.

## Database migrations

- `alembic check`: no schema drift.
- current revision: `0004_v2_trust_assessments_l2`.
- preserved historical database upgraded its migration graph without deleting,
  stamping or rewriting real data.
- empty disposable database upgraded through the complete V2 chain and the V1
  compatibility revisions.
- disposable M5 downgrade
  `0004_v2_trust_assessments_l2 -> 0003_v2_lineage_uniqueness` succeeded.
- re-upgrade to `0004_v2_trust_assessments_l2` succeeded.
- second `alembic check` reported no new operations.

## Real data end-to-end

The reference seed captured three NHTSA official API responses:

| Panel | Result | Artifact SHA-256 |
|---|---:|---|
| US vehicle makes | 12,306 records | `fd57cf33710b3e1db51f2840bfcd31d1699d2e561e89b34cfbf9372cdf1ae0d0` |
| Tesla MY2024 models | 6 records | `61b8535b63d89d34b5018f81df62ca4d6fb9d625ddd114d97ab4771fdaeb4f96` |
| Tesla Model 3 MY2024 rating variants | 2 records | `1c81cfbffbb3085688892860846bb9fe8092f509ef3391ef25ffec02e3bdd245` |

All three collection jobs and extraction runs succeeded with zero Schema
issues. Values use deterministic mappings rather than LLM arithmetic.

## Frontend and Compose

- `npm run build`: passed TypeScript and Vite production build.
- `npm audit`: zero known vulnerabilities after upgrading to Vite 6.4.3.
- containerized `pip check`: no broken Python requirements. The developer
  machine's unrelated global Python environment is not part of this result.
- five Compose services started; frontend, web, PostgreSQL, and Redis healthy.
- frontend Nginx successfully proxied `/api/v2/dashboards`.
- `/ready` returned PostgreSQL and Redis `ok`.
- browser 1440×800 verification rendered the V2 cockpit, verified situation
  layer, all three panels and their evidence hashes.
- provenance drawer showed every returned evidence fragment, JSON Pointer,
  timestamps, file/text hashes, Schema, UI DSL, source and artifact download.
- 390×844 responsive check: three panels rendered and body width equaled viewport width (no horizontal overflow).
- V1-compatible role/view switcher and truthful no-geocode map state passed.
- current V2 JavaScript bundle emitted no browser warnings or errors.
- operations smoke loaded the real 3-source/6-job state, kept all collection
  actions disabled until compliance acknowledgement, and exposed the human
  action and Schema-bound extraction paths without mutating production data.
- trust-workspace smoke loaded 2 real UNVERIFIED observations for the selected
  panel, separated Schema validity from trust, displayed source hosts/hashes
  and explicit validation tolerances, and showed honest zero states for
  calculations, validations and reviews. Desktop and 390×844 mobile layouts
  remained usable without writing real history.
- eligibility/L2 smoke displayed both real observations as NOT ASSESSED,
  zero ELIGIBLE, a disabled L2 action and the explicit “L2 当前不可用” state.
  The current JavaScript bundle emitted no warnings/errors.

## Known non-blocking warnings

BeautifulSoup/lxml currently emits an upstream `strip_cdata` deprecation
warning in the HTML parser test. It does not affect output.
