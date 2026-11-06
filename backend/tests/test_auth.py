from fastapi.testclient import TestClient
from datetime import date
from datetime import datetime, timedelta, timezone
from uuid import UUID
from urllib.parse import parse_qs, urlparse
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import pytest

from app.db.base import Base, get_db
from app.main import app
from app.models.entities import BirthChart, ChartCalculationRun, CompatibilityReport, HoroscopeContent, PasswordResetToken, SecurityAuditEvent, User
from app.core.security import hash_password
from app.core.config import settings
from app.services.astrology.sweph import ENGINE_VERSION


engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
Base.metadata.create_all(bind=engine)


def override_db():
    with TestSession() as session:
        yield session


app.dependency_overrides[get_db] = override_db
client = TestClient(app)


def setup_function():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with TestSession() as session:
        session.add(User(email="member@example.com", password_hash=hash_password("correct-password")))
        session.commit()


def test_login_accepts_oauth2_form_and_uses_email_as_username():
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "member@example.com", "password": "correct-password"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["token_type"] == "bearer"
    assert payload["access_token"]


def test_login_rejects_incorrect_password():
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "member@example.com", "password": "incorrect-password"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Email or password is incorrect"


def test_login_rejects_unknown_email():
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "unknown@example.com", "password": "correct-password"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Email or password is incorrect"


def test_inactive_user_cannot_login():
    with TestSession() as session:
        session.add(User(
            email="inactive@example.com",
            password_hash=hash_password("correct-password"),
            is_active=False,
        ))
        session.commit()
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "inactive@example.com", "password": "correct-password"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Email or password is incorrect"


def test_deactivated_user_access_token_is_rejected():
    token = login_token()
    with TestSession() as session:
        user = session.scalar(select(User).where(User.email == "member@example.com"))
        user.is_active = False
        session.commit()
    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


def test_openapi_oauth_authorize_uses_login_endpoint():
    schema = client.get("/openapi.json").json()
    scheme = schema["components"]["securitySchemes"]["OAuth2PasswordBearer"]["flows"]["password"]
    assert scheme["tokenUrl"] == "/api/v1/auth/login"
    request_body = schema["paths"]["/api/v1/auth/login"]["post"]["requestBody"]
    assert "application/x-www-form-urlencoded" in request_body["content"]


def test_cors_allows_ai_idempotency_header_preflight():
    response = client.options(
        "/api/v1/ai/conversations/test/messages/stream",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "authorization,content-type,idempotency-key",
        },
    )
    assert response.status_code == 200
    assert "idempotency-key" in response.headers["access-control-allow-headers"].lower()


def test_registration_still_returns_access_token():
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "new@example.com", "password": "correct-password-long"},
    )
    assert response.status_code == 201
    assert response.json()["token_type"] == "bearer"
    assert response.json()["access_token"]


def test_authenticated_account_endpoint_returns_current_user():
    login_response = client.post(
        "/api/v1/auth/login",
        data={"username": "member@example.com", "password": "correct-password"},
    )
    token = login_response.json()["access_token"]
    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["email"] == "member@example.com"
    assert response.json()["role"] == "USER"


def test_authenticated_account_endpoint_rejects_missing_token():
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


def create_profile(client_instance=client, token=None, overrides=None):
    fields = {
        "display_name": "Personal chart",
        "relationship": "self",
        "birth_date": "1990-05-14",
        "birth_time": "08:30:00",
        "time_accuracy": "exact",
        "birthplace": "Chennai",
        "country": "India",
        "latitude": 13.0827,
        "longitude": 80.2707,
        "timezone": "Asia/Kolkata",
    }
    fields.update(overrides or {})
    return client_instance.post("/api/v1/profiles", json=fields, headers={"Authorization": f"Bearer {token}"})


def login_token(email="member@example.com", password="correct-password"):
    response = client.post("/api/v1/auth/login", data={"username": email, "password": password})
    return response.json()["access_token"]


def test_profile_create_and_list_are_owner_scoped():
    token = login_token()
    created = create_profile(token=token)
    assert created.status_code == 201
    assert created.json()["timezone"] == "Asia/Kolkata"
    listed = client.get("/api/v1/profiles", headers={"Authorization": f"Bearer {token}"})
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()] == [created.json()["id"]]


def test_vedic_western_and_panchang_routes_report_disabled_calculation_gate(monkeypatch):
    token = login_token()
    profile = create_profile(token=token).json()
    monkeypatch.setattr(settings, "astrology_calculations_enabled", False)
    monkeypatch.setattr(settings, "swisseph_license_confirmed", False)
    auth = {"Authorization": f"Bearer {token}"}
    vedic = client.post("/api/v1/astrology/charts/vedic", json={"profile_id": profile["id"]}, headers=auth)
    western = client.post("/api/v1/astrology/charts/western", json={"profile_id": profile["id"]}, headers=auth)
    panchang = client.post("/api/v1/panchang/daily", json={
        "local_date": "2026-03-22", "location_name": "Chennai", "latitude": 13.0827,
        "longitude": 80.2707, "timezone": "Asia/Kolkata",
    }, headers=auth)
    for response in (vedic, western, panchang):
        assert response.status_code == 503
        assert "disabled intentionally" in response.json()["detail"]
        assert "No calculation was performed and no chart was saved" in response.json()["detail"]


def test_missing_ephemeris_runtime_has_distinct_safe_reason(monkeypatch):
    from app.services.astrology import VedicAstrologyEngine
    from app.services.astrology.base import EngineUnavailable

    monkeypatch.setattr(settings, "astrology_calculations_enabled", True)
    monkeypatch.setattr(settings, "swisseph_license_confirmed", True)
    monkeypatch.setattr(settings, "swisseph_ephe_path", None)
    with pytest.raises(EngineUnavailable) as error:
        VedicAstrologyEngine().get_provider()
    assert error.value.reason_code == "ephemeris_data_unavailable"


def test_horoscope_distinguishes_empty_catalogue_and_requires_owned_chart():
    token = login_token()
    profile = create_profile(token=token).json()
    headers = {"Authorization": f"Bearer {token}"}
    general = client.post("/api/v1/horoscope/daily", json={
        "mode": "general", "system": "vedic", "local_date": "2026-03-22", "language": "en", "sign": "Mesha",
    }, headers=headers)
    assert general.status_code == 200
    assert general.json()["status"] == "unavailable"
    assert general.json()["reason"] == "catalogue_empty"
    assert general.json()["content"] is None
    assert general.json()["source_references"] == []
    assert "No prediction" in general.json()["message"]

    personal = client.post("/api/v1/horoscope/daily", json={
        "mode": "personalized", "system": "vedic", "local_date": "2026-03-22", "language": "ta", "profile_id": profile["id"],
    }, headers=headers)
    assert personal.status_code == 200
    assert personal.json()["reason"] == "completed_chart_required"
    assert personal.json()["content"] is None
    assert "கணிப்போ" in personal.json()["message"]


def test_horoscope_period_and_topic_are_explicit_but_do_not_generate_unreviewed_content():
    token = login_token()
    response = client.post("/api/v1/horoscope/daily", json={
        "mode": "general", "system": "western", "local_date": "2026-03-22",
        "period": "monthly", "category": "career", "language": "en", "sign": "Aries",
    }, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()
    assert data["period"] == "monthly"
    assert data["category"] == "career"
    assert data["content"] is None
    assert data["source_references"] == []
    assert data["reason"] == "catalogue_empty"


def test_horoscope_rejects_a_chart_not_owned_by_the_selected_profile():
    owner_token = login_token()
    foreign_token = client.post("/api/v1/auth/register", json={
        "email": "chart-owner@example.com", "password": "correct-password-long",
    }).json()["access_token"]
    own_profile = create_profile(token=owner_token).json()
    foreign_profile = create_profile(token=foreign_token).json()
    foreign_chart = client.post("/api/v1/astrology/charts", json={
        "profile_id": foreign_profile["id"], "system": "vedic", "division": "D1",
    }, headers={"Authorization": f"Bearer {foreign_token}"}).json()
    response = client.post("/api/v1/horoscope/daily", json={
        "mode": "personalized", "system": "vedic", "local_date": "2026-03-22",
        "profile_id": own_profile["id"], "chart_id": foreign_chart["id"],
    }, headers={"Authorization": f"Bearer {owner_token}"})
    assert response.status_code == 404
    assert response.json()["detail"] == "Chart not found"


def test_horoscope_and_compatibility_reject_foreign_profile_ids():
    token = login_token()
    own = create_profile(token=token).json()
    foreign_register = client.post("/api/v1/auth/register", json={
        "email": "other-owner@example.com", "password": "correct-password-long",
    })
    foreign_token = foreign_register.json()["access_token"]
    foreign = create_profile(token=foreign_token, overrides={"display_name": "Private profile"}).json()
    headers = {"Authorization": f"Bearer {token}"}

    personal = client.post("/api/v1/horoscope/daily", json={
        "mode": "personalized", "system": "western", "local_date": "2026-03-22", "profile_id": foreign["id"],
    }, headers=headers)
    compatibility = client.post("/api/v1/compatibility/check", json={
        "profile_a_id": own["id"], "profile_b_id": foreign["id"], "system": "vedic",
    }, headers=headers)
    assert personal.status_code == 404
    assert compatibility.status_code == 404
    assert personal.json()["detail"] == "Profile not found"
    assert compatibility.json()["detail"] == "One or both profiles not found"


def test_horoscope_matches_the_exact_reviewed_bilingual_scope():
    from datetime import datetime
    token = login_token()
    source_refs = [{"source_id": "editorial-fixture", "citation": "test-only source fixture"}]
    with TestSession() as session:
        for language, text in (("en", "Test-only approved English fixture."), ("ta", "சோதனைக்கான தமிழ் உள்ளடக்கம்.")):
            session.add(HoroscopeContent(
                system="western", period="monthly", sign="Aries", category="career", language=language,
                starts_on=date(2026, 3, 1), ends_on=date(2026, 3, 31), content=text,
                approved=True, source_references=source_refs, source_verified=True,
                editorial_reviewed=True, reviewed_by="test-editor", reviewed_at=datetime.now(timezone.utc),
            ))
        session.commit()
    headers = {"Authorization": f"Bearer {token}"}
    wrong_scope = client.post("/api/v1/horoscope/daily", json={
        "mode": "general", "system": "vedic", "local_date": "2026-03-22", "language": "en", "sign": "Mesha",
    }, headers=headers)
    assert wrong_scope.status_code == 200
    assert wrong_scope.json()["reason"] == "no_matching_content"
    assert wrong_scope.json()["content"] is None

    for language in ("en", "ta"):
        response = client.post("/api/v1/horoscope/daily", json={
            "mode": "general", "system": "western", "local_date": "2026-03-22", "period": "monthly",
            "category": "career", "language": language, "sign": "Aries",
        }, headers=headers)
        assert response.status_code == 200
        assert response.json()["status"] == "available"
        assert response.json()["reason"] == "approved_content_available"
        assert response.json()["content"].startswith("Test-only") or "சோதனை" in response.json()["content"]
        assert response.json()["source_references"] == source_refs


def test_horoscope_does_not_serve_unreviewed_or_non_bilingual_content():
    token = login_token()
    with TestSession() as session:
        session.add(HoroscopeContent(
            system="western", period="daily", sign="Leo", category="overview", language="en",
            starts_on=date(2026, 3, 22), ends_on=date(2026, 3, 22), content="Test-only unreviewed fixture.",
            approved=True, source_references=["test fixture, not a real citation"], source_verified=True,
            editorial_reviewed=False, reviewed_by=None, reviewed_at=None,
        ))
        session.commit()
    response = client.post("/api/v1/horoscope/daily", json={
        "mode": "general", "system": "western", "local_date": "2026-03-22", "language": "en", "sign": "Leo",
    }, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["status"] == "unavailable"
    assert response.json()["reason"] == "awaiting_bilingual_editorial_review"
    assert response.json()["content"] is None


def test_horoscope_serves_published_bilingual_content_without_source_metadata():
    token = login_token()
    from datetime import datetime
    with TestSession() as session:
        for language in ("en", "ta"):
            session.add(HoroscopeContent(
                system="vedic", period="daily", sign="Simha", category="overview", language=language,
                starts_on=date(2026, 3, 22), ends_on=date(2026, 3, 22), content="Test-only text.",
                approved=True, source_references=[{"source_id": "fixture", "citation": "  "}],
                source_verified=True, editorial_reviewed=True, reviewed_by="test-editor",
                reviewed_at=datetime.now(timezone.utc),
            ))
        session.commit()
    response = client.post("/api/v1/horoscope/daily", json={
        "mode": "general", "system": "vedic", "local_date": "2026-03-22", "language": "en", "sign": "Simha",
    }, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["status"] == "available"
    assert response.json()["reason"] == "approved_content_available"
    assert response.json()["content"] == "Test-only text."


def test_birthplace_search_requires_auth_and_returns_provider_choices(monkeypatch):
    token = login_token()
    result = [{"id": "place-1", "city": "Nagercoil", "region": "Tamil Nadu", "country": "India",
               "latitude": 8.18, "longitude": 77.41, "timezone": "Asia/Kolkata", "attribution": "Geoapify"}]
    monkeypatch.setattr(settings, "geoapify_api_key", "test-provider-key")
    monkeypatch.setattr("app.api.routes.search_places", lambda *args, **kwargs: result)
    assert client.get("/api/v1/profiles/location-search?q=Nagercoil").status_code == 401
    response = client.get("/api/v1/profiles/location-search?q=Nagercoil&language=ta",
                          headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json() == result


def test_birthplace_search_reports_unconfigured_and_provider_failure(monkeypatch):
    token = login_token()
    headers = {"Authorization": f"Bearer {token}"}
    monkeypatch.setattr(settings, "geoapify_api_key", None)
    not_configured = client.get("/api/v1/profiles/location-search?q=Chennai", headers=headers)
    assert not_configured.status_code == 503
    assert "manually" in not_configured.json()["detail"]
    monkeypatch.setattr(settings, "geoapify_api_key", "test-provider-key")
    monkeypatch.setattr("app.api.routes.search_places", lambda *args, **kwargs: (_ for _ in ()).throw(
        __import__("app.services.geocoding", fromlist=["GeocodingUnavailable"]).GeocodingUnavailable("offline")))
    unavailable = client.get("/api/v1/profiles/location-search?q=Chennai", headers=headers)
    assert unavailable.status_code == 502
    assert "manually" in unavailable.json()["detail"]


def test_compatibility_requires_two_distinct_completed_chart_results():
    token = login_token()
    first = create_profile(token=token).json()
    second = create_profile(token=token, overrides={"display_name": "Second profile"}).json()
    headers = {"Authorization": f"Bearer {token}"}
    missing = client.post("/api/v1/compatibility/check", json={
        "profile_a_id": first["id"], "profile_b_id": second["id"], "system": "western",
    }, headers=headers)
    assert missing.status_code == 200
    assert missing.json()["status"] == "missing_charts"
    assert missing.json()["score"] is None
    assert missing.json()["factors"] == []

    with TestSession() as session:
        for profile_id in (UUID(first["id"]), UUID(second["id"])):
            chart = BirthChart(profile_id=profile_id, system="western", division="natal", status="complete", unavailable_reason="", config={})
            session.add(chart)
            session.flush()
            session.add(ChartCalculationRun(
                chart_id=chart.id, run_number=1, status="complete", config={}, result={"calculation_system": "western", "planets": []},
            ))
        session.commit()
    available_charts = client.post("/api/v1/compatibility/check", json={
        "profile_a_id": first["id"], "profile_b_id": second["id"], "system": "western",
    }, headers=headers)
    assert available_charts.status_code == 200
    assert available_charts.json()["status"] == "unavailable"
    assert available_charts.json()["reason"] == "reviewed_compatibility_method_unavailable"
    assert available_charts.json()["score"] is None
    assert available_charts.json()["completed_chart_count"] == 2
    assert all(available_charts.json()["chart_ids"])


def test_compatibility_rejects_chart_pair_from_wrong_profile_or_system():
    token = login_token()
    first = create_profile(token=token).json()
    second = create_profile(token=token, overrides={"display_name": "Second profile"}).json()
    headers = {"Authorization": f"Bearer {token}"}
    first_chart = client.post("/api/v1/astrology/charts", json={
        "profile_id": first["id"], "system": "vedic", "division": "D1",
    }, headers=headers).json()
    second_chart = client.post("/api/v1/astrology/charts", json={
        "profile_id": second["id"], "system": "vedic", "division": "D1",
    }, headers=headers).json()
    mismatched = client.post("/api/v1/compatibility/check", json={
        "profile_a_id": first["id"], "profile_b_id": second["id"], "system": "western",
        "chart_a_id": first_chart["id"], "chart_b_id": second_chart["id"],
    }, headers=headers)
    assert mismatched.status_code == 404
    assert mismatched.json()["detail"] == "Chart not found"


def test_profile_update_and_delete():
    token = login_token()
    created = create_profile(token=token)
    profile_id = created.json()["id"]
    updated = client.patch(
        f"/api/v1/profiles/{profile_id}",
        json={"display_name": "Updated profile", "relationship": "mother"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert updated.status_code == 200
    assert updated.json()["display_name"] == "Updated profile"
    assert updated.json()["relationship"] == "mother"
    removed = client.delete(f"/api/v1/profiles/{profile_id}", headers={"Authorization": f"Bearer {token}"})
    assert removed.status_code == 204
    assert client.get(f"/api/v1/profiles/{profile_id}", headers={"Authorization": f"Bearer {token}"}).status_code == 404


def test_profile_rejects_missing_and_invalid_fields():
    token = login_token()
    missing = client.post("/api/v1/profiles", json={"display_name": "Missing details"}, headers={"Authorization": f"Bearer {token}"})
    assert missing.status_code == 422
    bad_timezone = create_profile(token=token, overrides={"timezone": "Mars/Olympus"})
    assert bad_timezone.status_code == 422
    bad_coordinates = create_profile(token=token, overrides={"latitude": 13.0, "longitude": None})
    assert bad_coordinates.status_code == 422
    future_date = create_profile(token=token, overrides={"birth_date": "2999-01-01"})
    assert future_date.status_code == 422


def test_profile_cross_user_access_is_denied():
    owner_token = login_token()
    created = create_profile(token=owner_token)
    with TestSession() as session:
        session.add(User(email="other@example.com", password_hash=hash_password("other-password")))
        session.commit()
    other_token = login_token("other@example.com", "other-password")
    profile_id = created.json()["id"]
    assert client.get(f"/api/v1/profiles/{profile_id}", headers={"Authorization": f"Bearer {other_token}"}).status_code == 404
    assert client.patch(f"/api/v1/profiles/{profile_id}", json={"display_name": "stolen"}, headers={"Authorization": f"Bearer {other_token}"}).status_code == 404
    assert client.delete(f"/api/v1/profiles/{profile_id}", headers={"Authorization": f"Bearer {other_token}"}).status_code == 404
    assert client.get("/api/v1/profiles", headers={"Authorization": f"Bearer {other_token}"}).json() == []


def test_vedic_chart_api_persists_d9_and_enforces_profile_ownership(monkeypatch):
    from app.services.astrology.vedic import VEDIC_ENGINE_VERSION
    import app.api.routes as api_routes

    class Provider:
        ephemeris_version = "test-ephemeris-1"
        ffi = None

    class TestVedicEngine:
        def get_provider(self):
            return Provider()

        def calculate_chart(self, birth_data, config):
            return {
                "calculation_flags": {"requested": 1}, "engine_version": ENGINE_VERSION,
                "ephemeris_version": "test-ephemeris-1", "julian_day_ut": 2451545.0,
                "division": config["division"], "configuration": config,
            }

    monkeypatch.setattr(api_routes, "VedicAstrologyEngine", TestVedicEngine)
    owner = login_token()
    profile = create_profile(token=owner).json()
    result = client.post("/api/v1/astrology/charts/vedic", json={"profile_id": profile["id"], "division": "D9"}, headers={"Authorization": f"Bearer {owner}"})
    assert result.status_code == 201, result.text
    body = result.json()
    assert body["configuration"]["division"] == "D9"
    assert body["configuration"]["vedic_engine_version"] == VEDIC_ENGINE_VERSION
    assert body["result"]["division"] == "D9"
    assert client.get(f"/api/v1/astrology/charts/{body['chart_id']}", headers={"Authorization": f"Bearer {owner}"}).status_code == 200

    with TestSession() as session:
        session.add(User(email="other@example.com", password_hash=hash_password("other-password")))
        session.commit()
    other = login_token("other@example.com", "other-password")
    assert client.post("/api/v1/astrology/charts/vedic", json={"profile_id": profile["id"], "division": "D9"}, headers={"Authorization": f"Bearer {other}"}).status_code == 404
    assert client.get(f"/api/v1/astrology/charts/{body['chart_id']}", headers={"Authorization": f"Bearer {other}"}).status_code == 404


def test_vedic_dignity_reads_owned_completed_d1_snapshot_only():
    from app.services.astrology.sweph import RASHIS

    token = login_token()
    profile = create_profile(token=token).json()
    placements = [
        {"name": name, "longitude": index * 30.0 + 1.0, "rashi": RASHIS[index], "rashi_index": index}
        for index, name in enumerate(("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"))
    ]
    with TestSession() as session:
        chart = BirthChart(
            profile_id=UUID(profile["id"]), system="vedic", division="D1", status="complete",
            unavailable_reason="", config={"zodiac": "sidereal", "ayanamsa": "lahiri"},
        )
        session.add(chart)
        session.flush()
        run = ChartCalculationRun(
            chart_id=chart.id, run_number=1, status="complete", config={"ayanamsa": "lahiri"},
            result={"calculation_system": "vedic", "division": "D1", "configuration": {"ayanamsa": "lahiri"}, "planets": placements},
        )
        session.add(run)
        session.commit()
        chart_id = str(chart.id)

    own = client.get(f"/api/v1/astrology/charts/{chart_id}/vedic-dignity", headers={"Authorization": f"Bearer {token}"})
    assert own.status_code == 200, own.text
    body = own.json()
    assert body["chart_id"] == chart_id
    assert body["profile_id"] == profile["id"]
    assert body["status"] == "provisional"
    assert len(body["planets"]) == 7
    assert {item["source_id"] for item in body["source_references"]} == {
        "vedic.bphs.vedicpupil.web-ch3", "vedic.bphs.parashara-net.web-ch3",
    }
    assert all("unverified" in item["verification_status"] for item in body["source_references"])
    assert body["shadbala"]["status"] == "unavailable"
    assert "birth_date" not in body and "birthplace" not in body

    with TestSession() as session:
        session.add(User(email="dignity-other@example.com", password_hash=hash_password("other-password")))
        session.commit()
    other = login_token("dignity-other@example.com", "other-password")
    assert client.get(f"/api/v1/astrology/charts/{chart_id}/vedic-dignity", headers={"Authorization": f"Bearer {other}"}).status_code == 404


def test_vedic_dignity_rejects_d9_and_incomplete_saved_charts():
    token = login_token()
    profile = create_profile(token=token).json()
    with TestSession() as session:
        d9 = BirthChart(profile_id=UUID(profile["id"]), system="vedic", division="D9", status="complete", unavailable_reason="", config={})
        pending = BirthChart(profile_id=UUID(profile["id"]), system="vedic", division="D1", status="unavailable", unavailable_reason="disabled", config={})
        session.add_all([d9, pending])
        session.commit()
        d9_id, pending_id = str(d9.id), str(pending.id)
    headers = {"Authorization": f"Bearer {token}"}
    assert client.get(f"/api/v1/astrology/charts/{d9_id}/vedic-dignity", headers=headers).status_code == 422
    assert client.get(f"/api/v1/astrology/charts/{pending_id}/vedic-dignity", headers=headers).status_code == 409


def test_western_d9_is_rejected():
    token = login_token()
    profile = create_profile(token=token).json()
    response = client.post("/api/v1/astrology/charts/western", json={"profile_id": profile["id"], "division": "D9"}, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 422


def test_western_chart_api_persists_configuration_and_enforces_ownership(monkeypatch):
    import app.api.routes as api_routes
    from app.services.astrology.western import WESTERN_ENGINE_VERSION

    class Provider:
        ephemeris_version = "test-ephemeris-1"

    class TestWesternEngine:
        def get_provider(self):
            return Provider()

        def calculate_chart(self, birth_data, config):
            return {
                "calculation_flags": {"requested": 1}, "engine_version": ENGINE_VERSION,
                "ephemeris_version": "test-ephemeris-1", "configuration": config,
                "calculation_system": "western", "planets": [], "houses": [], "aspects": [],
            }

    monkeypatch.setattr(api_routes, "WesternAstrologyEngine", TestWesternEngine)
    owner_token = login_token()
    profile = create_profile(token=owner_token).json()
    response = client.post("/api/v1/astrology/charts/western", json={
        "profile_id": profile["id"], "house_system": "W", "aspect_orbs": {"conjunction": 3.5},
    }, headers={"Authorization": f"Bearer {owner_token}"})
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["configuration"]["house_system"] == "W"
    assert body["configuration"]["aspect_orbs"]["conjunction"] == 3.5
    assert body["configuration"]["aspect_orbs"]["sextile"] == 6.0
    assert body["configuration"]["western_engine_version"] == WESTERN_ENGINE_VERSION
    assert body["engine_version"].endswith(WESTERN_ENGINE_VERSION)
    saved = client.get(f"/api/v1/astrology/charts/{body['chart_id']}", headers={"Authorization": f"Bearer {owner_token}"})
    assert saved.status_code == 200
    assert saved.json()["result"]["calculation_system"] == "western"
    history = client.get(f"/api/v1/astrology/charts?profile_id={profile['id']}&system=western", headers={"Authorization": f"Bearer {owner_token}"})
    assert history.status_code == 200
    history_item = history.json()["items"][0]
    assert history_item["id"] == body["chart_id"] and history_item["status"] == "complete"
    assert history_item["configuration"]["house_system"] == "W"

    with TestSession() as session:
        session.add(User(email="other@example.com", password_hash=hash_password("other-password")))
        session.commit()
    other_token = login_token("other@example.com", "other-password")
    assert client.post("/api/v1/astrology/charts/western", json={"profile_id": profile["id"]}, headers={"Authorization": f"Bearer {other_token}"}).status_code == 404
    assert client.get(f"/api/v1/astrology/charts/{body['chart_id']}", headers={"Authorization": f"Bearer {other_token}"}).status_code == 404


def test_calculation_failures_do_not_expose_runtime_paths_or_native_errors(monkeypatch):
    import app.api.routes as api_routes
    from app.services.astrology.base import EngineUnavailable

    class BrokenEngine:
        def get_provider(self):
            raise EngineUnavailable("native failure at /private/ephemeris/sepl_18.se1")

    monkeypatch.setattr(api_routes, "VedicAstrologyEngine", BrokenEngine)
    token = login_token()
    profile = create_profile(token=token).json()
    response = client.post(
        "/api/v1/astrology/charts/vedic",
        json={"profile_id": profile["id"]},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 503
    assert response.json()["detail"] == "The Swiss Ephemeris native runtime is unavailable. No calculation was performed and no chart was saved."
    assert "/private/ephemeris" not in response.text and "sepl_18.se1" not in response.text


def test_chart_history_is_paginated_filtered_private_and_owner_scoped():
    owner_token = login_token()
    first_profile = create_profile(token=owner_token, overrides={"display_name": "History profile one"}).json()
    second_profile = create_profile(token=owner_token, overrides={"display_name": "History profile two"}).json()

    def create_saved(profile_id, system, division="D1"):
        response = client.post("/api/v1/astrology/charts", json={
            "profile_id": profile_id, "system": system, "division": division,
        }, headers={"Authorization": f"Bearer {owner_token}"})
        assert response.status_code == 202, response.text
        return response.json()

    saved_first = create_saved(first_profile["id"], "vedic", "D9")
    create_saved(first_profile["id"], "western")
    create_saved(second_profile["id"], "vedic")

    response = client.get("/api/v1/astrology/charts?profile_id={}&system=vedic&limit=1&offset=0".format(first_profile["id"]), headers={"Authorization": f"Bearer {owner_token}"})
    assert response.status_code == 200, response.text
    page = response.json()
    assert page["total"] == 1
    assert page["limit"] == 1 and page["offset"] == 0
    assert len(page["items"]) == 1
    item = page["items"][0]
    assert item["id"] == saved_first["id"]
    assert item["profile_id"] == first_profile["id"]
    assert item["profile_name"] == "History profile one"
    assert item["system"] == "vedic" and item["division"] == "D9"
    assert item["status"] == "unavailable"
    assert item["created_at"] and isinstance(item["configuration"], dict)
    assert "birth_date" not in item and "birthplace" not in item and "latitude" not in item

    all_profile_charts = client.get("/api/v1/astrology/charts?profile_id={}&limit=10&offset=0".format(first_profile["id"]), headers={"Authorization": f"Bearer {owner_token}"}).json()
    first_page = client.get("/api/v1/astrology/charts?profile_id={}&limit=1&offset=0".format(first_profile["id"]), headers={"Authorization": f"Bearer {owner_token}"}).json()
    next_page = client.get("/api/v1/astrology/charts?profile_id={}&limit=1&offset=1".format(first_profile["id"]), headers={"Authorization": f"Bearer {owner_token}"}).json()
    assert next_page["total"] == 2 and len(next_page["items"]) == len(first_page["items"]) == 1
    assert first_page["items"][0]["id"] != next_page["items"][0]["id"]
    assert {item["id"] for item in all_profile_charts["items"]} == {item["id"] for item in first_page["items"] + next_page["items"]}

    with TestSession() as session:
        session.add(User(email="history-other@example.com", password_hash=hash_password("other-password")))
        session.commit()
    other_token = login_token("history-other@example.com", "other-password")
    foreign_history = client.get("/api/v1/astrology/charts", headers={"Authorization": f"Bearer {other_token}"})
    assert foreign_history.status_code == 200
    assert foreign_history.json() == {"items": [], "total": 0, "limit": 20, "offset": 0}
    filtered_foreign = client.get(f"/api/v1/astrology/charts?profile_id={first_profile['id']}", headers={"Authorization": f"Bearer {other_token}"})
    assert filtered_foreign.status_code == 200 and filtered_foreign.json()["total"] == 0
    assert client.get("/api/v1/astrology/charts?system=invalid", headers={"Authorization": f"Bearer {owner_token}"}).status_code == 422
    assert client.get("/api/v1/astrology/charts?limit=101", headers={"Authorization": f"Bearer {owner_token}"}).status_code == 422
    assert client.get("/api/v1/astrology/charts").status_code == 401

def _seed_saved_chart(profile_id, system, division, result):
    from app.models.entities import BirthChart, ChartCalculationRun

    with TestSession() as session:
        chart = BirthChart(
            profile_id=UUID(profile_id), system=system, division=division,
            status="complete", unavailable_reason="", config={},
        )
        session.add(chart)
        session.flush()
        session.add(ChartCalculationRun(
            chart_id=chart.id, run_number=1, status="complete", config={},
            input_snapshot={"birthplace": "private fixture location", "birth_date": "1990-05-14"},
            result={"calculation_system": system, "division": division, **result},
            engine_version="fixture-engine/1.0.0", ephemeris_version="fixture-ephemeris",
        ))
        session.commit()
        return str(chart.id)


def _create_ai_conversation(token, profile_id, *, system="vedic", language="en", chart_id=None):
    response = client.post("/api/v1/ai/conversations", json={
        "profile_id": profile_id, "chart_id": chart_id,
        "astrology_system": system, "language": language,
    }, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 201, response.text
    return response.json()


def test_deterministic_ai_stream_persists_structured_chart_facts_and_uses_no_provider(monkeypatch):
    import socket
    from app.models.entities import AIUsageLog, ChatMessage

    def reject_network(*args, **kwargs):
        raise AssertionError("deterministic chat attempted an outbound network call")

    monkeypatch.setattr(socket.socket, "connect", reject_network)
    monkeypatch.setattr(socket, "create_connection", reject_network)
    token = login_token()
    profile = create_profile(token=token).json()
    chart_id = _seed_saved_chart(profile["id"], "vedic", "D1", {
        "planets": [{"name": "Sun", "longitude": 15.2, "rashi": "Mesha", "house": 1, "retrograde": False,
                     "nakshatra": {"name": "Ashwini", "lord": "Ketu", "pada": 2, "remaining_fraction": 0.5}}],
        "houses": [{"number": 1, "sign": "Mesha"}],
    })
    conversation = _create_ai_conversation(token, profile["id"], chart_id=chart_id)
    headers = {"Authorization": f"Bearer {token}", "Idempotency-Key": "deterministic-answer-1"}
    url = f"/api/v1/ai/conversations/{conversation['id']}/messages/stream"
    streamed = client.post(url, json={"content": "In my Vedic D1 chart, what is the Sun sign?"}, headers=headers)
    assert streamed.status_code == 200, streamed.text
    assert "event: metadata" in streamed.text and '"status": "answered"' in streamed.text
    assert "event: delta" in streamed.text and "event: done" in streamed.text
    assert "Sun is recorded in Mesha." in streamed.text
    history = client.get(f"/api/v1/ai/conversations/{conversation['id']}", headers=headers).json()
    assert [message["role"] for message in history["messages"]] == ["user", "assistant"]
    saved = history["messages"][1]
    assert saved["provider"] == "deterministic" and saved["input_tokens"] == saved["output_tokens"] == 0
    assert saved["structured_response"]["metadata"]["system"] == "vedic"
    assert saved["structured_response"]["metadata"]["division"] == "D1"
    fact_sections = [section for section in saved["structured_response"]["sections"] if section["section_type"] == "calculated_fact"]
    assert fact_sections and all(section["fact_ids"] and section["fact_references"] for section in fact_sections)
    assert all("private fixture location" not in message["content"] and "1990-05-14" not in message["content"] for message in history["messages"])
    with TestSession() as session:
        assert session.query(AIUsageLog).filter_by(feature="ai_chat", status="completed").count() == 1
        assert session.query(ChatMessage).filter_by(session_id=UUID(conversation["id"]), role="assistant").one().response_data


def test_greeting_works_without_chart_and_message_language_overrides_conversation_language():
    token = login_token()
    profile = create_profile(token=token).json()
    conversation = _create_ai_conversation(token, profile["id"], system="vedic", language="en")
    response = client.post(
        f"/api/v1/ai/conversations/{conversation['id']}/messages",
        json={"content": "வணக்கம்"}, headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200, response.text
    structured = response.json()["message"]["structured_response"]
    assert structured["status"] == "needs_clarification"
    assert structured["metadata"]["language"] == "ta"
    assert "வணக்கம்" in structured["answer"]
    assert "usage" not in response.json()


def test_chat_route_supplies_only_prior_conversation_turns_to_followup_classifier(monkeypatch):
    import app.api.ai_routes as ai_routes

    token = login_token()
    profile = create_profile(token=token).json()
    conversation = _create_ai_conversation(token, profile["id"])
    real_engine = ai_routes.get_intelligence_engine()
    observed = []

    class CapturingEngine:
        def answer_for_session(self, db, chat, user, question, *, history=()):
            observed.append((question, tuple((turn.role, turn.content) for turn in history)))
            return real_engine.answer_for_session(db, chat, user, question, history=history)

    monkeypatch.setattr(ai_routes, "get_intelligence_engine", lambda: CapturingEngine())
    url = f"/api/v1/ai/conversations/{conversation['id']}/messages"
    headers = {"Authorization": f"Bearer {token}"}
    assert client.post(url, json={"content": "Where is my Moon in my Vedic chart?"}, headers=headers).status_code == 200
    assert client.post(url, json={"content": "What about its house?"}, headers=headers).status_code == 200
    assert observed[0] == ("Where is my Moon in my Vedic chart?", ())
    assert observed[1][0] == "What about its house?"
    assert len(observed[1][1]) == 2
    assert observed[1][1][0] == ("user", "Where is my Moon in my Vedic chart?")
    assert observed[1][1][1][0] == "assistant"


def test_missing_chart_unsupported_and_general_knowledge_states_are_explicit():
    token = login_token()
    profile = create_profile(token=token).json()
    headers = {"Authorization": f"Bearer {token}"}
    conversation = _create_ai_conversation(token, profile["id"], system="western", language="en")
    base = f"/api/v1/ai/conversations/{conversation['id']}/messages"
    missing = client.post(base, json={"content": "In my Western natal chart, where is my Moon?"}, headers=headers)
    assert missing.status_code == 200
    assert missing.json()["message"]["structured_response"]["status"] == "missing_chart"
    unsupported = client.post(base, json={"content": "What is today's weather?"}, headers=headers)
    assert unsupported.status_code == 200
    assert unsupported.json()["message"]["structured_response"]["status"] == "unsupported"
    general = client.post(base, json={"content": "What is a Nakshatra?"}, headers=headers)
    assert general.status_code == 200
    general_response = general.json()["message"]["structured_response"]
    assert general_response["status"] == "answered"
    assert general_response["metadata"]["content_classification"] == "general_education"
    assert general_response["metadata"]["source_verification_status"] == "not_independently_verified"
    assert any(section["section_type"] == "general_education" and "27 Nakshatras" in section["text"] for section in general_response["sections"])
    assert any("not been independently source-verified" in section["text"] for section in general_response["sections"])
    assert not general_response["answer_fact_ids"] and not general_response["answer_rule_ids"]


@pytest.mark.parametrize(("question", "language", "phrase"), [
    ("What is the difference between Vedic and Western astrology?", "en", "sidereal zodiac"),
    ("What are the 12 zodiac signs?", "en", "Aries (Mesha)"),
    ("What are the 12 houses?", "en", "1 self and body"),
    ("What are Nakshatras?", "en", "27 Nakshatras"),
    ("வேத மற்றும் மேற்கத்திய ஜோதிடத்திற்கு என்ன வேறுபாடு?", "ta", "நிராயண ராசிச்சக்கரம்"),
    ("12 ராசிகள் என்றால் என்ன?", "ta", "மேஷம்"),
    ("நட்சத்திரங்கள் என்றால் என்ன?", "ta", "27 நட்சத்திரங்களாக"),
])
def test_general_astrology_questions_are_useful_without_a_saved_chart(question, language, phrase):
    token = login_token()
    profile = create_profile(token=token).json()
    conversation = _create_ai_conversation(token, profile["id"], system="vedic", language="en", chart_id=None)
    response = client.post(
        f"/api/v1/ai/conversations/{conversation['id']}/messages/stream",
        json={"content": question},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200, response.text
    assert '"status": "answered"' in response.text
    history = client.get(
        f"/api/v1/ai/conversations/{conversation['id']}",
        headers={"Authorization": f"Bearer {token}"},
    ).json()
    structured = history["messages"][1]["structured_response"]
    assert structured["metadata"]["language"] == language
    assert structured["metadata"]["system"] is None
    assert structured["metadata"]["division"] is None
    assert structured["metadata"]["content_classification"] == "general_education"
    assert structured["metadata"]["source_verification_status"] == "not_independently_verified"
    educational_section = next(section for section in structured["sections"] if section["section_type"] == "general_education")
    assert phrase in educational_section["text"]
    assert not educational_section["fact_references"] and not educational_section["rule_references"]
    assert not structured["answer_fact_ids"] and not structured["answer_rule_ids"]
    assert "Brihat Parashara" not in educational_section["text"]
    assert "Chapter" not in educational_section["text"] and "அத்தியாயம்" not in educational_section["text"]


def test_general_education_followup_uses_prior_user_topic_without_chart():
    token = login_token()
    profile = create_profile(token=token).json()
    conversation = _create_ai_conversation(token, profile["id"], chart_id=None)
    headers = {"Authorization": f"Bearer {token}"}
    url = f"/api/v1/ai/conversations/{conversation['id']}/messages"
    first = client.post(url, json={"content": "What are the 12 zodiac signs?"}, headers=headers)
    second = client.post(url, json={"content": "Tell me more"}, headers=headers)
    assert first.status_code == second.status_code == 200
    structured = second.json()["message"]["structured_response"]
    assert structured["status"] == "answered"
    assert structured["metadata"]["education_topic"] == "zodiac_signs"
    assert structured["metadata"]["content_classification"] == "general_education"


@pytest.mark.parametrize(("language", "questions", "expected_phrases"), [
    ("en", [
        "What is a Nakshatra?",
        "How many Padas does each Nakshatra have?",
        "Can you explain Ashwini Nakshatra in detail?",
        "What is its ruling planet?",
        "How is it used in Vedic birth chart interpretation?",
    ], ["27 Nakshatras", "four Padas", "Ashwini", "assigned to Ketu", "general Vedic chart practice"]),
    ("ta", [
        "நட்சத்திரம் என்றால் என்ன?",
        "ஒவ்வொரு நட்சத்திரத்திற்கும் எத்தனை பாதங்கள்?",
        "அசுவினி நட்சத்திரம் பற்றி விரிவாக விளக்குங்கள்",
        "அதன் அதிபதி யார்?",
        "வேத ஜாதக விளக்கத்தில் இது எவ்வாறு பயன்படுத்தப்படுகிறது?",
    ], ["27 நட்சத்திரங்களாக", "நான்கு பாதங்களாக", "அசுவினி", "கேது", "பொதுவான வேத ஜாதக நடைமுறையில்"]),
])
def test_nakshatra_educational_followup_conversation_uses_catalogue_without_chart(language, questions, expected_phrases):
    token = login_token()
    profile = create_profile(token=token).json()
    conversation = _create_ai_conversation(token, profile["id"], system="vedic", language=language, chart_id=None)
    headers = {"Authorization": f"Bearer {token}"}
    responses = []
    for index, question in enumerate(questions):
        response = client.post(
            f"/api/v1/ai/conversations/{conversation['id']}/messages",
            json={"content": question},
            headers=headers,
        )
        assert response.status_code == 200, response.text
        structured = response.json()["message"]["structured_response"]
        assert structured["status"] == "answered", (question, structured)
        assert structured["metadata"]["content_classification"] == "general_education"
        assert structured["metadata"]["source_verification_status"] == "not_independently_verified"
        assert structured["metadata"]["system"] is None
        assert structured["metadata"]["division"] is None
        assert structured["answer_fact_ids"] == []
        assert structured["answer_rule_ids"] == []
        education = next(section for section in structured["sections"] if section["section_type"] == "general_education")
        assert expected_phrases[index] in education["text"]
        responses.append(education["text"])
    assert "Birthplace" not in " ".join(responses)
    assert "birth_date" not in " ".join(responses)
    assert "chart fact" not in " ".join(responses).casefold()


@pytest.mark.parametrize(("question", "language", "division"), [
    ("What can you tell me about my birth chart?", "en", None),
    ("Tell me about my horoscope.", "en", None),
    ("What does my Lagna mean?", "en", None),
    ("Explain my Navamsa.", "en", "D9"),
    ("என் ஜாதகத்தைப் பற்றி என்ன சொல்ல முடியும்?", "ta", None),
    ("என் ஜாதகத்தைப் பற்றி சொல்லுங்கள்.", "ta", None),
    ("என் லக்னம் பற்றி சொல்லுங்கள்.", "ta", None),
    ("என் நவாம்சத்தை விளக்குங்கள்.", "ta", "D9"),
])
def test_frontend_chat_payload_returns_localized_missing_chart_without_clarification(question, language, division):
    token = login_token()
    profile = create_profile(token=token).json()
    conversation = _create_ai_conversation(
        token, profile["id"], system="vedic", language="en", chart_id=None,
    )
    assert conversation["profile_id"] == profile["id"]
    assert conversation["astrology_system"] == "vedic"
    assert conversation["chart_id"] is None

    # Mirrors AIChatPage's actual stream request body for the selected profile,
    # Vedic system, and empty "Saved calculated chart" selection.
    response = client.post(
        f"/api/v1/ai/conversations/{conversation['id']}/messages/stream",
        json={"content": question},
        headers={"Authorization": f"Bearer {token}", "Idempotency-Key": "missing-chart-api-regression"},
    )
    assert response.status_code == 200, response.text
    assert '"status": "missing_chart"' in response.text
    history = client.get(
        f"/api/v1/ai/conversations/{conversation['id']}",
        headers={"Authorization": f"Bearer {token}"},
    ).json()
    assistant = history["messages"][1]["structured_response"]
    assert assistant["status"] == "missing_chart"
    assert assistant["metadata"]["system"] == "vedic"
    assert assistant["metadata"]["division"] == division
    assert assistant["metadata"]["language"] == language
    if language == "en":
        assert "completed saved chart is required" in assistant["answer"]
        assert "Birth chart" in assistant["answer"]
    else:
        assert "முடிக்கப்பட்ட சேமித்த ஜாதகம் தேவை" in assistant["answer"]
        assert "‘ஜாதகம்’" in assistant["answer"]
    assert not assistant["answer_fact_ids"]
    assert "clarify" not in assistant["answer"].casefold()


def test_missing_chart_keeps_clarification_for_conflicting_system_request():
    token = login_token()
    profile = create_profile(token=token).json()
    conversation = _create_ai_conversation(token, profile["id"], system="vedic", chart_id=None)
    response = client.post(
        f"/api/v1/ai/conversations/{conversation['id']}/messages/stream",
        json={"content": "Compare my Vedic and Western charts"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert '"status": "needs_clarification"' in response.text


def test_western_saved_chart_returns_only_owned_actual_chart_facts():
    token = login_token()
    profile = create_profile(token=token).json()
    chart_id = _seed_saved_chart(profile["id"], "western", "W", {
        "planets": [{"name": "Moon", "longitude": 48.4, "sign": "Taurus", "house": 2, "retrograde": False}],
        "ascendant": {"longitude": 10.0, "sign": "Aries", "house": 1},
        "midheaven": {"longitude": 280.0, "sign": "Capricorn", "house": 10},
        "houses": [{"number": 2, "sign": "Taurus"}],
        "aspects": [{"planet_a": "Sun", "planet_b": "Moon", "aspect": "trine", "orb": 1.2, "motion": "applying"}],
    })
    conversation = _create_ai_conversation(token, profile["id"], system="western", chart_id=chart_id)
    response = client.post(
        f"/api/v1/ai/conversations/{conversation['id']}/messages",
        json={"content": "In my Western natal chart, what is my Moon sign?"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200, response.text
    structured = response.json()["message"]["structured_response"]
    assert structured["status"] == "answered"
    assert structured["metadata"]["system"] == "western"
    assert structured["metadata"]["division"] == "W"
    assert any("Moon is recorded in Taurus" in section["text"] for section in structured["sections"])


def test_test_only_knowledge_is_not_emitted_by_chat():
    token = login_token()
    profile = create_profile(token=token).json()
    chart_id = _seed_saved_chart(profile["id"], "vedic", "D1", {
        "planets": [{"name": "Moon", "longitude": 42.0, "rashi": "Vrishabha", "house": 4, "retrograde": False,
                     "nakshatra": {"name": "Rohini", "lord": "Moon", "pada": 2}}],
        "houses": [],
    })
    conversation = _create_ai_conversation(token, profile["id"], chart_id=chart_id)
    response = client.post(
        f"/api/v1/ai/conversations/{conversation['id']}/messages",
        json={"content": "In my Vedic D1 chart, what is my Moon sign?"},
        headers={"Authorization": f"Bearer {token}"},
    )
    structured = response.json()["message"]["structured_response"]
    assert structured["status"] == "answered"
    assert structured["metadata"]["matched_rule_ids"] == []
    assert not any(section["section_type"] == "traditional_interpretation" for section in structured["sections"])
    assert all("TEST FIXTURE" not in section["text"] for section in structured["sections"])
    assert any("sourced traditional interpretation" in section["text"] for section in structured["sections"])


def test_foreign_chart_association_is_treated_as_missing_and_never_leaks_facts():
    from app.models.entities import BirthChart, BirthProfile, ChartCalculationRun, ChatSession

    owner_token = login_token()
    owner_profile = create_profile(token=owner_token).json()
    with TestSession() as session:
        foreign_user = User(email="foreign-ai@example.com", password_hash=hash_password("foreign-password"))
        session.add(foreign_user)
        session.flush()
        foreign_profile = BirthProfile(
            owner_id=foreign_user.id, display_name="Foreign profile", relationship="self",
            birth_date=date(1990, 1, 1), birth_time=None, time_accuracy="unknown", birthplace="private foreign place",
            country="", latitude=None, longitude=None, timezone=None,
        )
        session.add(foreign_profile)
        session.flush()
        foreign_chart = BirthChart(profile_id=foreign_profile.id, system="vedic", division="D1", status="complete", unavailable_reason="", config={})
        session.add(foreign_chart)
        session.flush()
        session.add(ChartCalculationRun(
            chart_id=foreign_chart.id, run_number=1, status="complete", config={},
            input_snapshot={}, result={"calculation_system": "vedic", "division": "D1", "planets": [
                {"name": "Moon", "longitude": 44.0, "rashi": "ForeignSecret", "house": 2, "retrograde": False},
            ]}, engine_version="fixture", ephemeris_version="fixture",
        ))
        session.flush()
        owner = session.query(User).filter_by(email="member@example.com").one()
        chat = ChatSession(
            user_id=owner.id, profile_id=foreign_profile.id, chart_id=foreign_chart.id,
            astrology_system="vedic", language="en", title="Foreign association",
        )
        session.add(chat)
        session.commit()
        conversation_id = str(chat.id)
    response = client.post(
        f"/api/v1/ai/conversations/{conversation_id}/messages",
        json={"content": "In my Vedic D1 chart, where is my Moon?"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert response.status_code == 200, response.text
    structured = response.json()["message"]["structured_response"]
    assert structured["status"] == "missing_chart"
    assert "ForeignSecret" not in response.text and "private foreign place" not in response.text
    assert owner_profile["id"] != str(foreign_profile.id)


def test_conversation_history_persists_structured_messages_and_idempotent_replay(monkeypatch):
    import app.api.ai_routes as ai_routes
    from app.models.entities import AIUsageLog, ChatMessage

    token = login_token()
    profile = create_profile(token=token).json()
    conversation = _create_ai_conversation(token, profile["id"])
    headers = {"Authorization": f"Bearer {token}", "Idempotency-Key": "deterministic-retry-1"}
    url = f"/api/v1/ai/conversations/{conversation['id']}/messages/stream"
    original = ai_routes._build_response
    calls = 0

    def fail_once(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("private diagnostic text")
        return original(*args, **kwargs)

    monkeypatch.setattr(ai_routes, "_build_response", fail_once)
    first = client.post(url, json={"content": "Hello"}, headers=headers)
    assert first.status_code == 503 and "private diagnostic" not in first.text
    assert [item["role"] for item in client.get(f"/api/v1/ai/conversations/{conversation['id']}", headers=headers).json()["messages"]] == ["user"]
    retry = client.post(url, json={"content": "Hello"}, headers=headers)
    assert retry.status_code == 200 and "event: done" in retry.text
    replay = client.post(url, json={"content": "Hello"}, headers=headers)
    assert replay.status_code == 200 and "event: done" in replay.text
    assert calls == 2
    assert client.post(url, json={"content": "Different"}, headers=headers).status_code == 409
    with TestSession() as session:
        assert session.query(AIUsageLog).one().period_key
        log = session.query(AIUsageLog).one()
        assert log.status == "completed"
        assert session.query(ChatMessage).filter_by(session_id=UUID(conversation["id"]), role="user").count() == 1
        assert session.query(ChatMessage).filter_by(session_id=UUID(conversation["id"]), role="assistant").count() == 1


def test_chat_has_no_daily_cap_and_failed_auth_is_rejected(monkeypatch):
    monkeypatch.setattr(settings, "ai_chat_rate_limit_per_minute", 100)
    token = login_token()
    profile = create_profile(token=token).json()
    conversation = _create_ai_conversation(token, profile["id"])
    url = f"/api/v1/ai/conversations/{conversation['id']}/messages"
    first = client.post(url, json={"content": "Hi"}, headers={"Authorization": f"Bearer {token}"})
    second = client.post(url, json={"content": "Another"}, headers={"Authorization": f"Bearer {token}"})
    assert first.status_code == second.status_code == 200
    assert "usage" not in first.json() and "usage" not in second.json()
    assert client.post(url, json={"content": "Hello"}).status_code == 401
    assert client.get("/api/v1/ai/conversations").status_code == 401


def test_chat_burst_rate_limit_allows_idempotent_replay_and_rejects_new_spam(monkeypatch):
    monkeypatch.setattr(settings, "ai_chat_rate_limit_per_minute", 1)
    token = login_token()
    profile = create_profile(token=token).json()
    conversation = _create_ai_conversation(token, profile["id"])
    url = f"/api/v1/ai/conversations/{conversation['id']}/messages"
    headers = {"Authorization": f"Bearer {token}", "Idempotency-Key": "burst-request-one"}
    first = client.post(url, json={"content": "Hello"}, headers=headers)
    replay = client.post(url, json={"content": "Hello"}, headers=headers)
    too_fast = client.post(url, json={"content": "Another question"}, headers={
        "Authorization": f"Bearer {token}", "Idempotency-Key": "burst-request-two",
    })
    assert first.status_code == replay.status_code == 200
    assert too_fast.status_code == 429
    assert "too quickly" in too_fast.json()["detail"]


def configure_reset_delivery(monkeypatch, deliver=None):
    import app.api.routes as routes

    monkeypatch.setattr(settings, "app_env", "test")
    monkeypatch.setattr(settings, "password_reset_smtp_host", "smtp.test.invalid")
    monkeypatch.setattr(settings, "password_reset_smtp_sender", "AstroAI <no-reply@example.test>")
    monkeypatch.setattr(settings, "password_reset_frontend_url", "https://astroai.example.test")
    if deliver is not None:
        monkeypatch.setattr(routes, "deliver_reset_link", deliver)
    return routes


def test_forgot_password_is_neutral_and_persists_only_random_token_hash(monkeypatch):
    delivered = []
    configure_reset_delivery(monkeypatch, lambda email, url: delivered.append(url))
    known = client.post("/api/v1/auth/forgot-password", json={"email": "member@example.com"})
    unknown = client.post("/api/v1/auth/forgot-password", json={"email": "nobody@example.com"})
    assert known.status_code == unknown.status_code == 202
    assert known.json() == unknown.json()
    assert len(delivered) == 1 and "token=" in delivered[0]
    raw_token = parse_qs(urlparse(delivered[0]).fragment)["token"][0]
    assert raw_token not in known.text and raw_token not in unknown.text
    with TestSession() as session:
        reset = session.query(PasswordResetToken).one()
        assert reset.token_hash != raw_token
        import hashlib
        assert reset.token_hash == hashlib.sha256(raw_token.encode()).hexdigest()
        assert reset.expires_at.replace(tzinfo=timezone.utc) - reset.created_at.replace(tzinfo=timezone.utc) == timedelta(minutes=30)
        assert session.query(SecurityAuditEvent).filter_by(event_type="password_reset_requested").count() == 1


def test_reset_password_is_single_use_changes_hash_and_revokes_old_access_token(monkeypatch):
    delivered = []
    configure_reset_delivery(monkeypatch, lambda email, url: delivered.append(url))
    access_token = login_token()
    client.post("/api/v1/auth/forgot-password", json={"email": "member@example.com"})
    reset_token = parse_qs(urlparse(delivered[0]).fragment)["token"][0]
    with TestSession() as session:
        old_hash = session.scalar(select(User.password_hash).where(User.email == "member@example.com"))
    updated = client.post("/api/v1/auth/reset-password", json={"token": reset_token, "new_password": "new-safe-password-456"})
    assert updated.status_code == 200
    assert client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {access_token}"}).status_code == 401
    assert client.post("/api/v1/auth/reset-password", json={"token": reset_token, "new_password": "other-safe-password-456"}).status_code == 400
    assert client.post("/api/v1/auth/login", data={"username": "member@example.com", "password": "correct-password"}).status_code == 401
    assert client.post("/api/v1/auth/login", data={"username": "member@example.com", "password": "new-safe-password-456"}).status_code == 200
    with TestSession() as session:
        new_hash = session.scalar(select(User.password_hash).where(User.email == "member@example.com"))
        assert old_hash != new_hash
        assert session.query(SecurityAuditEvent).filter_by(event_type="password_reset_completed").count() == 1


def test_reset_rejects_invalid_and_expired_tokens(monkeypatch):
    delivered = []
    configure_reset_delivery(monkeypatch, lambda email, url: delivered.append(url))
    assert client.post("/api/v1/auth/reset-password", json={"token": "x" * 43, "new_password": "safe-password-456"}).status_code == 400
    client.post("/api/v1/auth/forgot-password", json={"email": "member@example.com"})
    token = parse_qs(urlparse(delivered[0]).fragment)["token"][0]
    with TestSession() as session:
        reset = session.query(PasswordResetToken).one()
        reset.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        session.commit()
    response = client.post("/api/v1/auth/reset-password", json={"token": token, "new_password": "safe-password-456"})
    assert response.status_code == 400
    assert "invalid or expired" in response.json()["detail"]


def test_reset_tokens_rotate_and_provider_failure_does_not_leak_secrets(monkeypatch, caplog):
    def broken_delivery(email, reset_url):
        raise RuntimeError("secret-token-or-password-must-not-be-logged")
    configure_reset_delivery(monkeypatch, broken_delivery)
    first = client.post("/api/v1/auth/forgot-password", json={"email": "member@example.com"})
    second = client.post("/api/v1/auth/forgot-password", json={"email": "member@example.com"})
    assert first.status_code == second.status_code == 202
    with TestSession() as session:
        tokens = session.query(PasswordResetToken).order_by(PasswordResetToken.created_at).all()
        assert len(tokens) == 2 and tokens[0].token_hash != tokens[1].token_hash
        assert tokens[0].consumed_at is not None and tokens[1].consumed_at is not None
    assert "secret-token-or-password-must-not-be-logged" not in caplog.text


def test_reset_delivery_unconfigured_is_service_unavailable_for_all_addresses(monkeypatch):
    monkeypatch.setattr(settings, "password_reset_smtp_host", None)
    monkeypatch.setattr(settings, "password_reset_smtp_sender", None)
    monkeypatch.setattr(settings, "password_reset_dev_token_file", None)
    existing = client.post("/api/v1/auth/forgot-password", json={"email": "member@example.com"})
    unknown = client.post("/api/v1/auth/forgot-password", json={"email": "nobody@example.com"})
    assert existing.status_code == unknown.status_code == 503
    assert existing.json() == unknown.json()


def test_password_reset_rate_limit_is_enforced_without_account_disclosure(monkeypatch):
    configure_reset_delivery(monkeypatch, lambda email, url: None)
    monkeypatch.setattr(settings, "password_reset_rate_limit_per_hour", 1)
    accepted = client.post("/api/v1/auth/forgot-password", json={"email": "member@example.com"})
    limited = client.post("/api/v1/auth/forgot-password", json={"email": "member@example.com"})
    assert accepted.status_code == 202 and limited.status_code == 429


def test_password_reset_ip_limit_applies_before_account_lookup(monkeypatch):
    configure_reset_delivery(monkeypatch, lambda email, url: None)
    monkeypatch.setattr(settings, "password_reset_ip_rate_limit_per_hour", 1)
    known = client.post("/api/v1/auth/forgot-password", json={"email": "member@example.com"})
    unknown = client.post("/api/v1/auth/forgot-password", json={"email": "nobody@example.com"})
    assert known.status_code == 202 and unknown.status_code == 429
    assert "account" not in unknown.json()["detail"].casefold()


def test_cross_conversation_idempotency_key_cannot_replay_another_conversation():
    token = login_token()
    profile = create_profile(token=token).json()
    first = _create_ai_conversation(token, profile["id"])
    second = _create_ai_conversation(token, profile["id"])
    headers = {"Authorization": f"Bearer {token}", "Idempotency-Key": "conversation-bound-key"}
    first_response = client.post(
        f"/api/v1/ai/conversations/{first['id']}/messages", json={"content": "Hi"}, headers=headers,
    )
    assert first_response.status_code == 200
    replay_other = client.post(
        f"/api/v1/ai/conversations/{second['id']}/messages", json={"content": "Hi"}, headers=headers,
    )
    assert replay_other.status_code == 409


def test_client_disconnect_before_done_does_not_persist_partial_assistant():
    import asyncio
    import app.api.ai_routes as ai_routes
    from app.models.entities import AIUsageLog, ChatMessage
    from app.schemas.api import AIMessageCreate

    token = login_token()
    profile = create_profile(token=token).json()
    conversation = _create_ai_conversation(token, profile["id"])
    with TestSession() as session:
        user = session.query(User).filter_by(email="member@example.com").one()
        response = asyncio.run(ai_routes.stream_message(
            UUID(conversation["id"]), AIMessageCreate(content="Hello"),
            request_key="disconnect-deterministic-1", user=user, db=session,
        ))
        async def disconnect_after_metadata_and_delta():
            metadata = await response.body_iterator.__anext__()
            assert "event: metadata" in metadata
            first_delta = await response.body_iterator.__anext__()
            assert "event: delta" in first_delta
            await response.body_iterator.aclose()
        asyncio.run(disconnect_after_metadata_and_delta())
    with TestSession() as session:
        usage = session.query(AIUsageLog).one()
        messages = session.query(ChatMessage).filter_by(session_id=UUID(conversation["id"])).all()
        assert usage.status == "failed"
        assert [message.role for message in messages] == ["user"]

def _create_vedic_compatibility_fixture(session, profile_id, moon_longitude, division="D1", ayanamsa="lahiri"):
    chart_config = {
        "division": division,
        "zodiac": "sidereal",
        "ayanamsa": ayanamsa,
        "house_system": "P",
    }
    chart = BirthChart(
        profile_id=profile_id,
        system="vedic",
        division=division,
        status="complete",
        unavailable_reason="",
        config=chart_config,
    )
    session.add(chart)
    session.flush()

    result = {
        "calculation_system": "vedic",
        "division": division,
        "ayanamsa_name": ayanamsa.title(),
        "configuration": {
            "division": division,
            "zodiac": "sidereal",
            "ayanamsa": ayanamsa,
        },
        "planets": [{"name": "Moon", "longitude": moon_longitude}],
    }
    run = ChartCalculationRun(
        chart_id=chart.id,
        run_number=1,
        status="complete",
        config=chart_config,
        input_snapshot={},
        result=result,
    )
    session.add(run)
    session.flush()
    return chart, run


def test_vedic_compatibility_calculates_and_persists_ashtakoota_report():
    token = login_token()
    first = create_profile(token=token).json()
    second = create_profile(token=token, overrides={"display_name": "Second profile"}).json()
    headers = {"Authorization": f"Bearer {token}"}

    with TestSession() as session:
        first_chart, first_run = _create_vedic_compatibility_fixture(session, UUID(first["id"]), 0.0)
        second_chart, second_run = _create_vedic_compatibility_fixture(session, UUID(second["id"]), 14.0)
        session.commit()
        chart_ids = (str(first_chart.id), str(second_chart.id))
        run_ids = (str(first_run.id), str(second_run.id))

    response = client.post("/api/v1/compatibility/check", json={
        "profile_a_id": first["id"], "profile_b_id": second["id"], "system": "vedic",
        "chart_a_id": chart_ids[0], "chart_b_id": chart_ids[1],
    }, headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "available"
    assert data["reason"] == "ashtakoota_calculated"
    assert data["score"] == 34
    assert data["maximum_score"] == 36
    assert len(data["factors"]) == 8
    assert data["result"]["role_mapping"]["profile_a"] == "bride"
    assert data["result"]["role_mapping"]["profile_b"] == "groom"
    assert data["result"]["calculation_run_ids"] == list(run_ids)

    with TestSession() as session:
        saved = session.get(CompatibilityReport, UUID(data["report_id"]))
        assert saved is not None
        assert saved.status == "complete"
        assert saved.system == "vedic"
        assert saved.profile_a_id == UUID(first["id"])
        assert saved.profile_b_id == UUID(second["id"])
        assert saved.result["total_score"] == 34
        assert len(saved.result["factors"]) == 8


def test_vedic_compatibility_auto_selects_d1_not_newer_d9():
    token = login_token()
    first = create_profile(token=token).json()
    second = create_profile(token=token, overrides={"display_name": "Second profile"}).json()
    headers = {"Authorization": f"Bearer {token}"}
    with TestSession() as session:
        _create_vedic_compatibility_fixture(session, UUID(first["id"]), 0.0, "D1")
        _create_vedic_compatibility_fixture(session, UUID(first["id"]), 90.0, "D9")
        _create_vedic_compatibility_fixture(session, UUID(second["id"]), 14.0, "D1")
        session.commit()

    response = client.post("/api/v1/compatibility/check", json={
        "profile_a_id": first["id"], "profile_b_id": second["id"], "system": "vedic",
    }, headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] == "available"
    assert response.json()["score"] == 34


def test_vedic_compatibility_rejects_explicit_d9_charts():
    token = login_token()
    first = create_profile(token=token).json()
    second = create_profile(token=token, overrides={"display_name": "Second profile"}).json()
    headers = {"Authorization": f"Bearer {token}"}
    with TestSession() as session:
        first_chart, _ = _create_vedic_compatibility_fixture(session, UUID(first["id"]), 0.0, "D9")
        second_chart, _ = _create_vedic_compatibility_fixture(session, UUID(second["id"]), 14.0, "D9")
        session.commit()
        chart_ids = (str(first_chart.id), str(second_chart.id))

    response = client.post("/api/v1/compatibility/check", json={
        "profile_a_id": first["id"], "profile_b_id": second["id"], "system": "vedic",
        "chart_a_id": chart_ids[0], "chart_b_id": chart_ids[1],
    }, headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] == "unavailable"
    assert response.json()["reason"] == "vedic_d1_chart_required"
    assert response.json()["score"] is None


def test_vedic_compatibility_rejects_non_lahiri_result():
    token = login_token()
    first = create_profile(token=token).json()
    second = create_profile(token=token, overrides={"display_name": "Second profile"}).json()
    headers = {"Authorization": f"Bearer {token}"}
    with TestSession() as session:
        first_chart, _ = _create_vedic_compatibility_fixture(session, UUID(first["id"]), 0.0)
        second_chart, second_run = _create_vedic_compatibility_fixture(session, UUID(second["id"]), 14.0)
        second_result = dict(second_run.result)
        second_result["ayanamsa_name"] = "Raman"
        second_result["configuration"] = dict(second_result["configuration"])
        second_result["configuration"]["ayanamsa"] = "raman"
        second_run.result = second_result
        session.commit()
        chart_ids = (str(first_chart.id), str(second_chart.id))

    response = client.post("/api/v1/compatibility/check", json={
        "profile_a_id": first["id"], "profile_b_id": second["id"], "system": "vedic",
        "chart_a_id": chart_ids[0], "chart_b_id": chart_ids[1],
    }, headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] == "unavailable"
    assert response.json()["reason"] == "d1_lahiri_moon_data_required"
    assert response.json()["score"] is None
