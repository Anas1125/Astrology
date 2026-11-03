# Test and verification guide

## Backend

From `backend/`:

```sh
.venv/bin/python -m pytest -q
.venv/bin/ruff check .
.venv/bin/alembic upgrade head
```

The unit/API suite uses SQLite. Optional native Swiss Ephemeris tests skip with a reason when the binding/data are not provisioned. Do not treat those skips as verification of a production Swiss runtime. The API calculation feature gates remain false by default.

## Frontend and browser journeys

From `frontend/`:

```sh
npm ci
npm test
npm run build
npx playwright install chromium
npm run test:e2e
```

Playwright starts local API and Vite processes and uses an isolated disposable test database/account. The E2E suite exercises existing supported journeys; when astrology calculations are gated, tests must validate the unavailable response rather than fabricate positions.

## Release validation

The CI workflow includes Ruff, backend pytest, Alembic upgrade/downgrade/upgrade against SQLite, frontend tests/build, and Playwright. Before release, additionally exercise PostgreSQL migrations against a restored staging backup, verify owner isolation with separate accounts, test actual deployment origins/TLS, restore a backup, and review logs/secrets configuration.

Test totals and skipped optional tests are recorded in `docs/PROJECT_STATUS.md`. A green test run verifies only the scenarios represented by those tests; it does not establish calculation licensing, source accuracy, copyright clearance, or production readiness.
