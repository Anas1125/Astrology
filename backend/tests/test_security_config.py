import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import app


@pytest.mark.parametrize(
    "overrides",
    [
        {"secret_key": "development-only-change-me"},
        {"secret_key": "short"},
        {"database_url": "sqlite:///prod.db"},
        {"cors_origins": "*"},
        {"cors_origins": "http://example.com"},
    ],
)
def test_production_settings_reject_insecure_values(overrides):
    values = {
        "app_env": "production",
        "secret_key": "a-secure-example-secret-key-value-123456",
        "database_url": "postgresql+psycopg://astroai:secret@db/astroai",
        "cors_origins": "https://astroai.example",
    }
    values.update(overrides)
    with pytest.raises(ValueError):
        Settings(**values)


def test_production_settings_accept_explicit_secure_baseline():
    configured = Settings(
        app_env="production",
        secret_key="a-secure-example-secret-key-value-123456",
        database_url="postgresql+psycopg://astroai:secret@db/astroai",
        cors_origins="https://astroai.example,https://www.astroai.example",
    )
    assert configured.cors_origin_list == ["https://astroai.example", "https://www.astroai.example"]


def test_health_and_readiness_endpoints_and_security_headers():
    response = TestClient(app).get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    ready = TestClient(app).get("/ready")
    assert ready.status_code == 200
    assert ready.json() == {"status": "ready"}
