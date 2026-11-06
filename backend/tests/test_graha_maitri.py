import pytest

from app.services.astrology.compatibility.graha_maitri import (
    ENEMY,
    FRIEND,
    NEUTRAL,
    GRAHA_MAITRI_CONVENTION,
    PLANETARY_RELATIONSHIPS,
    RASHI_LORDS,
    calculate_graha_maitri_compatibility,
    calculate_graha_maitri_score,
    get_planetary_relationship,
    get_rashi_lord,
)


def test_all_twelve_rashis_have_lords():
    assert len(RASHI_LORDS) == 12


@pytest.mark.parametrize(
    ("index", "expected"),
    [(1, "Mars"), (2, "Venus"), (4, "Moon"), (10, "Saturn"), (12, "Jupiter")],
)
def test_rashi_lord_examples(index, expected):
    assert get_rashi_lord(index) == expected


@pytest.mark.parametrize("value", [0, 13, -1, 1.5, "1", True])
def test_invalid_rashi_index(value):
    with pytest.raises(ValueError):
        get_rashi_lord(value)


def test_natural_friendship_is_directional():
    assert get_planetary_relationship("Mars", "Mercury") == ENEMY
    assert get_planetary_relationship("Mercury", "Mars") == NEUTRAL


def test_same_planet_is_friendly_to_itself():
    for planet in PLANETARY_RELATIONSHIPS:
        assert get_planetary_relationship(planet, planet) == FRIEND


@pytest.mark.parametrize(
    ("first", "second", "expected_score"),
    [
        ("Sun", "Mars", 5),       # friend / friend
        ("Sun", "Mercury", 4),    # neutral / friend
        ("Mars", "Venus", 3),     # neutral / neutral
        ("Moon", "Mercury", 2),   # friend / enemy
        ("Mars", "Saturn", 1),    # neutral / enemy
        ("Sun", "Saturn", 0),     # enemy / enemy
    ],
)
def test_all_six_mutual_relationship_score_classes(first, second, expected_score):
    result = calculate_graha_maitri_score(first, second)
    assert result["score"] == expected_score
    assert result["maximum"] == 5
    assert result["convention"] == GRAHA_MAITRI_CONVENTION


def test_score_is_order_independent_when_bride_and_groom_are_swapped():
    first = calculate_graha_maitri_score("Moon", "Mercury")
    second = calculate_graha_maitri_score("Mercury", "Moon")
    assert first["score"] == second["score"] == 2


def test_unknown_planets_are_rejected():
    with pytest.raises(ValueError):
        calculate_graha_maitri_score("Rahu", "Sun")


def test_moon_longitudes_in_same_rashi_use_same_lord():
    result = calculate_graha_maitri_compatibility(0.0, 29.9)
    assert result["bride_rashi"] == "Mesha"
    assert result["groom_rashi"] == "Mesha"
    assert result["bride_planet"] == result["groom_planet"] == "Mars"
    assert result["score"] == 5


def test_moon_longitudes_in_different_rashis():
    # 0° is Mesha (Mars); 35° is Vrishabha (Venus).
    result = calculate_graha_maitri_compatibility(0.0, 35.0)
    assert result["bride_rashi"] == "Mesha"
    assert result["groom_rashi"] == "Vrishabha"
    assert result["bride_planet"] == "Mars"
    assert result["groom_planet"] == "Venus"
    assert result["score"] == 3


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -1, 361, "12", True])
def test_invalid_moon_longitude_is_rejected(value):
    with pytest.raises(ValueError):
        calculate_graha_maitri_compatibility(value, 0.0)
