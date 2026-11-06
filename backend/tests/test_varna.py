import pytest

from app.services.astrology.compatibility.varna import (
    BRAHMIN,
    KSHATRIYA,
    VAISHYA,
    SHUDRA,
    VARNA_BY_RASHI,
    VARNA_CONVENTION,
    VARNA_RANKS,
    calculate_varna_compatibility,
    calculate_varna_score,
    get_varna,
)


def test_all_twelve_rashis_have_varna():
    assert len(VARNA_BY_RASHI) == 12


@pytest.mark.parametrize(
    ("rashi_index", "expected"),
    [
        (1, KSHATRIYA),   # Mesha
        (2, VAISHYA),     # Vrishabha
        (3, SHUDRA),      # Mithuna
        (4, BRAHMIN),     # Karka
        (5, KSHATRIYA),   # Simha
        (6, VAISHYA),     # Kanya
        (7, SHUDRA),      # Tula
        (8, BRAHMIN),     # Vrischika
        (9, KSHATRIYA),   # Dhanu
        (10, VAISHYA),    # Makara
        (11, SHUDRA),     # Kumbha
        (12, BRAHMIN),    # Meena
    ],
)
def test_rashi_varna_mapping(rashi_index, expected):
    assert get_varna(rashi_index) == expected


@pytest.mark.parametrize("value", [0, 13, -1, 1.5, "1", True])
def test_invalid_rashi_index_rejected(value):
    with pytest.raises(ValueError):
        get_varna(value)


@pytest.mark.parametrize(
    ("bride", "groom", "expected"),
    [
        (BRAHMIN, BRAHMIN, 1),
        (BRAHMIN, KSHATRIYA, 0),
        (BRAHMIN, VAISHYA, 0),
        (BRAHMIN, SHUDRA, 0),
        (KSHATRIYA, BRAHMIN, 1),
        (KSHATRIYA, KSHATRIYA, 1),
        (KSHATRIYA, VAISHYA, 0),
        (KSHATRIYA, SHUDRA, 0),
        (VAISHYA, BRAHMIN, 1),
        (VAISHYA, KSHATRIYA, 1),
        (VAISHYA, VAISHYA, 1),
        (VAISHYA, SHUDRA, 0),
        (SHUDRA, BRAHMIN, 1),
        (SHUDRA, KSHATRIYA, 1),
        (SHUDRA, VAISHYA, 1),
        (SHUDRA, SHUDRA, 1),
    ],
)
def test_varna_scoring_table(bride, groom, expected):
    result = calculate_varna_score(bride, groom)
    assert result["score"] == expected
    assert result["maximum"] == 1


def test_varna_scoring_is_directional():
    assert calculate_varna_score(BRAHMIN, SHUDRA)["score"] == 0
    assert calculate_varna_score(SHUDRA, BRAHMIN)["score"] == 1


def test_invalid_varna_rejected():
    with pytest.raises(ValueError):
        calculate_varna_score("Unknown", BRAHMIN)


def test_all_144_rashi_pairs_obey_rank_rule():
    for bride_index in range(1, 13):
        for groom_index in range(1, 13):
            bride_varna = get_varna(bride_index)
            groom_varna = get_varna(groom_index)
            result = calculate_varna_score(bride_varna, groom_varna)
            expected = int(
                VARNA_RANKS[groom_varna] >= VARNA_RANKS[bride_varna]
            )
            assert result["score"] == expected
            assert result["score"] in (0, 1)


def test_moon_longitude_integration():
    # 0 degrees = Mesha (Kshatriya); 35 degrees = Vrishabha (Vaishya).
    result = calculate_varna_compatibility(0.0, 35.0)

    assert result["bride_rashi"] == "Mesha"
    assert result["groom_rashi"] == "Vrishabha"
    assert result["bride_varna"] == KSHATRIYA
    assert result["groom_varna"] == VAISHYA
    assert result["score"] == 0
    assert result["convention"] == VARNA_CONVENTION


def test_360_degrees_wraps_to_first_rashi():
    result = calculate_varna_compatibility(360.0, 0.0)
    assert result["bride_rashi"] == "Mesha"
    assert result["bride_varna"] == KSHATRIYA


@pytest.mark.parametrize(
    "value",
    [float("nan"), float("inf"), -1, 361, "12", True],
)
def test_invalid_moon_longitude_rejected(value):
    with pytest.raises(ValueError):
        calculate_varna_compatibility(value, 0.0)
