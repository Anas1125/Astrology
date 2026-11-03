# AstroAI

AstroAI is a bilingual astrology application with a React/Vite frontend and a FastAPI backend. It uses PostgreSQL for production and SQLite for local tests. Its chat experience is deterministic Python code that reads owner-scoped saved chart facts and eligible, versioned knowledge rules when available; it does not call an external AI inference service.

## Local development

1. Copy `.env.example` to `.env` and set a unique local secret.
2. Start the development stack with `docker compose up --build`.
3. Apply migrations with `cd backend && .venv/bin/alembic upgrade head` (or run the repository-specific migration command in the deployment guide).
4. API docs: http://localhost:8000/docs; frontend: http://localhost:5173; liveness/readiness: `/health` and `/ready`.

Without Docker, run the backend with `cd backend && python -m venv .venv && .venv/bin/pip install -e '.[dev]' && .venv/bin/alembic upgrade head && .venv/bin/uvicorn app.main:app --reload`; frontend with `cd frontend && npm ci && npm run dev`.

## Status

See [docs/PROJECT_STATUS.md](docs/PROJECT_STATUS.md) for verified functionality and blockers. Public astrology chart calculations remain gated pending Swiss Ephemeris accuracy and commercial licensing review. No substantive astrology interpretation rules are approved yet, so chat reports calculated saved-chart facts when present and states that sourced interpretations are unavailable.
