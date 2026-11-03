from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.models import entities  # noqa: F401
from app.api.routes import router
from app.api.ai_routes import router as ai_router

app = FastAPI(title="AstroAI API", version="0.1.0", description="Multilingual astrology SaaS API")
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origin_list, allow_credentials=True, allow_methods=["GET", "POST", "PATCH", "DELETE"], allow_headers=["Authorization", "Content-Type", "Idempotency-Key"])
app.include_router(router, prefix="/api/v1")
app.include_router(ai_router, prefix="/api/v1")


@app.get("/health")
def health():
    return {"status": "ok"}
