from fastapi.testclient import TestClient
from datetime import date
from uuid import UUID
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base, get_db
from app.main import app
from app.models.entities import User
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
    import app.services.ai.provider as legacy_provider
    from app.models.entities import AIUsageLog, ChatMessage
    import pytest

    monkeypatch.setattr(legacy_provider, "get_ai_provider", lambda: pytest.fail("legacy provider was called"))
    for key in ("AI_PROVIDER", "AI_BASE_URL", "AI_API_KEY", "AI_MODEL"):
        monkeypatch.delenv(key, raising=False)
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
    assert response.json()["usage"]["requests_used"] == 1


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
    assert general_response["status"] == "unsupported"
    assert "approved, sourced general astrology" in general_response["answer"]


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
    from app.models.entities import AIUsageDailyCounter, AIUsageLog, ChatMessage

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
        assert session.query(AIUsageDailyCounter).one().request_count == 1
        log = session.query(AIUsageLog).one()
        assert log.status == "completed"
        assert session.query(ChatMessage).filter_by(session_id=UUID(conversation["id"]), role="user").count() == 1
        assert session.query(ChatMessage).filter_by(session_id=UUID(conversation["id"]), role="assistant").count() == 1


def test_daily_usage_limit_remains_per_user_and_failed_auth_is_rejected(monkeypatch):
    monkeypatch.setattr(settings, "ai_free_daily_limit", 1)
    token = login_token()
    profile = create_profile(token=token).json()
    conversation = _create_ai_conversation(token, profile["id"])
    url = f"/api/v1/ai/conversations/{conversation['id']}/messages"
    assert client.post(url, json={"content": "Hi"}, headers={"Authorization": f"Bearer {token}"}).status_code == 200
    assert client.post(url, json={"content": "Another"}, headers={"Authorization": f"Bearer {token}"}).status_code == 429
    assert client.post(url, json={"content": "Hello"}).status_code == 401
    assert client.get("/api/v1/ai/conversations").status_code == 401


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
