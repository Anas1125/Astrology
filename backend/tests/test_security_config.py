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
        "password_reset_frontend_url": "https://astroai.example",
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
        password_reset_frontend_url="https://astroai.example",
    )
    assert configured.cors_origin_list == ["https://astroai.example", "https://www.astroai.example"]


def test_local_agpl_calculation_switch_is_development_only_and_separate_from_public_flags():
    local = Settings(
        app_env="development",
        astrology_calculations_enabled=False,
        swisseph_license_confirmed=False,
        astrology_local_agpl_development_enabled=True,
    )
    assert local.astrology_calculations_authorized
    assert local.astrology_calculations_enabled is False
    assert local.swisseph_license_confirmed is False
    with pytest.raises(ValueError, match="permitted only in development"):
        Settings(app_env="production", astrology_local_agpl_development_enabled=True)


def test_local_calculation_endpoints_reject_non_loopback_peers(monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "app_env", "development")
    monkeypatch.setattr(settings, "astrology_local_agpl_development_enabled", True)
    remote = TestClient(app, client=("198.51.100.24", 53211))
    response = remote.post("/api/v1/panchang/daily", json={})
    assert response.status_code == 403
    loopback = TestClient(app, client=("127.0.0.1", 53211))
    protected = loopback.post("/api/v1/panchang/daily", json={})
    assert protected.status_code == 401


@pytest.mark.parametrize("overrides", [
    {"password_reset_dev_token_file": "/tmp/reset.txt"},
    {"password_reset_smtp_host": "smtp.example", "password_reset_smtp_sender": "no-reply@example.test", "password_reset_smtp_starttls": False},
    {"password_reset_frontend_url": "http://astroai.example"},
])
def test_production_password_reset_configuration_rejects_dev_paths_and_insecure_origins(overrides):
    values = {
        "app_env": "production",
        "secret_key": "a-secure-example-secret-key-value-123456",
        "database_url": "postgresql+psycopg://astroai:secret@db/astroai",
        "cors_origins": "https://astroai.example",
        "password_reset_frontend_url": "https://astroai.example",
    }
    values.update(overrides)
    with pytest.raises(ValueError):
        Settings(**values)


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
