# Deployment and release preparation

This guide prepares the existing AstroAI API image and static frontend for a controlled deployment. It does not authorize a public launch. No live service was changed as part of this work.

## Runtime requirements

- Backend: Python 3.12 slim container, FastAPI/Uvicorn, SQLAlchemy, Alembic, and PostgreSQL via psycopg.
- Frontend: static Vite build in `frontend/dist`; deploy to the selected HTTPS static host/CDN.
- Database: PostgreSQL. SQLite is supported for local tests only.
- The AI chat path is deterministic and has no model/provider/API-key requirement. Chat has no daily cap; its database-shared default burst limit is 30 requests per user per minute. Redis is not required by current application code.
- Public astrology calculation routes remain disabled. Swiss Ephemeris data files and native libraries are not copied into the image; a license review is unresolved.

## Environment configuration

Set these through the hosting platform's secret/configuration manager. Do not put production values in `.env`, image build arguments, CI logs, or Git.

| Variable | Production requirement |
| --- | --- |
| `APP_ENV` | `production` |
| `SECRET_KEY` | Unique random secret, at least 32 characters; rotate through a planned key migration |
| `DATABASE_URL` | `postgresql+psycopg://...` with a dedicated least-privilege application user |
| `CORS_ORIGINS` | Comma-separated exact HTTPS frontend origins; no wildcard |
| `TRUSTED_PROXY_IPS` | Exact direct peer IPs for controlled reverse proxies; empty by default |
| `AI_CHAT_RATE_LIMIT_PER_MINUTE` | Chat burst limit per authenticated user; default 30 |
| `PASSWORD_RESET_RATE_LIMIT_PER_HOUR` | Password reset requests per account; default 5 |
| `PASSWORD_RESET_IP_RATE_LIMIT_PER_HOUR` | Password reset requests per client IP; default 20 |
| `PASSWORD_RESET_SMTP_HOST` | SMTP server hostname; required to send recovery messages |
| `PASSWORD_RESET_SMTP_PORT` | SMTP submission port; default 587 |
| `PASSWORD_RESET_SMTP_USERNAME` / `PASSWORD_RESET_SMTP_PASSWORD` | Optional SMTP authentication; load password from secret manager |
| `PASSWORD_RESET_SMTP_SENDER` | Verified sender address, for example `AstroAI <no-reply@example.com>` |
| `PASSWORD_RESET_SMTP_STARTTLS` | Use STARTTLS; default `true` |
| `PASSWORD_RESET_FRONTEND_URL` | Public frontend origin; use the HTTPS production origin |
| `ASTROLOGY_CALCULATIONS_ENABLED` | `false` until the calculation/licensing gate is completed |
| `SWISSEPH_LICENSE_CONFIRMED` | `false` until reviewed and approved outside the application |

Production settings reject the development JWT secret, short secrets, SQLite, wildcard CORS and non-HTTPS origins. TLS termination must be configured at the load balancer/reverse proxy. Do not trust forwarded headers until the proxy network and forwarded-header policy are explicitly configured. Password reset uses a forwarded client IP only if the direct peer is listed in `TRUSTED_PROXY_IPS`; otherwise it ignores the header.

Password reset uses 32-byte cryptographic tokens, stores only SHA-256 token hashes, expires links after 30 minutes, and allows one successful use. Reset links put the token in a URL fragment; browser fragments are not sent in HTTP requests or ordinary access logs. Resetting increments the user's auth version so previously issued access JWTs are rejected. Configure SMTP before relying on the recovery flow. If SMTP is missing, the endpoint returns 503 for all addresses without looking up whether an account exists.

For local testing only, set `APP_ENV=development`, `PASSWORD_RESET_DEV_TOKEN_FILE=/absolute/private/path/astroai-reset-link.txt`, and `PASSWORD_RESET_FRONTEND_URL=http://localhost:5173`. The server writes only the latest link to a file created with mode 0600; the API response and logs do not contain the token. Keep this file outside Git, delete it after testing, and never set `PASSWORD_RESET_DEV_TOKEN_FILE` in staging or production. The Playwright journey uses an isolated temporary SQLite database and temporary local file in this mode. This development path verifies token handling/UI but is not email-delivery verification.

## Vercel deployment (FastAPI backend)

The production backend can run as a Vercel Python Function. In the Vercel backend project, keep **Root Directory** set to `backend`. `backend/pyproject.toml` declares `app.main:app` as the FastAPI entrypoint, and `backend/vercel.json` explicitly includes `ephe/*.se1` in the function bundle. The `swisseph-ffi` package is a runtime dependency and provides the platform-specific shared library.

Add the official Swiss Ephemeris data files under `backend/ephe/` before deploying. See [backend/ephe/README.md](../backend/ephe/README.md) for the official sources and the modern-date files. Configure `SWISSEPH_EPHE_PATH=ephe`; relative paths resolve against the backend project root. The currently documented `sepl_18.se1`/`semo_18.se1` pair covers 1800–2399 only. Add other official date-range pairs for profiles outside that range.

The database setting uses `DATABASE_URL` when provided and falls back to the Neon integration variable `POSTGRES_PRISMA_URL`. Prefer adding an explicit `DATABASE_URL` in Vercel when you have a reason to select a particular Neon connection string; never expose its value in logs or client-side `VITE_*` variables.

After the AGPL license file, source-code notice, matching public source, and ephemeris files are committed and live, set these Vercel variables for a Preview deployment first:

```dotenv
APP_ENV=production
ASTROLOGY_CALCULATIONS_ENABLED=true
SWISSEPH_LICENSE_CONFIRMED=true
ASTROLOGY_LOCAL_AGPL_DEVELOPMENT_ENABLED=false
SWISSEPH_EPHE_PATH=ephe
```

Also configure the existing production `SECRET_KEY`, Neon connection variable (`DATABASE_URL` or `POSTGRES_PRISMA_URL`), exact HTTPS `CORS_ORIGINS`, and `PASSWORD_RESET_FRONTEND_URL` with your HTTPS frontend origin (the production settings validator rejects its localhost default). Do not enable the two calculation flags before the AGPL source offer and the corresponding source are actually available to remote users. The local-only development switch must remain false on Vercel. Redeploy after changing variables. Verify `/health`, `/ready`, Vedic and Western calculations, and reference-chart parity in Preview before promoting to Production.

## Build and run the API image

From the repository root:

```sh
docker build -t astroai-api:release-candidate ./backend
docker run --rm --env-file /secure/path/astroai-api.env -p 8000:8000 astroai-api:release-candidate
```

The container runs as an unprivileged `astroai` user. It includes the tracked `ephe/` data directory and installs the pinned `swisseph-ffi` runtime dependency; the wrapper supplies the platform-specific shared library. Its `.dockerignore` excludes environment files, databases, and test files. The image contains the Alembic configuration and migration scripts.

Build the static client separately:

```sh
cd frontend
npm ci
npm test
npm run build
```

Deploy only `frontend/dist` to the configured HTTPS host. Set its public `VITE_API_BASE_URL` at build time to the API's HTTPS `/api/v1` URL. Never put backend-only secrets in `VITE_*` variables.

## Database migration procedure

Run migrations as a one-off release job, not from every API worker's startup command:

```sh
docker run --rm --env-file /secure/path/astroai-api.env astroai-api:release-candidate alembic upgrade head
```

Before a production migration, take a database backup, review the Alembic revision and test it against a restored staging copy. Confirm the expected `alembic_version` after migration, then roll out API instances. Avoid automatic downgrades on release rollback; restore or apply a reviewed forward migration based on the change and data state. Never run destructive migration experiments against production.

### Enable password recovery

For local-only testing, add the following to the developer's untracked root `.env` (or export these variables for the API process):

```dotenv
APP_ENV=development
PASSWORD_RESET_DEV_TOKEN_FILE=/tmp/astroai-password-reset-link.txt
PASSWORD_RESET_FRONTEND_URL=http://localhost:5173
```

Start the API and frontend, submit the forgot-password form with a test account, then open the URL in `/tmp/astroai-password-reset-link.txt`. The token is in a URL fragment, which browsers do not send in the HTTP GET. The reset page reads it, removes it from the address bar, and sends it only in the reset POST body. The API response and application logs do not contain it. Delete the file after the test. This method is strictly for local development and does not test SMTP.

For staging/production, set `APP_ENV`, `PASSWORD_RESET_SMTP_HOST`, `PASSWORD_RESET_SMTP_PORT` (normally 587), `PASSWORD_RESET_SMTP_USERNAME`, `PASSWORD_RESET_SMTP_PASSWORD` (from a secret manager), `PASSWORD_RESET_SMTP_SENDER`, `PASSWORD_RESET_SMTP_STARTTLS=true`, and `PASSWORD_RESET_FRONTEND_URL=https://<public-frontend-origin>` in the service configuration. Configure sender-domain authentication and delivery monitoring at the selected mail host. Apply the Alembic migration, request recovery for a controlled mailbox, receive the message, complete a reset, verify the prior access token is rejected, and check that logs contain no token, password, reset URL, or email address. Until this live-mail test succeeds, claim only that the reset API and local test path work; email recovery has not been verified end-to-end.

## Health checks, logs, and monitoring

- `/health` is a process liveness check and does not query the database.
- `/ready` runs `SELECT 1`; it returns 503 without exposing connection details if PostgreSQL is unavailable. The container health check targets this endpoint.
- Uvicorn writes to stdout/stderr. The platform should collect and retain logs with access controls. Application errors avoid returning exception internals. Do not add request bodies, passwords, birth data, tokens, or chat contents to logs.
- Monitor process restarts, readiness, HTTP 5xx/401/429 rates, latency, PostgreSQL availability/connection saturation, disk growth, and backup completion. Alert thresholds and a staffed response process still need to be selected by the operator.

## Backup and recovery

Use managed PostgreSQL point-in-time recovery where available and take periodic encrypted logical backups. Example manual commands (use the secret manager for credentials):

```sh
pg_dump --format=custom --no-owner "$DATABASE_URL" > astroai-$(date -u +%Y%m%dT%H%M%SZ).dump
pg_restore --list astroai-backup.dump
```

Store backups outside the application host with encryption, retention, and access controls. Regularly restore a backup into an isolated non-production database and verify Alembic state plus representative owner-scoped records. Define an RPO/RTO, retention duration, restore operator, and incident procedure before launch; those operational values are deployment-owner decisions.

## CI and release checks

`.github/workflows/ci.yml` runs repository Ruff, backend pytest, frontend tests and production build, Alembic SQLite upgrade/downgrade/upgrade, and Playwright Chromium journeys. This CI coverage does not replace staging verification against the actual production PostgreSQL service, host TLS/reverse proxy, production CORS origins, secret manager, backups, and monitoring.

## Release blockers

- AstroAI elects the Swiss Ephemeris AGPL-3.0-or-later route. Keep calculation flags off until the entire project and required notices are published under AGPL, corresponding source is available to remote users, and independent reference testing is signed off. Obtain legal review if ownership or third-party compatibility is uncertain.
- There are 81 research topics in the catalogue but zero source-verified substantive rules and zero approved production interpretation rules. Chat can return saved calculated facts but cannot provide sourced traditional interpretations.
- Daily horoscope, Panchang, compatibility, report generation, and administrative knowledge management have no production-ready API workflow; the frontend presents explicit unavailable states where linked.
- Authentication now supports forgot/reset-password endpoints and revokes all existing access JWTs after a reset through the account auth-version claim. It still has no refresh-token rotation or email verification. SMTP credentials and sender-domain deliverability must be configured and tested by the deployer before claiming recovery email delivery works end-to-end.
- Login/registration have no distributed IP-based rate limiter. Add a trusted gateway/WAF policy before public exposure. Chat and password recovery use database-shared rate buckets.
- Human legal review, privacy/data-retention decisions, production Postgres exercise, staging release sign-off, restore rehearsal, monitoring thresholds, and support ownership remain outstanding.

AstroAI has not been deployed by this task and is not declared production-ready.
