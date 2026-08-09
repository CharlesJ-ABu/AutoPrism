# AutoPrism V2 Security Notes

## Local V2 boundary

V2 is intentionally an unauthenticated local/internal edition. Do not expose
port 8000 directly to the public Internet. Public authentication, RBAC,
organization isolation and encrypted credentials belong to the `saas` branch.

The production frontend proxies `/api` to FastAPI. CORS is limited to the
documented localhost frontend origins.

## Credentials

- `backend/.env` is ignored by Git.
- `.env.example` contains placeholders only.
- API keys supplied through the dashboard composer are sent only to the local
  backend for that proposal request and are not persisted in dashboard models.
- Google discovery API keys and raw search-engine IDs are request-only. The key
  is excluded entirely; discovery history stores only a one-way configuration
  hash, query and normalized candidates. Queries are immutable audit data and
  must not contain secrets.
- Never put secrets in source definitions, parser configuration, prompts,
  model settings, logs, screenshots or review cases.
- V2 credential references are identifiers only; the encrypted credential
  vault is a SaaS deliverable.

If a real key is ever printed in a terminal, application log, test artifact or
assistant transcript, rotate it even when Git history is clean.

## Acquisition controls

Collection applies registered-source policy before fetch. Authenticated
sources require an explicit credential reference. Robots denial, credentials,
CAPTCHA/anti-bot blocks, terms conflicts, rate limits or legal uncertainty
must stop the job and create a human-action request. The system must not work
around access controls.

Fetches are streamed with time and byte limits. Redirects are recorded through
the final canonical URL. Raw content is never considered executable.

## Artifact integrity

Artifacts are addressed and verified by SHA-256. Database evidence stores the
source URL, retrieval time, response metadata, parser type and reproducible
locator. Artifact files and PostgreSQL must be backed up together.

## Custom code

The database can freeze custom React source and its hash, but V2 does not yet
execute custom source. Do not enable execution until the isolated runtime,
CSP, dependency allowlist, network policy, resource quotas and credential
separation in `V2_TODO.md` are complete.

## Audit performed

On 2026-07-25:

- current tracked/untracked source (excluding the ignored local `.env`) matched
  no common OpenAI/Google/AWS key patterns;
- all Git history matched no such key patterns;
- `backend/.env` was confirmed ignored;
- `npm audit` reported zero vulnerabilities after upgrading Vite;
- `pip check` reported no broken requirements.
