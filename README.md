# AstroAI

AstroAI is a multilingual astrology SaaS foundation built as a modular monolith: FastAPI backend, React/Vite frontend, PostgreSQL persistence, Redis/Celery jobs, and adapter-based astrology and AI services.

## Local development

1. Copy `.env.example` to `.env` and change secrets.
2. Start services: `docker compose up --build`.
3. API docs: http://localhost:8000/docs; frontend: http://localhost:5173.
4. The initial API supports health, registration/login, profile CRUD, and chart creation. Production setup requires migrations and credentials configured as described in `docs/DEPLOYMENT.md`.

Without Docker, run the backend with `cd backend && python -m venv .venv && . .venv/bin/activate && pip install -e '.[dev]' && uvicorn app.main:app --reload`; frontend with `cd frontend && npm install && npm run dev`.

## Status

See [docs/PROJECT_STATUS.md](docs/PROJECT_STATUS.md) for implemented modules, verification and known limitations. Astrology outputs are intentionally unavailable until a commercially suitable, verified ephemeris engine is selected.
