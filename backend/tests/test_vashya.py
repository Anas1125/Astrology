import pytest

from app.services.astrology.compatibility.vashya import (
    CHATASHPADA,
    MANAVA,
    JALACHARA,
    VANACHARA,
    KEETA,
    VASHYA_CONVENTION,
    VASHYA_SCORE_TABLE,
    calculate_vashya_compatibility,
    calculate_vashya_score,
    get_vashya,
)


@pytest.mark.parametrize(
    ("rashi_index", "degrees", "expected"),
    [
        (1, 0, CHATASHPADA),   # Mesha
        (2, 29.999, CHATASHPADA),
        (3, 10, MANAVA),        # Mithuna
        (4, 10, JALACHARA),     # Karka
        (5, 10, VANACHARA),     # Simha
        (6, 10, MANAVA),        # Kanya
        (7, 10, MANAVA),        # Tula
        (8, 10, KEETA),         # Vrischika
        (9, 14.999, MANAVA),    # First half Dhanu
        (9, 15, CHATASHPADA),   # Second half Dhanu
        (10, 14.999, CHATASHPADA),  # First half Makara
        (10, 15, JALACHARA),    # Second half Makara
        (11, 10, MANAVA),       # Kumbha
        (12, 10, JALACHARA),    # Meena
    ],
)
def test_vashya_group_mapping(rashi_index, degrees, expected):
    assert get_vashya(rashi_index, degrees) == expected


@pytest.mark.parametrize("rashi_index", [0, 13, -1, 1.5, "1", True])
def test_invalid_rashi_index_rejected(rashi_index):
    with pytest.raises(ValueError):
        get_vashya(rashi_index, 10)


@pytest.mark.parametrize(
    "degrees",
    [-0.1, 30, 30.1, float("nan"), float("inf"), "12", True],
)
def test_invalid_degrees_in_rashi_rejected(degrees):
    with pytest.raises(ValueError):
        get_vashya(1, degrees)


def test_complete_five_by_five_score_table():
    assert set(VASHYA_SCORE_TABLE) == {
        CHATASHPADA, MANAVA, JALACHARA, VANACHARA, KEETA
    }
    for bride_group, row in VASHYA_SCORE_TABLE.items():
        assert set(row) == {
            CHATASHPADA, MANAVA, JALACHARA, VANACHARA, KEETA
        }
        assert all(0 <= score <= 2 for score in row.values())


@pytest.mark.parametrize(
    ("bride", "groom", "expected"),
    [
        (CHATASHPADA, CHATASHPADA, 2),
        (CHATASHPADA, MANAVA, 1),
        (CHATASHPADA, JALACHARA, 1),
        (CHATASHPADA, VANACHARA, 1.5),
        (CHATASHPADA, KEETA, 1),
        (MANAVA, JALACHARA, 1.5),
        (MANAVA, VANACHARA, 0),
        (VANACHARA, CHATASHPADA, 0),
        (JALACHARA, VANACHARA, 1),
        (KEETA, VANACHARA, 0),
    ],
)
def test_directional_vashya_scores(bride, groom, expected):
    result = calculate_vashya_score(bride, groom)
    assert result["score"] == expected
    assert result["maximum"] == 2
    assert result["convention"] == VASHYA_CONVENTION


def test_vashya_scoring_is_directional():
    forward = calculate_vashya_score(CHATASHPADA, VANACHARA)
    reverse = calculate_vashya_score(VANACHARA, CHATASHPADA)
    assert forward["score"] == 1.5
    assert reverse["score"] == 0


def test_invalid_vashya_group_rejected():
    with pytest.raises(ValueError):
        calculate_vashya_score("Unknown", CHATASHPADA)


def test_moon_longitude_integration_same_group():
    # Mesha and Vrishabha are both Chatushpada.
    result = calculate_vashya_compatibility(0.0, 35.0)
    assert result["bride_vashya"] == CHATASHPADA
    assert result["groom_vashya"] == CHATASHPADA
    assert result["score"] == 2


def test_moon_longitude_integration_directional_example():
    # Mesha = Chatushpada; Simha = Vanachara.
    result = calculate_vashya_compatibility(0.0, 125.0)
    assert result["bride_rashi"] == "Mesha"
    assert result["groom_rashi"] == "Simha"
    assert result["score"] == 1.5


def test_longitude_360_wraps_to_mesha():
    result = calculate_vashya_compatibility(360.0, 0.0)
    assert result["bride_rashi"] == "Mesha"
    assert result["bride_vashya"] == CHATASHPADA


@pytest.mark.parametrize(
    "value",
    [float("nan"), float("inf"), -1, 361, "12", True],
)
def test_invalid_moon_longitude_rejected(value):
    with pytest.raises(ValueError):
        calculate_vashya_compatibility(value, 0.0)
