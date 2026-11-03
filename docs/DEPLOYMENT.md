# Deployment and release preparation

This guide prepares the existing AstroAI API image and static frontend for a controlled deployment. It does not authorize a public launch. No live service was changed as part of this work.

## Runtime requirements

- Backend: Python 3.12 slim container, FastAPI/Uvicorn, SQLAlchemy, Alembic, and PostgreSQL via psycopg.
- Frontend: static Vite build in `frontend/dist`; deploy to the selected HTTPS static host/CDN.
- Database: PostgreSQL. SQLite is supported for local tests only.
- The AI chat path is deterministic and has no model/provider/API-key requirement. The daily abuse limit is database-backed; Redis is not required by current application code.
- Public astrology calculation routes remain disabled. Swiss Ephemeris data files and native libraries are not copied into the image; a license review is unresolved.

## Environment configuration

Set these through the hosting platform's secret/configuration manager. Do not put production values in `.env`, image build arguments, CI logs, or Git.

| Variable | Production requirement |
| --- | --- |
| `APP_ENV` | `production` |
| `SECRET_KEY` | Unique random secret, at least 32 characters; rotate through a planned key migration |
| `DATABASE_URL` | `postgresql+psycopg://...` with a dedicated least-privilege application user |
| `CORS_ORIGINS` | Comma-separated exact HTTPS frontend origins; no wildcard |
| `AI_FREE_DAILY_LIMIT` | Technical abuse cap, default 20; not a paid tier |
| `ASTROLOGY_CALCULATIONS_ENABLED` | `false` until the calculation/licensing gate is completed |
| `SWISSEPH_LICENSE_CONFIRMED` | `false` until reviewed and approved outside the application |

Production settings reject the development JWT secret, short secrets, SQLite, wildcard CORS and non-HTTPS origins. TLS termination must be configured at the load balancer/reverse proxy. Do not trust forwarded headers until the proxy network and forwarded-header policy are explicitly configured.

## Build and run the API image

From the repository root:

```sh
docker build -t astroai-api:release-candidate ./backend
docker run --rm --env-file /secure/path/astroai-api.env -p 8000:8000 astroai-api:release-candidate
```

The container runs as an unprivileged `astroai` user. Its `.dockerignore` excludes environment files, databases, test files, ephemeris data, and native Swiss Ephemeris libraries. The image contains the Alembic configuration and migration scripts and installs only the core backend package; the optional `astrology` extra is not installed.

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

- Swiss Ephemeris and `swisseph-ffi` commercial/network-use licensing requires professional review. Calculation flags stay off until approval and independent reference testing are signed off.
- There are 81 research topics in the catalogue but zero source-verified substantive rules and zero approved production interpretation rules. Chat can return saved calculated facts but cannot provide sourced traditional interpretations.
- Daily horoscope, Panchang, compatibility, report generation, and administrative knowledge management have no production-ready API workflow; the frontend presents explicit unavailable states where linked.
- Authentication has short-lived access JWTs but no refresh-token rotation, revocation, email verification, or password reset flow. Reauthentication is required at expiry.
- Login/registration have no distributed IP-based rate limiter. Add a trusted gateway/WAF policy before public exposure; do not rely on a per-process counter in a multi-worker deployment.
- Human legal review, privacy/data-retention decisions, production Postgres exercise, staging release sign-off, restore rehearsal, monitoring thresholds, and support ownership remain outstanding.

AstroAI has not been deployed by this task and is not declared production-ready.
