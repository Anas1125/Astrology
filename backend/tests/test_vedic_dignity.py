import pytest

from app.services.astrology.vedic_dignity import (
    CLASSICAL_PLANETS,
    NATURAL_RELATIONSHIPS,
    DIGNITY_RULESET_ID,
    DignityInputError,
    analyze_vedic_d1_dignity,
)


def _chart(placements):
    planets = []
    for name, (sign, degree) in placements.items():
        # Sign ordering follows the Vedic engine's RASHIS tuple.
        from app.services.astrology.sweph import RASHIS
        longitude = RASHIS.index(sign) * 30.0 + degree
        planets.append({"name": name, "longitude": longitude, "rashi": sign, "rashi_index": RASHIS.index(sign)})
    return {"calculation_system": "vedic", "division": "D1", "configuration": {"ayanamsa": "lahiri"}, "planets": planets}


def _baseline():
    return {name: ("Mesha", 1.0) for name in CLASSICAL_PLANETS}


@pytest.mark.parametrize("planet", CLASSICAL_PLANETS)
def test_exaltation_and_debilitation_signs_and_deep_degrees(planet):
    expected_exaltation = {
        "Sun": ("Mesha", 10.0), "Moon": ("Vrishabha", 3.0), "Mars": ("Makara", 28.0),
        "Mercury": ("Kanya", 15.0), "Jupiter": ("Karka", 5.0), "Venus": ("Meena", 27.0),
        "Saturn": ("Tula", 20.0),
    }
    expected_debilitation = {
        "Sun": ("Tula", 10.0), "Moon": ("Vrischika", 3.0), "Mars": ("Karka", 28.0),
        "Mercury": ("Meena", 15.0), "Jupiter": ("Makara", 5.0), "Venus": ("Kanya", 27.0),
        "Saturn": ("Mesha", 20.0),
    }
    placements = _baseline()
    sign, degree = expected_exaltation[planet]
    placements[planet] = sign, degree
    row = next(item for item in analyze_vedic_d1_dignity(_chart(placements), chart_id="c", profile_id="p")["planets"] if item["planet"] == planet)
    assert row["dignity"] == ("moolatrikona" if planet in {"Moon", "Mercury"} else "exalted")
    assert row["is_at_deep_exaltation_degree"] is True

    sign, degree = expected_debilitation[planet]
    placements[planet] = sign, degree
    row = next(item for item in analyze_vedic_d1_dignity(_chart(placements), chart_id="c", profile_id="p")["planets"] if item["planet"] == planet)
    assert row["dignity"] == "debilitated"
    assert row["is_at_deep_debilitation_degree"] is True


@pytest.mark.parametrize("planet", CLASSICAL_PLANETS)
def test_moolatrikona_inclusive_start_and_exclusive_end(planet):
    expected = {
        "Sun": ("Simha", 0.0, 20.0), "Moon": ("Vrishabha", 3.0, 30.0),
        "Mars": ("Mesha", 0.0, 12.0), "Mercury": ("Kanya", 15.0, 20.0),
        "Jupiter": ("Dhanu", 0.0, 10.0), "Venus": ("Tula", 0.0, 15.0),
        "Saturn": ("Kumbha", 0.0, 20.0),
    }
    placements = _baseline()
    sign, start, end = expected[planet]
    placements[planet] = sign, start
    row = next(item for item in analyze_vedic_d1_dignity(_chart(placements), chart_id="c", profile_id="p")["planets"] if item["planet"] == planet)
    assert row["dignity"] == "moolatrikona"
    assert row["is_moolatrikona"] is True
    if end == 30.0:
        from app.services.astrology.sweph import RASHIS
        placements[planet] = RASHIS[(RASHIS.index(sign) + 1) % 12], 0.0
    else:
        placements[planet] = sign, end
    row = next(item for item in analyze_vedic_d1_dignity(_chart(placements), chart_id="c", profile_id="p")["planets"] if item["planet"] == planet)
    assert row["is_moolatrikona"] is False


@pytest.mark.parametrize("planet,sign", [("Sun", "Simha"), ("Moon", "Karka"), ("Mars", "Vrischika"), ("Mercury", "Mithuna"), ("Jupiter", "Meena"), ("Venus", "Vrishabha"), ("Saturn", "Makara")])
def test_own_sign_classification(planet, sign):
    placements = _baseline()
    placements[planet] = sign, 25.0
    result = analyze_vedic_d1_dignity(_chart(placements), chart_id="chart-id", profile_id="profile-id")
    row = next(item for item in result["planets"] if item["planet"] == planet)
    assert row["dignity"] == "own_sign"
    assert row["relationship_to_sign_lord"] == "self"


def test_permanent_relationship_table_has_friend_neutral_and_enemy_and_is_chart_independent():
    assert NATURAL_RELATIONSHIPS["Sun"]["Mars"] == "friend"
    assert NATURAL_RELATIONSHIPS["Sun"]["Mercury"] == "neutral"
    assert NATURAL_RELATIONSHIPS["Sun"]["Venus"] == "enemy"
    assert NATURAL_RELATIONSHIPS["Moon"]["Saturn"] == "neutral"
    assert all(NATURAL_RELATIONSHIPS[p][p] == "self" for p in CLASSICAL_PLANETS)


def test_friend_neutral_enemy_sign_classifications_and_provenance():
    placements = _baseline()
    placements.update({"Sun": ("Karka", 11), "Moon": ("Simha", 11), "Mars": ("Mithuna", 11)})
    result = analyze_vedic_d1_dignity(_chart(placements), chart_id="chart-id", profile_id="profile-id")
    rows = {item["planet"]: item for item in result["planets"]}
    assert rows["Sun"]["dignity"] == "friend_sign"  # Cancer lord is a natural friend of Sun.
    assert rows["Moon"]["dignity"] == "friend_sign"  # Leo lord is a natural friend of Moon.
    assert rows["Mars"]["dignity"] == "enemy_sign"  # Gemini lord is a natural enemy of Mars.
    placements["Sun"] = ("Mithuna", 11)
    rows = {item["planet"]: item for item in analyze_vedic_d1_dignity(_chart(placements), chart_id="c", profile_id="p")["planets"]}
    assert rows["Sun"]["dignity"] == "neutral_sign"
    assert result["status"] == "provisional"
    assert result["ruleset_id"] == DIGNITY_RULESET_ID
    assert result["chart_id"] == "chart-id" and result["profile_id"] == "profile-id"
    assert result["excluded_planets"] == ["Rahu", "Ketu"]
    assert result["shadbala"]["status"] == "unavailable"


@pytest.mark.parametrize("mutate", ["missing", "duplicate", "invalid", "wrong_system", "wrong_division", "conflicting_sign"])
def test_invalid_or_incomplete_chart_is_rejected(mutate):
    chart = _chart(_baseline())
    if mutate == "missing":
        chart["planets"] = [p for p in chart["planets"] if p["name"] != "Venus"]
    elif mutate == "duplicate":
        chart["planets"].append(chart["planets"][0])
    elif mutate == "invalid":
        chart["planets"][0]["longitude"] = float("nan")
    elif mutate == "wrong_system":
        chart["calculation_system"] = "western"
    elif mutate == "wrong_division":
        chart["division"] = "D9"
    else:
        chart["planets"][0]["rashi"] = "Meena"
    with pytest.raises(DignityInputError):
        analyze_vedic_d1_dignity(chart, chart_id="c", profile_id="p")


def test_nodes_and_outer_planets_are_ignored_without_dignity_classifications():
    chart = _chart(_baseline())
    chart["planets"].extend([{"name": "Rahu", "longitude": 15}, {"name": "Ketu", "longitude": 195}, {"name": "Uranus", "longitude": 20}])
    result = analyze_vedic_d1_dignity(chart, chart_id="c", profile_id="p")
    assert {row["planet"] for row in result["planets"]} == set(CLASSICAL_PLANETS)
    assert all(row["planet"] not in {"Rahu", "Ketu"} for row in result["planets"])
