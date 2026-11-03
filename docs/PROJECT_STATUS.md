# Project status

Updated: 2026-11-03

## Environment findings
- Runtime versions: Python 3.14.7, Node.js 26.9.0, npm 11.19.1. A system Python 3.9.6 is also present but is below the backend's Python >=3.11 requirement.
- Python dependencies are declared at exact versions in `backend/pyproject.toml`. Pip was run inside `backend/.venv`; outbound DNS to `pypi.org` failed. The system Python is PEP 668 externally managed. Pip cache is disabled/unowned at the configured `~/Library/Caches/pip`; an isolated cache directory had no packages.
- npm registry is `https://registry.npmjs.org/`. npm cache contains selected tarballs but lacks metadata needed for offline dependency resolution (`npm install --offline` returns ENOTCACHED for @vitejs/plugin-react). Network access therefore blocks install/build. Exact frontend dependency pins have been added, but a lockfile could not be generated.
- Resume installs with `cd backend && .venv/bin/pip install -e '.[dev]'` and `cd frontend && npm install`; then run `cd backend && .venv/bin/pytest`, `cd backend && .venv/bin/alembic upgrade head`, and `cd frontend && npm run build`.

## Implemented in this continuation
- Expanded SQLAlchemy entities for profile sharing, calculation snapshots, AI sessions/messages/usage/prompt versions, plans/entitlements/subscriptions, payments/webhooks, reports, compatibility, horoscope content, Panchang and audit logs.
- Added Alembic environment and initial schema revision `0001_initial_schema`; app startup no longer calls `metadata.create_all()`.
- Added chart run config/version fields, timestamps, constraints and indexes.
- Added owner-scoped profile PATCH and DELETE endpoints.
- Added provider-independent async OpenAI-compatible SSE adapter, owner-scoped saved-chart context, bilingual safety prompts, persistent conversation APIs, streaming routes, usage accounting and a dashboard AI chat experience (see Phase 4 verification below).
- Engine interfaces are independent for Vedic and Western chart/positions/houses/transits/compatibility and explicitly report unavailable until a verified commercially cleared engine is configured. No unlicensed Swiss Ephemeris dependency or invented results are included.
- Frontend dependency versions are now pinned. UI language switching is implemented without unavailable i18next packages; customer sidebar modules navigate locally and profile management is connected to the owner-scoped API.
- Added two Node built-in smoke tests.

## Verification actually performed
- `python3 -m compileall -q backend/app backend/alembic` passed (syntax only; imports against third-party dependencies were not possible).
- `node --test frontend/test/*.test.mjs` passed: 2 tests.
- Backend installation, imports, HTTP health checks, Alembic execution, frontend build, browser journeys and database-backed tests were not run because dependencies could not be installed.

## Pending
- Database-backed migration verification; consider split `profile_birth_details` model/encryption and complete required entities such as sessions, planets, houses, aspects, divisions, dasha, yogas/doshas, horoscope translation workflows and admin config.
- Secure auth lifecycle (refresh rotation, verification/reset, rate limiting, RBAC policies), profile timezone/DST validation and sharing API.
- Professional licensing clearance and independent production reference sign-off remain pending for Swiss Ephemeris. Vedic D1/D9/Nakshatra/Lagna/Vimshottari implementations now pass current unit/native/API tests; public chart calculations remain disabled. Western transits are not implemented.
- AI output moderation/provider staging validation, atomic distributed quota enforcement and subscription entitlements (not part of Phase 4).
- Horoscope/Panchang/compatibility calculations, PDF generation/fonts, Razorpay verified webhooks, admin APIs/UI and customer API wiring.
- Playwright and backend integration suites; frontend production build.

## Next actions
1. Restore access to approved PyPI/npm registries or provide a local wheelhouse/cache, then install pinned dependencies and generate `frontend/package-lock.json`.
2. Run/import-check the API and migration on PostgreSQL and SQLite, fix runtime issues, and add DB-backed tests.
3. Complete the modular service endpoints and frontend flows after selected provider/license decisions.

## Swiss Ephemeris dependency verification gate (2026-11-03)
- Inspected the published `swisseph-ffi==1.0.0` package and source/API documentation. It is a Python `ctypes` wrapper exposing raw Swiss Ephemeris C functions; its published wheel is `py3-none-any`, while the package documentation states it bundles native libraries for Linux x64/arm64, macOS x64/arm64 (`macos-arm64/libswe.dylib`), and Windows. It also supports `SWISSEPH_LIBRARY_PATH` override and documents bundled/system library lookup. These are publisher/source claims; this machine did not obtain the wheel, so the ARM64 Mach-O binary and actual `otool -L` dependency chain were not independently inspected.
- Wrapper metadata declares AGPL-3.0-or-later. Swiss Ephemeris separately offers AGPL or its professional license; the wrapper's AGPL terms must be reviewed independently, and a Swiss Ephemeris professional license does not by itself change the wrapper's license. No commercial deployment clearance is claimed. See [Swiss Ephemeris licensing documentation](https://www.astro.com/swisseph/swisseph.htm) and [swisseph-ffi 1.0.0 package/API information](https://pypi.org/project/swisseph-ffi/1.0.0/).
- Platform is macOS ARM64 with Python 3.14.7. The isolated environment `/private/tmp/astroai-swe314` was created, but installing the package failed because DNS resolution for `pypi.org` fails. No existing project environment was changed. Local search found no Python 3.13 interpreter, cached `swisseph-ffi` distribution, native library, or `.se1` ephemeris files. Python 3.13 runtime compatibility therefore remains unevaluated; installing another interpreter requires a reachable approved package source.
- Runtime PoC status: **not run**. The isolated environment could not install the wrapper and no ephemeris data are available. Consequently Julian Day through the wrapper, a known planetary position, Lahiri ayanamsa, missing-data error behavior in the real native library, and independent accuracy comparisons have not passed runtime verification. Published independent reference material located for a future gate includes the Astronomical Almanac 2016 Venus example (Swiss Ephemeris documentation, p. B68–B70) and the Indian Astronomical Ephemeris 2019 Lahiri reference (documented in the same source); do not treat these documented values as local test results.
- Existing AstroAI Swiss adapter code is experimental and **not production-ready**. Public calculation routes remain disabled: `astrology_calculations_enabled=false` and `swisseph_license_confirmed=false` by default. Do not enable them until the native ARM64 library/dependencies, Python runtime, actual ephemeris files, reference accuracy, missing-file behavior, and both licensing questions pass review.
- Gate checks: attempted isolated `pip install --no-cache-dir swisseph-ffi==1.0.0` under Python 3.14; **failed** at DNS resolution (`NameResolutionError` for `pypi.org`). Python 3.13 check: **not satisfied** (interpreter not present; no local cached install found). Native PoC and Swiss accuracy checks: **not run** due unavailable package and data. No full adapter implementation proceeded after this gate result.
- Next gate actions: provide working access to an approved Python registry/wheelhouse and Swiss Ephemeris data source; provision Python 3.13 separately if 3.14 cannot be validated; inspect the extracted macOS ARM64 dylib with `file`/`otool -L`/signature tools; run the documented JD, Venus and Lahiri reference PoC; verify strict missing-file failure; complete wrapper and engine license review. Only then decide whether to continue with this binding.

## Authentication Swagger fix (2026-11-03)
- `/api/v1/auth/login` now depends on FastAPI `OAuth2PasswordRequestForm`, matching Swagger OAuth2 `application/x-www-form-urlencoded` requests (`username`, `password`). `username` is looked up in `users.email`; password checks use the existing `verify_password`; successful responses use the existing `TokenResponse` and existing `create_access_token` JWT implementation.
- Added exact dependency `python-multipart==0.0.20`, needed by FastAPI form parsing.
- Registration and `current_user` / OAuth2 bearer JWT verification are unchanged.
- Added five tests in `backend/tests/test_auth.py`: successful form login, incorrect password, unknown email, OpenAPI Swagger form/token URL, and registration regression.
- Verification: Python `compileall` passed; existing Node tests passed 2/2. Backend pytest tests were not run because `backend/.venv/bin/pytest` is absent and dependency installation remains blocked by registry connectivity. No backend test pass is claimed.

## Frontend authentication experience (2026-11-03)
- Added a polished AstroAI public welcome page and linked Sign Up / Log In flows, retaining the existing navy, midnight and gold design.
- Registration calls `POST /api/v1/auth/register` with the backend-supported `{email,password}` JSON contract; confirms password locally and enforces the backend's 12–128 character password limits. The current backend has no `full_name` field, so the page explains that a name belongs in a birth profile rather than sending unsupported account data.
- Login calls `POST /api/v1/auth/login` as URL-encoded OAuth2 form fields (`username=email`, `password`). Both flows use the returned `access_token`.
- Added `/api/v1/auth/me` so the client can verify an existing token and show actual account email/role. Dashboard route `/app/*` is protected, restores same-tab sessions from `sessionStorage` after reload, clears expired/invalid tokens when `/auth/me` rejects them, and offers logout. Passwords are never stored in browser storage.
- Access JWT lifetime remains 20 minutes. The API has no refresh-token endpoint or HttpOnly refresh-cookie mechanism; users sign in again after expiration. This limitation is intentional and no refresh endpoint was invented.
- Existing owner-scoped profile API queries are unchanged. Frontend profile form is still not wired to profile endpoints.
- Added frontend contract/auth route regression checks and backend tests for `/auth/me` success and missing-token rejection.

### Verification
- `npm run build`: passed (TypeScript and Vite production build; 1596 modules transformed).
- `npm test`: passed, 5/5 Node smoke tests.
- `python3 -m compileall -q backend/app backend/tests`: passed (syntax only).
- Backend pytest was attempted but could not run: `No module named pytest` in the available Python environment. Backend endpoint tests remain unverified.

## Birth profile management (2026-11-03)
- Connected the existing dashboard Birth Profiles item to authenticated `GET/POST /api/v1/profiles` and `PATCH/DELETE /api/v1/profiles/{id}` client operations using the current bearer token.
- Implemented profile listing, create, edit, delete with browser confirmation, loading/empty/error states, retry, field validation, and success notifications. Displays profile relationship, birth date/time, birthplace/country, coordinates and timezone.
- Form supports display name; relationship type; date; exact/approximate/unknown time accuracy; birth time; birthplace; country; latitude/longitude; IANA timezone. Exact time requires a time; unknown time is sent as null. Manual location input is clearly labeled.
- Backend schemas validate nonblank display name/place, relationship and time accuracy values, future dates, exact-time requirements, coordinate ranges/pairs, timezone identifiers through Python `zoneinfo`, and text lengths. Existing handlers already scope profile reads/updates/deletes to the authenticated owner; tests cover cross-user isolation.
- Existing SQLAlchemy `BirthProfile` model and `0001_initial_schema` migration already include all requested fields (birth time, relationship, accuracy, birthplace, country, latitude, longitude, timezone). No schema change was needed; no migration was added or existing data/table recreated.
- No geocoder/location provider is integrated. Coordinates and IANA timezone must be supplied by the user; the application does not infer either.

### Verification
- `python3 -m compileall -q backend/app backend/tests backend/alembic`: passed (syntax only).
- `npm test`: passed, 8/8 Node smoke tests.
- `npm run build`: passed (TypeScript and Vite production build; 1597 modules transformed).
- Backend pytest attempted: not run because the Python environment has no pytest (`No module named pytest`). Profile endpoint test code is present but remains unexecuted. Frontend smoke tests check API contracts and rendered workflow source patterns; interactive browser automation was not run.

## Vedic engine milestone 2 (2026-11-03)
- Implemented Vedic D1/D9 derivations on the shared Swiss Ephemeris provider. D1 planetary data retain the planet name and include sidereal longitude, sign/Rashi, configured-cusp house, retrograde status and nested Nakshatra data. Mean Rahu is calculated by Swiss Ephemeris; Ketu is recorded exactly opposite, with the node model identified in result metadata.
- Added Navamsa segment mapping and movable/fixed/dual sign starts; D9 transformed planetary/Ascendant placements and house sectors use the selected house system's D1 cusps transformed into Navamsa longitudes. The response includes both D1 and requested division placements.
- Nakshatra data now include the 27-star sequence, lord, Pada and remaining fraction/degrees. Boundary computations snap only floating-point noise at exact partition boundaries; Navamsa tests cover all 96 within-sign transitions.
- Added Vimshottari Mahadasha and Antardasha periods with the nine-lord order, birth balance, partially elapsed Antardashas, and explicit `savana_360_day` (360-day year) metadata. No other year convention is accepted.
- `POST /api/v1/astrology/charts/vedic` accepts `division` (`D1` default or `D9`) and the explicit dasha convention. Existing JSON chart/run persistence stores the result, profile input snapshot, division/configuration and engine/ephemeris versions. No database schema migration is required. Existing profile ownership checks apply to calculation and retrieval.
- Western request schema does not expose Vedic division or dasha fields. Unsupported Western D9 input is rejected. Calculation and Swiss licensing flags remain disabled by default; the implementation is not enabled for public chart requests.
- Updated [ASTROLOGY_ENGINE.md](ASTROLOGY_ENGINE.md) with API example and convention details. Swiss Ephemeris and wrapper licensing review remains unresolved; no commercial rights are claimed.

### Verification
- Full backend suite using the external native test environment (`swisseph-ffi==1.0.0`, Swiss Ephemeris 2.10.03, external `sepl_18.se1` / `semo_18.se1`): **163 passed, 0 failed**. This included real native D1/D9 calculations and Lahiri/Swiss-file calculations; no tests skipped in this run.
- Boundary/unit coverage includes all 12 Rashi starts, all 12 Navamsa start-sign rules, 96 Navamsa segment transitions, 27 Nakshatra boundaries/Pada transitions, Dasha sequence/duration/balance and partial Antardasha checks. API tests cover D9 persistence and cross-user calculation/retrieval denial.
- 26 existing dependency deprecation warnings were reported. No frontend code changed and no frontend build/test was required for this backend-only milestone.
- No migration generated because existing `birth_charts` and `chart_calculation_runs` JSON/config/version fields hold the added data.
- This native run supersedes earlier environment-gate notes above that recorded wrapper/data unavailability at that time; verification was performed using the subsequently supplied external test environment, without copying its native library or ephemeris files into the repository.

## Western natal engine milestone 3 (2026-11-03)
- Completed the Western tropical natal adapter over the shared astronomy provider; no planetary calculation code was duplicated. Planet positions retain provider speed/retrograde data and now include tropical sign/degrees and configured-cusp house membership. Ascendant and Midheaven include tropical sign/degrees and chart metadata.
- Added all five major aspects (conjunction, sextile, square, trine, opposition). Defaults are 6 degrees each; API overrides normalize against these defaults, are range-checked, and are saved in the chart config/result. Applying/separating is derived from relative geocentric ecliptic longitude speeds; missing speeds are reported as `unknown`, exact aspects as `exact`.
- Supported house codes/name metadata include Placidus (`P`) and Whole Sign (`W`), plus the additional Swiss house systems accepted by the shared provider. Swiss house calculation failures (including latitude-specific Placidus errors) return a clear validation error with Whole Sign/Equal alternatives. Birth time, timezone, and coordinates remain validated through existing conversion/provider checks.
- Western route uses existing authentication, owner-scoped profile lookup and saved chart/run snapshots. Persistence includes effective house/aspect configuration plus provider and Western engine versions; chart retrieval remains owner-scoped. D9 is not accepted on the Western route. Public calculation/license flags remain false.
- No migration required: existing chart/run JSON config/result and engine version fields persist these values.

### Verification
- Added `backend/tests/test_western_engine.py` for all five aspects, orb boundaries, applying/separating, missing-speed behavior, sign/house assignment, retrograde metadata, invalid dates/times/coordinates, invalid or unsupported house systems, and public-flag guards.
- Added native tests for the J2000 tropical Sun against the U.S. Naval Observatory approximate apparent geocentric ecliptic-longitude algorithm; Ascendant/Midheaven against independent GMST/obliquity equations; Whole Sign cusp spacing; and the Swiss Ephemeris manual Placidus cusp/Ascendant reference (2000-01-26 08:08 UT, 30E, 66.562N).
- Added Western chart API persistence/configuration and profile-ownership tests. Existing native missing-file and Moshier fallback-rejection tests remain in the full suite.
- Full backend pytest with the external native runtime and ephemeris data: **184 passed, 0 failed, 0 skipped** (26 dependency deprecation warnings).
- Commercial Swiss Ephemeris/wrapper licensing review remains unresolved. Calculation flags remain disabled; passing tests do not grant commercial deployment rights.

## Phase 3: Astrology dashboard integration (2026-11-03)
- Replaced the dashboard's Vedic and Western astrology placeholder destinations with an authenticated chart workspace while retaining the existing dashboard shell and design. The workspace loads owner-visible birth profiles, remembers the selected profile in session storage, and offers Vedic/Western selection, D1/D9, and house-system controls.
- Frontend calls the existing contracts: `POST /api/v1/astrology/charts/vedic` with `profile_id`, `division`, `house_system`, and the explicit `savana_360_day` convention; `POST /api/v1/astrology/charts/western` with `profile_id`, `house_system` and optional `aspect_orbs`; and `GET /api/v1/astrology/charts/{chart_id}` to retrieve persisted results. Requests use the current bearer token. The response envelope consumed is `chart_id`, `profile_id`, `calculation_system`, `status`, version/configuration/snapshot metadata, `result`, and `calculated_at`.
- Saved chart IDs are remembered per account, profile, system, division and house system in session storage. Because the API has no chart-list endpoint, the frontend can retrieve a previously calculated result only when its ID is still known in that browser session; it does not invent or request unsupported fields.
- Vedic views render API-provided D1/D9 placements in South Indian or North Indian layouts, with ascendant, houses, planet table, Nakshatra/Pada and Vimshottari Mahadasha/Antardasha. Western views render API-provided tropical planet positions, house cusps, Ascendant, Midheaven and aspects in a circular chart and details table. English and Tamil chart text and astronomical labels are covered.
- Loading, no-profile/no-chart, incomplete birth data, API error and HTTP 503 calculation-unavailable states are explicit. The client preserves server feature gates and does not fabricate placements. Calculation flags remain disabled by default; Swiss Ephemeris and wrapper licensing review remains unresolved.
- No backend, engine, database or migration changes were required. Authentication and profile APIs remain the existing implementations.

### Verification
- Added `frontend/test/astrology-dashboard.test.mjs`: exact API URLs/bodies/auth headers and saved retrieval, error/gate propagation, profile choice and cache scoping, controlled-fixture rendering of Vedic D1/D9 and both chart layouts, Western wheel/angles/aspects, loading/error/unavailable/empty feedback, and English/Tamil key parity.
- `cd frontend && npm test`: **15 passed, 0 failed, 0 skipped**.
- `cd frontend && npm run build`: **passed** (TypeScript check and Vite production build).
- These frontend tests use controlled response fixtures and server rendering; a live browser-to-backend chart journey was not run. With public calculation flags disabled, actual chart requests are expected to honor the server's unavailable response until separately authorized and licensing review is complete.

## Phase 3, Milestone 2: Persistent chart history and end-to-end integration (2026-11-03)
- Added authenticated `GET /api/v1/astrology/charts` with optional `profile_id` and `system=vedic|western` filters and bounded `limit`/`offset` pagination. Response shape is `{items,total,limit,offset}`; each item contains chart `id`, `profile_id`, `profile_name`, `system`, `division`, `status`, `created_at`, `configuration`, and `unavailable_reason`. It returns no birth date/time, birthplace, coordinates, timezone, input snapshot or planetary result.
- History queries join through `birth_profiles` and apply the authenticated owner's ID before filters, count or page selection. Existing `GET /astrology/charts/{chart_id}` remains owner-scoped for opening complete saved results. No table or migration change was needed; existing chart/profile foreign keys and indexes support the query.
- Replaced session-only chart ID restoration with server history retrieval. The frontend filters history by selected profile/system, pages through results, and retrieves complete charts by their saved ID. Incomplete/unavailable chart records show the unavailable explanation instead of pretending to contain a result. Only the selected profile ID remains in session storage.
- Any API 401 now clears the local access-token session. `ProtectedRoute` then redirects to login. Existing network and 503 UI error states remain explicit.
- Added Playwright end-to-end coverage using a disposable SQLite database at the OS temporary directory and unique `example.com` test accounts. The test exercises registration, login, no-profile state, profile creation/selection, Vedic D1/D9 selection, Vedic and Western unavailable responses with both server flags false, persisted chart history, logout/login persistence, network error/retry, and invalid-token redirection. An unavailable chart row is created using the existing authenticated `POST /api/v1/astrology/charts` endpoint because calculations are intentionally gated; no chart result is seeded or fabricated.
- Added backend tests for owner isolation, profile/system filters, pagination, response privacy, invalid filters/limits and missing authentication. Added frontend API contract checks for history filter URL construction and bearer headers.
- Playwright dependency pinned to `@playwright/test==1.64.0`; E2E command is `cd frontend && npm run test:e2e`.

### Verification
- Backend full pytest: **171 passed, 14 skipped, 0 failed**. The skips require the optional `swisseph-ffi` native package and/or external `.se1` files, which were unavailable in this run. 28 dependency deprecation warnings.
- Frontend full tests: **15 passed, 0 skipped, 0 failed**.
- Frontend production build: **passed** (TypeScript and Vite; 1604 modules transformed).
- Playwright: **1 passed, 0 failed** against the real local FastAPI and Vite servers with an isolated temporary SQLite database. Calculation and licensing flags were both explicitly false. This verifies the unavailable-state path; it does not verify live astronomical chart calculation.
- `@playwright/test==1.64.0` is recorded in `package.json` and `package-lock.json`. This checkout's npm offline install was blocked by registry metadata/cache permission errors, so the passing run resolved the same installed 1.64.0 package from the machine's existing local package installation. A clean environment should run `npm ci` with registry access to install from the lockfile.
- Calculation flags remain disabled and commercial licensing clearance remains unresolved.
## Phase 4 — AI Astrologer (2026-11-03)

> Historical implementation record. The external-provider design described here was later replaced by the deterministic internal engine in Milestones 1–5 below. Provider code and configuration are no longer part of the active application.

### Implemented
- Added a provider-neutral async `AIProvider` protocol and OpenAI-compatible SSE adapter. The server loads provider, base URL, API key, model, timeout and token limit from environment settings. Missing/incomplete configuration returns a clear 503; provider failures are sanitized and no credentials are sent to or returned by the frontend.
- Added authenticated conversation create/list/history/delete and message endpoints under `/api/v1/ai/conversations`. Both normal and SSE message submission persist user/assistant messages. SSE emits `delta`, `done`, and sanitized `error` events. Provider usage metadata is saved when supplied, and assistant messages record provider/model/prompt version.
- Added owner-checked saved chart context retrieval. Context is only built from a completed persisted chart and completed calculation run whose profile belongs to the caller. It contains curated Vedic placements/Nakshatra/Dasha or Western houses/aspects, not profile birth details or calculation input snapshots. Missing chart context is explicitly represented and does not trigger a calculation.
- Added English and Tamil system prompts that separate calculated facts from interpretation, frame astrology as reflective rather than scientific certainty, restrict medical/legal/financial diagnosis and guarantees, and prohibit disclosure of internal prompts or provider credentials.
- Added a configurable free daily request limit (`AI_FREE_DAILY_LIMIT`, default 20) and bounded history context (`AI_HISTORY_MESSAGE_LIMIT`, default 20). Request attempts are counted before provider execution, including provider failures; token counts are recorded when the provider returns usage. This is a basic per-user quota, not a subscription entitlement or distributed atomic rate limiter.
- Added the dashboard AI Astrologer experience with profile, astrology system and completed saved chart selection; persistent conversation history; bilingual chat; streaming responses; deletion; no-chart guidance; usage display; and safety disclaimer. Existing calculation feature/licensing gates are untouched.
- Added nullable `chat_sessions.chart_id` association with `ON DELETE SET NULL` in Alembic revision `0003_ai_chat_chart`; existing conversations remain valid without chart associations. SQLite upgrade → downgrade → upgrade was verified against a temporary database.

### Verification
- Backend: `backend/.venv/bin/python -m pytest -q` — **179 passed, 14 skipped, 0 failed**. Existing skipped tests require external Swiss Ephemeris runtime/data. New tests cover provider configuration, SSE parsing/usage, timeout and HTTP failure handling, saved Vedic/Western chart context privacy, missing context, conversation ownership, persistence, streaming, quotas, and Tamil prompts.
- Frontend: `npm test` — **18 passed, 0 failed**.
- Frontend production: `npm run build` — **passed** (TypeScript check and Vite production bundle).
- Backend style check: Ruff on changed AI/backend files — **passed**.
- Alembic SQLite migration upgrade/downgrade/upgrade — **passed**.
- No live AI provider request was made because no provider credentials were configured in the environment. Provider API interoperability, generated-answer quality, model safety behavior, and token accounting against a live provider remain unverified.

### Remaining limitations / next tasks
- Configure an approved provider and credentials in the backend environment, then run a staging smoke test before presenting AI responses as available. The implementation currently supports OpenAI-compatible chat-completion SSE providers only.
- Add production moderation/output policy review, cancellation/backpressure handling, and atomic distributed quota enforcement before high-concurrency deployment. Provider attempts that fail after reservation currently consume quota and leave the submitted user message in history.
- This milestone does not add subscriptions/payments, refresh-token functionality, astrology calculation capability, or any calculation/licensing bypass. Swiss Ephemeris commercial deployment clearance remains unresolved; public calculation gates remain disabled by default.

## Phase 4 verification and hardening (2026-11-03)

> Historical verification record for the superseded provider-based implementation. Current architecture and verification are recorded in the deterministic milestones and release-hardening section below.
- Provider settings were inspected without printing credentials: provider name is `openai-compatible`; base URL, API key and model are all unconfigured. **No live provider request was made.** To enable an approved provider, install `cd backend && pip install -e '.[ai]'`, then configure `AI_PROVIDER`, `AI_BASE_URL` (HTTPS API prefix ending before `/chat/completions`), `AI_API_KEY`, `AI_MODEL`, `AI_TIMEOUT_SECONDS`, and `AI_MAX_TOKENS` in the backend environment. Plain HTTP is accepted only for loopback development/testing. The adapter verifies bearer header/model/base URL, SSE deltas and usage extraction, bounded timeout, and sanitized HTTP/transport errors in tests.
- Replaced count-then-insert quota checks with `ai_usage_daily_counters`, keyed by user and UTC day, reserved through a conditional atomic upsert for SQLite and PostgreSQL. Concurrent SQLite requests were tested; no Redis dependency is required for this database-backed reservation. Migration `0004_atomic_ai_usage` backfills existing `ai_chat` usage rows and adds request status/idempotency fields.
- `Idempotency-Key` now prevents duplicate submissions per user and binds a key to a SHA-256 hash of message content. Completed requests replay their saved response, in-flight duplicates return 409, and retrying a failed request with the same key does not consume another quota slot. Failed provider attempts still count once; interrupted/empty responses do not save partial assistant messages and become retryable. Added the header to CORS and covered its preflight.
- Added tests for provider configuration and errors, Vedic/Western context and private-field exclusion, ownership, unavailable chart context, streamed persistence, empty/error/interrupted streams, client disconnect state, failed-request retry/replay, key mismatch, atomic concurrency, and per-user quota isolation. The E2E journey now uses a deterministic local OpenAI-compatible mock server and a temporary database; no customer data or live provider is used.
- The dashboard language switch is available on AI/chat pages. Playwright covers actual login/profile selection, the no-chart path, streaming and persisted message history after a new login, Tamil UI, and conversation deletion.

### Final verification
- Backend pytest: **186 passed, 14 skipped, 0 failed** (the existing Swiss Ephemeris data/runtime skips remain); Ruff passed. 40 dependency deprecation warnings remain.
- Frontend tests: **19 passed, 0 failed**. Production build passed.
- Playwright: **1 passed, 0 failed** using isolated local API, Vite and deterministic mock provider servers.
- Alembic `0004` upgrade → downgrade → upgrade passed on SQLite; a separate populated migration check confirmed historical daily usage backfill. PostgreSQL SQL is implemented through its dialect-specific atomic upsert, but no live PostgreSQL service was available for integration testing.
- No live AI provider was configured, so real provider interoperability, response quality, and live token reporting remain unverified. Provider/model integration remains OpenAI-compatible only. Subscription/payment functionality and commercial Swiss Ephemeris licensing clearance remain out of scope/unresolved; astrology calculation flags remain disabled.

## Deterministic intelligence foundation — Milestone 1 (2026-11-03)
- Added provider-independent typed contracts for intent, question classification, saved chart facts, conversation turns, interpretation rules, matched rules, response sections/statuses and version metadata under `backend/app/services/ai/contracts.py`.
- Added versioned JSON knowledge fixtures for Vedic, Western, English and Tamil. All entries are explicitly `test_only` and marked as test text, not astrology claims. The schema requires rule and knowledge-base semantic versions, explicit conditions, supported language, traditional interpretation classification, source attribution, reference and editorial status.
- Added `knowledge_loader.py` with JSON and safe YAML loading, strict Pydantic validation, duplicate ID detection across a knowledge directory, version consistency, provenance checks, and exact matching that never matches a rule if any required chart fact is absent. No interpretation rules are active content.
- Added `tests/test_ai_knowledge.py` for valid JSON/YAML, invalid documents/fields/languages/versions/provenance, duplicate identifiers, missing chart facts, test-only fixtures, and typed response statuses.
- Verification: full backend pytest **203 passed, 14 skipped, 0 failed**; 40 existing dependency deprecation warnings. No database migration was needed. No frontend, chart engine, authentication, or persistence changes were made.
- Next milestone: implement deterministic intent/question classification and fact extraction from the existing owner-scoped saved-chart context, then add matching/response assembly without introducing interpretation claims until bilingual content has editorial sources and review.

## Deterministic intelligence — Milestone 2 (2026-11-03)
- Added deterministic English/Tamil message-language detection, greeting/chart-question/clarification/unsupported/missing-chart intents, and chart topic, system, division, and entity classification. Ambiguous or conflicting systems/divisions are returned explicitly; selected system/division resolves ambiguity only when the caller says the selected chart is available.
- Added a typed chart-fact adapter for persisted Vedic D1/D9 and Western natal context, including planets, signs, houses, retrograde, angles, Nakshatra/Pada, Vimshottari periods, Western aspects, chart/profile IDs, division, engine version, ephemeris version, calculation timestamp and per-fact provenance. Invalid values are omitted and listed as missing. Birth details and calculation input snapshots are not copied into facts.
- Added `load_session_chart_facts`, which reuses `load_session_context` and its owner/profile/chart/system/completed-run query filters. Foreign-owner context resolves to unavailable facts; no calculation is performed.
- Verification: focused classifier/fact/knowledge tests **52 passed**; full backend pytest **238 passed, 14 skipped, 0 failed**; Ruff passed; `git diff --check` passed. No migration required. Existing provider routes and frontend are unchanged.
- Next: Milestone 3 should define deterministic rule-match inputs and provenance-aware fact/rule references, then begin reviewed bilingual interpretation content separately. Do not generate or activate substantive astrology rules until editorial/source review is complete.

## Deterministic intelligence — Milestone 3 (2026-11-03)
- Added `rule_matcher.py` as a separate deterministic matcher. It requires a chart-question classification with resolved system/topic, checks the selected chart's system/division, matches exact equality conditions against validated typed facts, and uses stable rule-ID/fact-reference ordering.
- Matching supports only fields emitted by the typed chart-fact adapter: planetary sign/longitude/house/retrograde, D9 sign/index/longitude, Nakshatra/name/lord/Pada/fraction, ascendant/Midheaven, house cusps, Vimshottari metadata and Dasha/Antardasha periods, and Western aspects/orb/motion. Loader validation rejects unknown fields, invalid condition types, system-incompatible facts, and invalid divisions.
- Every match retains rule/version/knowledge version, localization, system/division, chart/profile IDs, editorial provenance, and exact chart/profile-scoped fact references. The matcher rejects mixed chart/profile/system/division facts, duplicate or invalid fact keys, and source provenance that does not point back to the saved chart.
- Production matching permits only `approved` rules with adequate non-placeholder source attribution. Draft/reviewed/test-only rules are skipped by default. Test-only rules can be enabled only through an explicit matcher test option; existing knowledge fixtures remain test-only and contain no astrology claims. Rules with the same explicitly authored `conflict_group` are returned with a conflict record instead of silently merged.
- Verification: focused Milestone 1/3 loader and matcher tests **50 passed**; full backend pytest **271 passed, 14 skipped, 0 failed**; Ruff passed; `git diff --check` passed. No migration or frontend/auth/calculation-engine changes.
- Limitation: no substantive rule content is approved, so production matching currently yields no interpretations. Conflict detection requires authors to assign a shared conflict group; the matcher does not infer semantic contradictions from free text.
- Next milestone: implement deterministic response assembly over calculated facts, matched reviewed rules, and explicit limitations. Keep it unavailable until sourced bilingual rules pass editorial review; preserve fact/rule citations in every output section.

## Deterministic intelligence — Milestone 4: response assembly (2026-11-03)
- Added a provider-independent `response_composer.py` that turns deterministic question classifications, validated saved-chart facts and matcher output into typed `answered`, `missing_chart`, `unsupported` or `needs_clarification` responses. It is not connected to chat routes; frontend, authentication, persistence and calculation engines are unchanged.
- Responses include a short localized answer, separated fact/interpretation/limitation sections, language, selected system/division, intelligence and knowledge-base versions, stable chart fact IDs, and rule source, attribution, reference, editorial status and chart/profile provenance. `MatchedFactReference` now has a stable `fact_id`; the matcher derives it from saved chart identity and fact field.
- English and Tamil templates cover greeting, unsupported/clarification/missing-chart states, fact summaries, unavailable fact/rule messages and safety wording. Tamil labels cover common planet, sign and Nakshatra terms. Reviewed interpretation text is copied only in its authored language; the composer does not translate or generate interpretive content.
- The composer fails closed on invalid chart facts, cross-chart/profile references, unapproved/test-only rules, inadequate provenance, unsupported system/division facts, unsafe guarantee/advice language, inconsistent conflict metadata, private-detail markers and response-size limits. Conflicting rule groups are withheld together and disclosed as a limitation. Current knowledge files contain no substantive approved rules; test-only fixtures never appear in production composition.
- No database migration was required. Existing response contracts now include an answer, answer source IDs, fact/rule source references and chart division metadata. No route consumes the composer in this milestone.

### Verification
- Added `backend/tests/test_ai_response_composer.py` covering English/Tamil responses, Vedic D1/D9, Nakshatra/Pada, Vimshottari facts, Western aspects, missing/unsupported/clarification states, no approved rules, test-only exclusion, source/fact provenance, conflict withholding, profile isolation, invalid facts, private data, safety wording, bounded output and deterministic output.
- Focused composer/knowledge/matcher tests: **70 passed**.
- Full backend pytest: **291 passed, 14 skipped, 0 failed**. The 14 existing skips require optional Swiss Ephemeris native runtime/data. 40 dependency deprecation warnings remain.
- Ruff on `backend/app/services/ai` and affected AI tests: **passed**. Repository-wide Ruff still reports two unrelated unused imports in `backend/alembic/versions/0001_initial_schema.py` and `backend/app/services/astrology/vedic.py`; neither file was changed.
- `git diff --check`: **passed**.

### Remaining limitations / next milestone
- The composer remains intentionally disconnected from existing AI chat routes. No substantive approved Vedic or Western interpretations exist; chart questions return sourced calculated facts and a localized notice that sourced interpretation is unavailable.
- Next milestone: add an editorially sourced and reviewed bilingual knowledge set (or keep interpretation unavailable), then connect deterministic composition to chat only after route-level ownership, usage, idempotency and SSE tests are in place. Do not restore or invoke an external AI provider.


## Deterministic chat integration — Milestone 5 (2026-11-03)

- Replaced the active chat provider invocation with `DeterministicAstrologyIntelligence`: language detection and intent classification, owner-scoped retrieval of completed saved chart facts, versioned knowledge loading, production-eligible rule matching, and response composition/validation. No chart calculations are run in chat. No external provider, LLM, inference service, key, or network call is used.
- Preserved authenticated conversation CRUD/history, profile/chart ownership checks, daily atomic usage counters, request idempotency, retries, and SSE. The route validates the complete answer before streaming metadata and section deltas, then persists the complete structured response and readable text only after the stream finishes. Client disconnects do not save partial assistant output. Migration `0005_deterministic_ai_responses` adds nullable `chat_messages.response_data`; existing rows remain readable.
- Frontend continues using the existing chat page and SSE delta path, and renders persisted structured answer sections with separate calculated-fact, traditional-interpretation, and limitation styling plus source attribution. English and Tamil UI/engine messages remain supported. Playwright now runs without a mock or provider process and checks the localized missing-chart state.
- There are no approved substantive interpretation rules, so test-only rules are not emitted; the engine returns actual chart facts when present and clearly states that a sourced interpretation is unavailable. General astrology definitions without approved knowledge are declined. The deterministic engine does not resolve conversational references from prior messages.
- Removed provider credentials from `.env.example` and clarified that `provider.py` and its Settings fields/optional HTTP client remain dormant legacy code for existing tests; deterministic chat never reads them. Removed the obsolete history-limit setting. Hardened `.gitignore` for `.env.*`, SQLite files and egg-info. Removed two repository-wide Ruff unused imports. No source files were deleted.

### Verification
- Backend full pytest from `backend/`: **295 passed, 14 skipped, 0 failed** (skips require optional Swiss native runtime/data).
- Frontend full Node test suite: **19 passed, 0 failed**.
- Frontend production build: **passed** after typing the source-provenance response contract.
- Ruff repository check: **passed**.
- `git diff --check`: **passed** before final checkpoint review.
- Playwright: **1 passed, 0 failed** with isolated local API/Vite servers and a temporary SQLite database; the engine runs without provider credentials or a mock provider.
- Alembic on SQLite: **upgrade to head, downgrade to 0004, upgrade to head passed**, including `0005_deterministic_ai_responses`.
- Final `git diff --check`: **passed**.

### Remaining limitations and next milestone
- No production-approved traditional interpretation content exists. The deterministic engine is intentionally limited to greetings, supported classification, factual saved-chart responses, localized missing/unsupported states, and sourced interpretations only if approved rules are later added.
- Provider adapter code and its optional dependency extra remain in the repository but are not part of active chat execution. Remove them in a separate cleanup only after confirming no external consumers depend on that legacy module.
- Next: author and editorially review sourced bilingual rules in small batches, with provenance and safety tests, before enabling any interpretive responses. Keep calculation feature/licensing gates disabled.

## Astrology source library — Milestone 6 (2026-11-03)

- Added typed versioned source registry at `backend/app/services/ai/knowledge/sources/registry.v1.json` with five edition-level records for BPHS, Phaladeepika, Saravali, Ptolemy's Tetrabiblos, and Lilly's Christian Astrology. Records include attribution, historical-period confidence, translator/editor, edition/publication notes, digital catalog/text locations, completeness, rights and reuse assessments, verification notes, topics, and citation formats.
- Added `source_registry.py` with required bibliographic-field validation, semantic registry versions, unique source IDs, access/completeness disclosure, source/edition relationship validation, system alignment, and excerpt-use gating. BPHS edition, volume translator/date, textual history and chapter numbering are explicitly unresolved; the registry does not assign a definitive ancient date.
- Extended rule contracts with source/edition IDs and registry version, exact passage locators, optional excerpt/citation note, editorial explanation, English/Tamil localizations, separate reviewer roles, review timestamp, and translation-review state. Existing v1 test-only fixtures continue to load unchanged. Approved rules now require bilingual content, an exact locator, review metadata, registered edition and matching source tradition; the matcher and response composer enforce the same gate.
- Added a research-only topic catalogue for all requested Vedic and Western topics and validation ensuring unique topic IDs, registered candidate sources, and no promotion to approved rules.
- Added `docs/KNOWLEDGE_RESEARCH_WORKFLOW.md`, documented citation/review steps and separate source text/commentary handling, and configured setuptools package data for the versioned JSON knowledge files.
- No book text or substantive astrology interpretations were copied into the repository. No database migration, calculation-engine, auth, or chat-route changes were made.

### Source and rights findings
- Delhi University Library catalogs a Sanskrit Ranjan BPHS record dated 1984; WorldCat records other Ranjan editions/printings, and the sources disagree on dates and volume-level translators. The registry links catalogs rather than circulating scans, and leaves edition-specific passage references unverified.
- The accessible IGNCA Phaladeepika scan identifies V. Subrahmanya Sastri's second revised/enlarged English edition (1950), prints a copyright notice, and describes chapters I–XXVIII. Its preface's attribution/date remarks are recorded as the translator's own estimate, not established history. Reuse is not cleared.
- WorldCat identifies R. Santhanam's 1983 first-edition English Saravali record; Wellcome catalog metadata corroborates the translation/commentary attribution. A licensed full text was not verified. Reuse is not cleared.
- LacusCurtius identifies the complete Robbins Loeb 1940 Tetrabiblos translation and asserts U.S. public-domain status due to nonrenewal; this assertion is not legal advice and remains unverified. Publisher/platform and jurisdiction terms require review.
- Wellcome identifies Lilly's 1647 three-book original and applies a Public Domain Mark, while noting the digitized copy lacks its last leaf. A later Houlding retyped edition is explicitly copyrighted by its host and excluded as a reusable text. Registry conservatively permits no excerpts pending legal review.
- All source registry records flag commercial reuse as not cleared or requiring legal review. No commercial copyright conclusion is claimed.

### Verification
- New focused source/knowledge/matcher/composer tests: **84 passed**.
- Full backend pytest: **309 passed, 14 skipped, 0 failed** (optional Swiss native/runtime-data skips); frontend tests: **19 passed, 0 failed**; frontend production build: **passed**; Ruff and `git diff --check`: **passed**.
- Backend wheel package-data inspection was attempted but could not run: the isolated backend environment has no `setuptools`, and the build backend import failed before wheel creation. JSON package-data declarations are in `backend/pyproject.toml`; verify wheel contents once setuptools is available from an approved registry/cache.
- No migration required. Current knowledge files remain test-only; production interpretation stays unavailable until a source passage is acquired/verified, rights are reviewed, and bilingual editorial review is recorded.

## Release hardening continuation (2026-11-03)

### Implemented
- Added explicit interpretation-rule lifecycle states (`research_candidate`, `source_verified`, `editorial_review_pending`, `translation_review_pending`, `approved`, `rejected`, `retired`) with a monotonic reviewer/timestamp/note trail. Transitions require explicit caller-supplied reviewers; approval requires source/edition linkage, locator, source-verification record, bilingual text, separate editorial and translation reviewers, and a separate approver. Loader, matcher, and source provenance validation reject incomplete/legacy approval metadata. Retired rules remain traceable but cannot match. Existing test-only JSON fixtures remain loadable.
- Reviewer independence checks normalize case and repeated whitespace so identity variants cannot satisfy the separate-reviewer requirement.
- Expanded the versioned research backlog to **81 topic candidates** in `catalogue.v2.json`, covering the requested nine Vedic grahas, twelve rāśis, twelve bhāvas, lagna, nakṣatra/pāda, dignity, Vimśottarī, yogas, D1/D9, relationships, seven traditional Western planets, twelve signs, twelve houses, rulership/dignity, five major aspects, retrograde, planetary condition, combinations and natal methodology. The earlier v1 catalogue is retained. These are research topics only: **0 source-verified rule records and 0 approved substantive rules**.
- Strengthened rule matching tests for conjunctive multi-factor requirements, required-fact absence, explicit Vedic division scope, and rejection of cross-system/unsupported outer-planet source claims. Existing matcher already applies all listed conditions as exact conjunctive matches and retains each supporting chart fact reference.
- Enabled narrow English/Tamil chat follow-ups from the latest user-authored question only. Prior assistant output is not used as chart fact context; current explicit entities take precedence. The API passes only prior turns from the same authenticated conversation and excludes the current user message from that history. Profile-name lookup now also checks the conversation owner's profile ID.
- Improved chat presentation so calculated facts show their saved-chart fact references separately from traditional interpretation. Source sections show the registered edition and chapter/verse/page/section locator with language-specific labels when references exist. Updated public/dashboard copy to avoid saying substantive traditional interpretations are currently available.
- Removed the dormant OpenAI-compatible provider adapter, model prompt builder, provider-only tests, API-key Settings fields, and optional provider dependency. The chat integration test now blocks socket connections while exercising a deterministic API response.
- Added production configuration checks (non-default >=32-character secret, PostgreSQL, explicit HTTPS origins), response security headers, and a DB-backed `/ready` endpoint while retaining `/health` as liveness. Added an unprivileged backend container, runtime health check, Docker exclusions for secrets/databases/ephemeris files/native libraries, and a local CI workflow for full tests/build/E2E/migration cycling. Removed empty Razorpay placeholders from the environment example; no billing or subscription code was added.
- Updated README, architecture, testing, security, and deployment documentation. No SQL model or schema changed; no migration is required.

### Verification
- Backend full pytest from `backend/`: **328 passed, 14 skipped, 0 failed**. Skips are the existing optional Swiss native/data-dependent tests. 41 warnings remain: 1 Starlette/AnyIO deprecation and 40 FastAPI `asyncio.iscoroutinefunction` deprecations.
- Repository-wide Ruff (`backend/.venv/bin/ruff check .`): **passed**.
- Frontend Node test suite: **20 passed, 0 failed**. Production TypeScript/Vite build: **passed** (1,605 modules transformed).
- Playwright: **1 passed, 0 failed**. Journey covers registration, profile creation, calculation-gate messages, persisted chart history, deterministic chat/missing-chart response, logout/login persistence, Tamil UI, conversation removal, and second-account isolation for the first account's conversation/profile.
- Alembic SQLite upgrade to head → downgrade to base → upgrade to head: **passed** against a fresh temporary database. No PostgreSQL service was available for a live PostgreSQL migration run.
- `git diff --check`: **passed**. `pip check`: **passed**. `npm audit --offline`: **0 known vulnerabilities in the locally available advisory metadata**; offline metadata freshness is not established. `pip-audit`/`safety` are not installed, and PyPI DNS resolution failed during a permitted attempt to install the declared existing setuptools build backend. Wheel creation/resource inspection is therefore **still unverified**; no project dependency versions were changed.

### Release assessment and remaining blockers
- AstroAI is **not production-ready**. The workflows that work locally include authentication, owner-scoped profile CRUD, saved chart history, deterministic bilingual chat over existing saved facts, quota/idempotency, versioned source/rule validation, and the verified unavailable-calculation response. A Playwright journey verified these application paths against local services and an isolated temporary database.
- Chart calculation endpoints remain feature/license gated; the 14 skipped native/data-dependent cases mean this run does not re-verify Swiss Ephemeris runtime accuracy. Commercial licensing for both Swiss Ephemeris and `swisseph-ffi` needs professional review. No public service should enable these flags yet.
- No sourced Vedic/Western interpretation rules are approved. The chat can report chart facts when a completed chart exists, but sourced interpretations and general astrology definitions remain unavailable. The research catalogue is not evidence that its topics are source-verified.
- Remaining release work includes acquiring/validating exact editions and passage locators, legal review of source/translation/digital rights, actual independent bilingual editorial review, wheel/package verification after setuptools is available, PostgreSQL staging migration/restore exercise, external gateway rate limiting for auth/general requests, refresh/recovery/email-verification flows, production operations/monitoring decisions, and launch-owner review. Horoscope, Panchang, compatibility, admin workflows and reports remain unavailable/placeholder modules from earlier status; paid features remain explicitly out of scope.
- No production deployment was performed. A local checkpoint commit is created after reviewing the complete staged diff; no push is performed.

## Final product completion pass (2026-11-03)

- Authentication now rejects deactivated accounts both during OAuth form login and on requests using previously issued access tokens. A disabled user's token stops working without requiring a JWT revocation list.
- Public chart calculation failures now return a generic unavailable response instead of exposing native-library diagnostics or server filesystem paths. The calculation and license flags remain false.
- Dashboard date display now uses the user's current local date and language. Removed the inert notification and guide controls. Horoscope, Panchang, and compatibility destinations now state their specific missing approval/runtime requirements in English and Tamil and explicitly avoid generating unsupported predictions or scores.
- Added Playwright coverage for the three unavailable product destinations. Verified the real Swiss Ephemeris native library and configured external ephemeris data from the isolated Python 3.14 ARM64 environment without copying either into the repository.
- Official licensing references reviewed: Astrodienst's dual-license and service activation guidance, its Professional License contract, and the wrapper's own AGPL-3.0-or-later release metadata. The wrapper and Swiss Ephemeris licenses are separate review items; no legal conclusion or commercial clearance is claimed.

### Verification
- Full backend suite with the actual isolated Swiss Ephemeris ARM64 wrapper and external `.se1` files: **345 passed, 0 skipped, 0 failed**. Native version: **2.10.03**. Sun/Moon, Lahiri, sidereal/tropical differences, houses/Ascendant, D1/D9 derivations, reference positions and fallback rejection all ran against the native library and files. 41 dependency deprecation warnings remain (Starlette/AnyIO and FastAPI).
- Frontend suite: **21 passed, 0 failed**. Production TypeScript/Vite build: **passed** (1,605 modules).
- Playwright: **1 passed, 0 failed**, including registration, profiles, disabled calculation states, horoscope/Panchang/compatibility unavailable explanations, chart history, deterministic chat, logout/re-login, localization and cross-account privacy. The existing local Vite server occupied port 5173, so E2E ran on isolated loopback port 5174.
- Repository Ruff: **passed**. SQLite Alembic upgrade to head → downgrade to base → upgrade to head: **passed**. `pip check`: **passed**. `npm audit --offline`: 0 findings in cached advisory metadata; freshness is unknown. `git diff --check`: **passed**.
- Packaging remains unverified: wheel build cannot import the declared `setuptools.build_meta` because setuptools is absent from the local virtual environment. PyPI DNS failed previously; dependencies were not changed. Docker is not installed here. `pip-audit` and `safety` are unavailable, and no live PostgreSQL staging service exists.

### Current release assessment
- The established Vedic D1/D9, Nakshatra/Pada, Savana Vimshottari, Western natal, houses, major aspects, saved-chart, and deterministic chat paths remain implemented; transits, yogas/doshas, dignity, synastry, compatibility, location-aware Panchang, horoscope content, bilingual PDF reports, and admin knowledge management are not complete production features.
- Knowledge catalogue: **81 research topics**; **0 substantive source-verified rules**; **0 genuinely approved bilingual rules**. No rule is promoted without actual edition/passage verification and separate human editorial/translation review.
- This execution does not enable public calculations or deploy infrastructure. A complete production or staging release is still blocked by legal licensing review, approved source content and human reviewers, operational and security decisions, and PostgreSQL/package deployment verification.
- Final status: **NOT READY FOR STAGING**. This is an engineering readiness assessment, not a legal or security certification.
