"""Trust only the configured same-origin edge, never browser-supplied forwarding headers."""
import hmac
from fastapi import HTTPException, Request
from app.core.config import settings

COOKIE_NAME = "__Host-astroai-session"


def trusted_session_proxy(request: Request) -> bool:
    supplied = request.headers.get("x-astro-proxy-secret", "")
    origin = request.headers.get("x-astro-proxy-origin", "")
    return bool(
        settings.session_proxy_secret
        and origin in settings.cookie_origin_list
        and hmac.compare_digest(supplied.encode(), settings.session_proxy_secret.encode())
    )


def require_session_proxy(request: Request) -> None:
    if not trusted_session_proxy(request):
        raise HTTPException(403, "Session proxy required")
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        if (request.headers.get("origin") != request.headers.get("x-astro-proxy-origin")
                or request.headers.get("x-astro-csrf") != "1"):
            raise HTTPException(403, "Cross-origin session request denied")
