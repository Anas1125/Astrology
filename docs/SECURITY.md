# Security

Passwords use Argon2id via pwdlib; API access tokens are short-lived HS256 JWTs. SQLAlchemy queries are parameterized and profile reads are scoped to the authenticated owner. Before production: configure a strong secret, HTTPS, restricted CORS, refresh token rotation/revocation, email verification/reset, rate limiting, CSRF strategy, sensitive-field encryption, audit logs, account export/deletion and formal secret management. Never commit `.env`.
