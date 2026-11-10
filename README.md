# AstroAI

AstroAI is a bilingual astrology application with a React/Vite frontend and a FastAPI backend. It uses PostgreSQL for production and SQLite for local tests. Its chat experience is deterministic Python code that reads owner-scoped saved chart facts and eligible, versioned knowledge rules when available; it does not call an external AI inference service.

## Local development

1. Copy `.env.example` to `.env` and set a unique local secret.
2. Start the development stack with `docker compose up --build`.
3. Apply migrations with `cd backend && .venv/bin/alembic upgrade head` (or run the repository-specific migration command in the deployment guide).
4. API docs: http://localhost:8000/docs; frontend: http://localhost:5173; liveness/readiness: `/health` and `/ready`.

Without Docker, run the backend with `cd backend && python -m venv .venv && .venv/bin/pip install -e '.[dev]' && .venv/bin/alembic upgrade head && .venv/bin/uvicorn app.main:app --reload`; frontend with `cd frontend && npm ci && npm run dev`.

## License and source

AstroAI is licensed under the GNU Affero General Public License, version 3 or (at your option) any later version (`AGPL-3.0-or-later`). See [LICENSE](LICENSE). This project elects the AGPL licensing route for its use of Swiss Ephemeris. The application provides a visible source-code and license notice for remote users; the corresponding source is available from this public repository.

## Status

See [docs/PROJECT_STATUS.md](docs/PROJECT_STATUS.md) for verified functionality and blockers. Public chart calculations remain disabled until the Vercel runtime, official ephemeris data, AGPL source offer, and independent calculation reference checks are verified. No substantive astrology interpretation rules are approved yet, so chat reports calculated saved-chart facts when present and states that sourced interpretations are unavailable.
