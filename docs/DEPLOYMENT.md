# Deployment

## Local development

Set up dependencies with `cd backend && python3 -m venv .venv && .venv/bin/pip install -e '.[dev]'`, then `cd ../frontend && npm install`. The development container uses PostgreSQL and Redis. Copy `.env.example` to `.env`, set a strong secret, then use Docker Compose. Network-restricted environments need approved access to PyPI and npm registry or pre-populated package caches; Python pip cache and npm cache are independent.

Start API with `cd backend && .venv/bin/alembic upgrade head && .venv/bin/uvicorn app.main:app --reload`; start client with `cd frontend && npm run dev`. Run API docs at `/docs`, health at `/health`.

For production, build the frontend with `npm run build` and deploy `frontend/dist` to Cloudflare Pages. Deploy the API container and PostgreSQL/Redis on a secured Docker-compatible VPS. Configure TLS/reverse proxy, restricted origins, credentials, migrations, backups and monitoring. The migration is authored but still needs execution verification in a dependency-enabled environment.

AI and Razorpay require provider credentials and their adapters are not yet connected to API routes. No payment success is simulated. Astrology engines are intentionally unavailable pending licensing and calculation validation.
