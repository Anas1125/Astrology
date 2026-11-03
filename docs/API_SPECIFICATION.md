# API specification

FastAPI generates OpenAPI at `/openapi.json` and Swagger UI at `/docs`.

- `POST /api/v1/auth/register` and `/auth/login`
- `GET /api/v1/profiles`, `POST /api/v1/profiles`, `GET /api/v1/profiles/{id}`
- `POST /api/v1/astrology/charts` (202; creates an unavailable calculation record until engine configured)
- `GET /health`

Bearer access tokens are required for profile and chart routes. Pagination, refresh rotation, and the remaining requested endpoint groups are not yet implemented.
