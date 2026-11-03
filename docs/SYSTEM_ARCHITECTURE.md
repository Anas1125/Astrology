# System architecture

AstroAI is a modular monolith: React/Vite web client, FastAPI API, SQLAlchemy persistence, and PostgreSQL in production (SQLite for local tests). Versioned HTTP endpoints live under `/api/v1`; Alembic manages schema history. The backend contains replaceable Vedic and Western calculation adapters over a shared astronomy provider. Public calculations are disabled by configuration until accuracy and licensing reviews are complete.

The astrology chat path is deterministic Python: classifier → owner-scoped saved-chart fact adapter → versioned rule matcher → validated bilingual response composer. It makes no external inference calls. Interpretation knowledge is separate from chart calculations and must pass a human review lifecycle with registered source/edition provenance. The current included rule files are test-only; no substantive interpretation is production-approved.

AI messages and daily technical-usage counters persist in the relational database. Redis/Celery were described in the original architecture but are not currently used by application code; Redis is not required by the deterministic chat quota. Hosted static frontend, API/container, PostgreSQL, TLS termination, secret management, and operational monitoring are separate deployment concerns described in `DEPLOYMENT.md`.
