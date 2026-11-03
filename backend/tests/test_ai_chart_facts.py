from datetime import date, time
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.entities import BirthChart, BirthProfile, ChartCalculationRun, ChatSession, User
from app.services.ai.chart_facts import chart_facts_from_context
from app.services.ai.chat import load_session_chart_facts
from app.services.ai.contracts import AstrologySystem, ChartFact


def _context(system="vedic", division="D1"):
    context = {
        "available": True,
        "chart_id": "chart-test",
        "profile_id": "profile-test",
        "system": system,
        "division": division,
        "engine_version": "astroai-test/1.2.0",
        "calculated_at": "2026-01-01T00:00:00+00:00",
        "birth_date": "1900-01-01",
        "birth_time": "12:00:00",
        "birthplace": "Private place",
        "latitude": 10.0,
        "longitude": 20.0,
        "planets": [{
            "name": "Moon", "longitude": 44.2, "sign": "Vrishabha", "house": 2,
            "retrograde": False,
            "nakshatra": {"name": "Rohini", "lord": "Moon", "pada": 3, "remaining_fraction": 0.4},
            "d9": {"rashi": "Karka", "rashi_index": 3, "longitude": 100.0},
        }],
        "ascendant": {"longitude": 18.0, "rashi": "Mesha", "nakshatra": "Ashwini", "pada": 2},
        "houses": [{"number": 2, "cusp_longitude": 30.0, "rashi": "Vrishabha"}],
        "vimshottari_dasha": {
            "year_convention": "savana_360_day",
            "starting_nakshatra": "Rohini",
            "starting_lord": "Moon",
            "birth_balance_days": 10.5,
            "mahadashas": [{"lord": "Moon", "start": "2026-01-01T00:00:00+00:00", "end": "2036-01-01T00:00:00+00:00"}],
            "antardashas": [{"lord": "Moon", "sub_lord": "Mars", "start": "2026-01-01", "end": "2026-11-01"}],
        },
        "aspects": [],
    }
    if system == "western":
        context["planets"] = [{"name": "Mars", "longitude": 91.0, "sign": "Cancer", "house": 7, "retrograde": True}]
        context["midheaven"] = {"longitude": 280.0, "sign": "Capricorn"}
        context["houses"] = [{"number": 7, "cusp_longitude": 90.0, "sign": "Cancer"}]
        context["aspects"] = [{"planet_a": "Sun", "planet_b": "Mars", "aspect": "square", "orb": 1.5, "motion": "applying"}]
        context.pop("vimshottari_dasha")
    if system == "vedic" and division == "D9":
        context["planets"] = [{
            "name": "Moon", "longitude": 100.0, "sign": "Karka", "house": 4, "retrograde": False,
            "d9": {"rashi": "Karka", "rashi_index": 3, "longitude": 100.0},
        }]
        context["houses"] = [{"number": 4, "cusp_longitude": 90.0, "rashi": "Karka"}]
    return context


def _fact_map(facts):
    return {(fact.subject, fact.predicate): fact.value for fact in facts.facts}


def test_vedic_d1_facts_include_planet_nakshatra_pada_ascendant_and_dasha_without_private_data():
    context = _context()
    facts = chart_facts_from_context(context, expected_system="vedic", expected_division="D1")
    values = _fact_map(facts)
    assert facts.available
    assert facts.chart_id == "chart-test" and facts.profile_id == "profile-test"
    assert facts.calculation_engine_version == "astroai-test/1.2.0"
    assert facts.calculated_at is not None
    assert values[("Moon", "sign")] == "Vrishabha"
    assert values[("Moon", "retrograde")] is False
    assert values[("Moon", "nakshatra.name")] == "Rohini"
    assert values[("Moon", "nakshatra.pada")] == 3
    assert values[("ascendant", "pada")] == 2
    assert values[("Vimshottari", "year_convention")] == "savana_360_day"
    assert values[("Dasha:Moon", "end")] == "2036-01-01T00:00:00+00:00"
    serialized = str(facts.model_dump())
    for private in ("birth_date", "birth_time", "birthplace", "latitude", "Private place"):
        assert private not in serialized
    assert all(fact.source_chart_id == "chart-test" and fact.system is AstrologySystem.VEDIC for fact in facts.facts)
    assert all(fact.provenance.startswith("saved_chart:chart-test:") for fact in facts.facts)


def test_vedic_d9_facts_use_saved_d9_placements_and_do_not_label_them_nakshatra():
    facts = chart_facts_from_context(_context(division="D9"), expected_system="vedic", expected_division="D9")
    values = _fact_map(facts)
    assert facts.available and facts.division == "D9"
    assert values[("Moon", "sign")] == "Karka"
    assert values[("Moon", "d9.rashi")] == "Karka"
    assert values[("Moon", "d9.longitude")] == 100.0
    assert not any(fact.predicate.startswith("nakshatra.") for fact in facts.facts)


def test_western_facts_include_planets_houses_aspects_and_retrograde():
    facts = chart_facts_from_context(_context("western", "W"), expected_system="western")
    values = _fact_map(facts)
    assert facts.available
    assert values[("Mars", "retrograde")] is True
    assert values[("Mars", "house")] == 7
    assert values[("House:7", "sign")] == "Cancer"
    assert values[("Aspect:Sun/Mars", "aspect")] == "square"
    assert values[("Aspect:Sun/Mars", "motion")] == "applying"
    assert values[("midheaven", "sign")] == "Capricorn"


def test_missing_optional_facts_stay_missing_and_incomplete_chart_is_unavailable():
    context = _context("western", "W")
    context.pop("houses")
    context.pop("aspects")
    facts = chart_facts_from_context(context)
    assert facts.available
    assert not any(fact.subject.startswith("House:") or fact.subject.startswith("Aspect:") for fact in facts.facts)
    context["available"] = False
    unavailable = chart_facts_from_context(context)
    assert not unavailable.available
    assert "saved_chart_unavailable" in unavailable.missing
    assert unavailable.facts == ()


@pytest.mark.parametrize(
    ("context", "kwargs", "reason"),
    [
        (_context("western", "W"), {"expected_system": "vedic"}, "wrong_astrology_system"),
        (_context("vedic", "D1"), {"expected_division": "D9"}, "wrong_chart_division"),
        (_context("vedic", "D8"), {}, "unsupported_vedic_division"),
        ({**_context(), "chart_id": None}, {}, "saved_chart_identity_missing"),
        ({**_context(), "planets": []}, {}, "planetary_placements_missing"),
    ],
)
def test_wrong_system_division_and_incomplete_required_data_are_unavailable(context, kwargs, reason):
    facts = chart_facts_from_context(context, **kwargs)
    assert not facts.available
    assert reason in facts.missing


def test_invalid_fact_values_are_omitted_and_reported_without_coercion():
    context = _context()
    context["planets"][0]["longitude"] = "44.2"
    context["planets"][0]["retrograde"] = "false"
    facts = chart_facts_from_context(context)
    assert facts.available
    assert not any(fact.subject == "Moon" and fact.predicate == "longitude" for fact in facts.facts)
    assert not any(fact.subject == "Moon" and fact.predicate == "retrograde" for fact in facts.facts)
    assert {"Moon.longitude", "Moon.retrograde"} <= set(facts.missing)
    with pytest.raises(ValueError):
        ChartFact(subject="Moon", predicate="longitude", value={"degrees": 44.2}, system="vedic", source_chart_id="chart", provenance="saved")


def test_saved_chart_adapter_reuses_owner_scoped_lookup_and_rejects_other_user_context():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    owner = User(email="owner-facts@example.com", password_hash="unused")
    other = User(email="other-facts@example.com", password_hash="unused")
    profile = BirthProfile(
        owner_id=owner.id, display_name="Private", relationship="self", birth_date=date(1990, 1, 1),
        birth_time=time(12), time_accuracy="exact", birthplace="Private City", country="Private Country",
        latitude=10, longitude=20, timezone="Asia/Kolkata",
    )
    with session_factory() as session:
        session.add_all([owner, other])
        session.flush()
        profile.owner_id = owner.id
        session.add(profile)
        session.flush()
        chart = BirthChart(profile_id=profile.id, system="vedic", division="D1", status="complete", unavailable_reason="", config={})
        session.add(chart)
        session.flush()
        session.add(ChartCalculationRun(
            chart_id=chart.id, run_number=1, status="complete", config={},
            input_snapshot={"birth_date": "1990-01-01", "birthplace": "Private City"},
            result={"calculation_system": "vedic", "planets": [{"name": "Moon", "longitude": 44.2, "rashi": "Vrishabha"}]},
            engine_version="fixture-engine",
        ))
        session.flush()
        chat = ChatSession(user_id=owner.id, profile_id=profile.id, chart_id=chart.id, astrology_system="vedic", language="en")
        session.add(chat)
        session.commit()
        own_facts = load_session_chart_facts(session, chat, owner)
        foreign_facts = load_session_chart_facts(session, chat, other)
        assert own_facts.available
        assert own_facts.chart_id == str(chart.id)
        assert not foreign_facts.available
        assert "saved_chart_unavailable" in foreign_facts.missing
        assert foreign_facts.facts == ()
    engine.dispose()
