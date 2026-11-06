# API specification

FastAPI generates OpenAPI at `/openapi.json` and Swagger UI at `/docs`.

- `POST /api/v1/auth/register` and `/auth/login`
- `POST /api/v1/auth/forgot-password` (neutral response; requires configured SMTP or development-only reset-link file)
- `POST /api/v1/auth/reset-password` (single-use token and new password)
- `GET /api/v1/profiles`, `POST /api/v1/profiles`, `GET /api/v1/profiles/{id}`
- `GET /api/v1/profiles/location-search?q={place}&language={en|ta}` (authenticated; server-side Geoapify key, minimum three-character query, rate limited)
- `POST /api/v1/horoscope/daily` (returns `available` only when exact scope/date has verified, reviewed, bilingual content with provenance; otherwise a reason-specific unavailable response)
- `POST /api/v1/astrology/charts` (202; creates an unavailable calculation record until engine configured)
- `GET /health`

Bearer access tokens are required for profile and chart routes. Pagination, refresh rotation, and the remaining requested endpoint groups are not yet implemented.
