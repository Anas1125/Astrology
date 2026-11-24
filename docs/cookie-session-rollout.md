# Staged cookie authentication rollout

The default build remains bearer authentication. No migrations are required. Cookie mode uses the existing JWT auth_version column for **account-wide** logout revocation (all devices and legacy tokens). Password reset also invalidates sessions. Newly issued cookie JWTs are transport-bound: they cannot be used as bearer tokens. Browser JavaScript receives only account metadata, never the cookie JWT.

## 1. Backend settings (Vercel production)

- APP_ENV=production
- SESSION_PROXY_SECRET: generate a new independent random secret (python -c 'import secrets; print(secrets.token_hex(32))'). Never commit it or use a VITE_ prefix.
- COOKIE_AUTH_ORIGINS=https://astrology-b2l.pages.dev
- DISABLE_BEARER_AUTH=false

Retain existing SECRET_KEY and CORS_ORIGINS. Deploy and verify backend health. Do not change the Swiss Ephemeris calculation gates.

## 2. Cloudflare Pages production runtime settings

Root directory frontend, build output dist. Add these runtime variables to the Pages project:
- ASTRO_API_ORIGIN=https://astrology-phi-five.vercel.app
- ASTRO_FRONTEND_ORIGIN=https://astrology-b2l.pages.dev
- SESSION_PROXY_SECRET: exactly the same value as Vercel, stored as a secret.

Keep VITE_COOKIE_AUTH unset/false initially. Deploy the latest main commit, not an old retry. Verify that GET https://astrology-b2l.pages.dev/api/v1/auth/me returns HTTP 401 JSON (not SPA HTML or a 503).

## 3. Enable browser cookie mode

Set VITE_COOKIE_AUTH=true in Cloudflare production build variables; retain existing VITE_API_BASE_URL, VITE_SITE_URL and VITE_CSP_ENFORCE. Deploy the latest main commit. Log in again; old browser storage is cleared in cookie mode.

Verify in a private browser window: signup, login, reload, profiles, charts, chat SSE, Vastu multipart upload, admin edits, password reset, logout. Network requests should use the frontend /api/v1 URL and carry no Authorization bearer header. Login JSON contains account metadata only. The __Host-astroai-session cookie must be Secure, HttpOnly, SameSite=Lax, Path=/, and have no Domain attribute. Normal cookies are browser-session cookies; remember-me persists up to seven days, administrator tokens expire after one hour and are session-only. Confirm localStorage and sessionStorage contain no astroai_access_token. Confirm a request after logout is unauthorized and another signed-in device must log in again.

## 4. Retire bearer only after all tests pass

Set DISABLE_BEARER_AUTH=true on Vercel and deploy. This disables legacy login/register and rejects legacy access tokens on protected routes. API documentation's OAuth bearer login will no longer work. Do not activate if a legitimate API client needs bearer authentication. Verify direct bearer requests are rejected and cookie login works.

Rollback: first re-enable bearer on Vercel, then rebuild Cloudflare with VITE_COOKIE_AUTH=false. Users will need to sign in again. Cookie-based logout is account-wide; in-flight requests already authorized may still complete. HttpOnly reduces token theft via JavaScript but does not prevent all XSS or session abuse.
