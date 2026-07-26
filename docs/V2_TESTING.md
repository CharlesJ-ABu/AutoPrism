# AutoPrism V2 Test Record

Last full validation: 2026-07-27 (Asia/Shanghai).

## Automated backend

`python -m unittest discover -s tests -v` passed 23/23 tests against the
disposable PostgreSQL database. The fast no-database run also passed all
18 applicable tests and skipped the 5 database tests explicitly.

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
- provider-neutral adapters and deterministic JSON mapping;
- deterministic decimal calculation and replay hash;
- numeric cross-source tolerance and review routing.

## Database migrations

- `alembic check`: no schema drift.
- current revision: `0002_backfill_legacy_evidence`.
- preserved historical database upgraded its migration graph without deleting,
  stamping or rewriting real data.
- empty disposable database upgraded through the complete V2 chain and the V1
  compatibility revisions.
- disposable database downgrade
  `0002_backfill_legacy_evidence -> 8a9c3d4e5f60` succeeded.
- re-upgrade to `0002_backfill_legacy_evidence` succeeded.
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

## Known non-blocking warnings

BeautifulSoup/lxml currently emits an upstream `strip_cdata` deprecation
warning in the HTML parser test. It does not affect output.
