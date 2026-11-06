import ipaddress

from fastapi import FastAPI
from fastapi import Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.core.config import settings
from app.db.base import get_db
from app.models import entities  # noqa: F401
from app.api.routes import router
from app.api.horoscope_admin import router as horoscope_admin_router
from app.api.ai_routes import router as ai_router

from app.api.vastu_routes import router as vastu_router
app = FastAPI(title="AstroAI API", version="0.1.0", description="Multilingual astrology SaaS API")
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origin_list, allow_credentials=True, allow_methods=["GET", "POST", "PATCH", "DELETE"], allow_headers=["Authorization", "Content-Type", "Idempotency-Key"])


@app.middleware("http")
async def local_calculation_loopback_only(request: Request, call_next):
    calculation_path = request.url.path.startswith("/api/v1/astrology/charts/") or request.url.path == "/api/v1/panchang/daily"
    if settings.astrology_local_agpl_development_enabled and calculation_path:
        host = request.client.host if request.client else ""
        try:
            is_loopback = ipaddress.ip_address(host).is_loopback
        except ValueError:
            is_loopback = False
        if not is_loopback:
            return JSONResponse(status_code=403, content={"detail": "Local development calculations accept loopback connections only."})
    return await call_next(request)


@app.middleware("http")
async def security_headers(request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    if settings.app_env.casefold() in {"production", "prod"}:
        response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    return response


app.include_router(router, prefix="/api/v1")
app.include_router(horoscope_admin_router, prefix="/api/v1")
app.include_router(ai_router, prefix="/api/v1")
app.include_router(vastu_router, prefix="/api/v1")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/ready")
def readiness(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Database unavailable") from exc
    return {"status": "ready"}
