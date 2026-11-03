# Security and privacy review

This is an engineering review of implemented controls and remaining release work, not a security certification or legal-compliance determination.

## Controls present in the current code

- Passwords are hashed with Argon2id through `pwdlib`; authentication uses the existing short-lived HS256 access JWT and does not store passwords in the browser.
- Authenticated API routes use the existing bearer dependency. Profile, chart history, chart retrieval, AI conversations, and selected saved-chart context apply owner filters. AI context only loads a completed chart and its completed run. Deactivated accounts are rejected at login and existing bearer tokens stop working on the next authenticated request.
- SQLAlchemy expressions use bound parameters. Request models constrain fields and lengths; uploaded files are not currently accepted by the API. Calculation runtime/native errors are converted to a generic unavailable response so server paths and native diagnostics are not returned to clients.
- AI responses use only validated saved-chart facts and production-eligible sourced rules. Birth date/time, place, coordinates, and profile snapshots are not sent into response facts. There are no external inference calls in the active deterministic chat path.
- Daily AI abuse quota reservation is an atomic database operation and is isolated by user/day. Idempotency keys are user-scoped and bound to message hashes.
- Production configuration rejects the development secret, secrets shorter than 32 characters, SQLite, wildcard CORS, and non-HTTPS origins. Responses include content-type, framing, referrer and permissions headers; HSTS is added in production mode.
- `/health` and `/ready` separate process liveness from database readiness. Readiness errors are sanitized.

## Items to complete before public access

- Add shared IP/network rate limiting at a trusted gateway or WAF for registration, login, and general API abuse. The AI daily quota is not an IP limiter.
- Implement refresh-token rotation/revocation, email verification, account recovery, and credential-stuffing defenses. Current access tokens expire and require the user to sign in again.
- Choose and document retention/deletion/export rules for account, birth-profile, chart, and conversation records; test the lifecycle in PostgreSQL.
- Decide whether sensitive birth fields require encryption at rest beyond storage-provider/database encryption, and review database/log access policies.
- Configure a trusted TLS proxy and origin allowlist; validate deployment-specific headers and rate limits from outside the app network.
- Review dependency advisories using current approved vulnerability scanners and registry metadata. This local run had no verified online advisory feed; passing package tests is not a vulnerability scan.
- Review Swiss Ephemeris and wrapper licenses, privacy terms, and any future source-content reuse with qualified counsel.
- Conduct a targeted security assessment and incident/backup restore rehearsal. No certification is claimed.

## Operational rules

- Keep `.env` and production secrets outside Git and container images. Keep ephemeris data and native libraries outside the repo and image.
- Never log passwords, access tokens, birth details, profile input snapshots, or conversation bodies.
- Keep `ASTROLOGY_CALCULATIONS_ENABLED=false` and `SWISSEPH_LICENSE_CONFIRMED=false` until calculation accuracy and licensing reviews are formally complete.
- Never interpret a passing test suite as proof of security, legal compliance, or production readiness.
