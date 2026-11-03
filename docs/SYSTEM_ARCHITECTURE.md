# System architecture

AstroAI uses a modular monolith: React/Vite web client, FastAPI application, SQLAlchemy persistence, PostgreSQL, Redis and worker-ready Celery infrastructure. API routes are versioned under `/api/v1`. Calculation and AI provider integrations belong behind replaceable service adapters. The current API exposes health, auth, profiles and chart requests; the chart service reports unavailable until an appropriate verified ephemeris is selected.
