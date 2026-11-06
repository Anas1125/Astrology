import pytest

from app.services.astrology.compatibility.yoni import (
    YONI_BY_NAKSHATRA,
    YONI_LABELS,
    YONI_ORDER,
    YONI_SCORE_TABLE,
    YONI_CONVENTION,
    calculate_yoni_compatibility,
    calculate_yoni_score,
    get_yoni,
)


def test_mapping_contains_all_27_nakshatras():
    assert len(YONI_BY_NAKSHATRA) == 27


def test_mapping_contains_14_animal_types_and_27_sex_variants():
    assert len(set(YONI_BY_NAKSHATRA.values())) == 27
    assert len(YONI_LABELS) == 27


@pytest.mark.parametrize(
    ("index", "expected"),
    [
        (1, "horse_male"),
        (2, "elephant_male"),
        (3, "sheep_female"),
        (4, "serpent_male"),
        (5, "serpent_female"),
        (6, "dog_female"),
        (7, "cat_female"),
        (8, "sheep_male"),
        (9, "cat_male"),
        (10, "rat_male"),
        (11, "rat_female"),
        (12, "cow_male"),
        (13, "buffalo_female"),
        (14, "tiger_female"),
        (15, "buffalo_male"),
        (16, "tiger_male"),
        (17, "deer_female"),
        (18, "deer_male"),
        (19, "dog_male"),
        (20, "monkey_male"),
        (21, "mongoose_male"),
        (22, "monkey_female"),
        (23, "lion_female"),
        (24, "horse_female"),
        (25, "lion_male"),
        (26, "cow_female"),
        (27, "elephant_female"),
    ],
)
def test_nakshatra_yoni_assignment(index, expected):
    assert get_yoni(index) == expected


@pytest.mark.parametrize("value", [0, 28, -1, 1.5, "1", True])
def test_invalid_nakshatra_index_rejected(value):
    with pytest.raises(ValueError):
        get_yoni(value)


def test_score_matrix_is_27_by_27():
    assert len(YONI_SCORE_TABLE) == 27
    assert set(YONI_SCORE_TABLE) == set(YONI_ORDER)
    for row in YONI_SCORE_TABLE.values():
        assert set(row) == set(YONI_ORDER)
        assert len(row) == 27
        assert all(score in (0, 1, 2, 3, 4) for score in row.values())


def test_score_matrix_is_symmetric():
    for first in YONI_ORDER:
        for second in YONI_ORDER:
            assert (
                YONI_SCORE_TABLE[first][second]
                == YONI_SCORE_TABLE[second][first]
            )


def test_same_yoni_variant_scores_four():
    for yoni in YONI_ORDER:
        result = calculate_yoni_score(yoni, yoni)
        assert result["score"] == 4
        assert result["maximum"] == 4


def test_same_animal_opposite_sex_scores_four():
    assert calculate_yoni_score("horse_male", "horse_female")["score"] == 4
    assert calculate_yoni_score("elephant_male", "elephant_female")["score"] == 4


def test_known_enemy_pairs_score_zero():
    pairs = [
        ("horse_male", "buffalo_female"),
        ("elephant_male", "lion_female"),
        ("sheep_female", "monkey_male"),
        ("serpent_male", "mongoose_male"),
        ("dog_female", "deer_female"),
        ("cat_female", "rat_male"),
        ("cow_male", "tiger_female"),
    ]
    for first, second in pairs:
        assert calculate_yoni_score(first, second)["score"] == 0


def test_known_neutral_and_friendly_pairs_from_reference_table():
    assert calculate_yoni_score("horse_male", "elephant_male")["score"] == 2
    assert calculate_yoni_score("horse_male", "serpent_male")["score"] == 2
    assert calculate_yoni_score("horse_male", "deer_female")["score"] == 3


def test_invalid_yoni_rejected():
    with pytest.raises(ValueError):
        calculate_yoni_score("unknown_yoni", "horse_male")


def test_result_identifies_scoring_convention():
    result = calculate_yoni_score("horse_male", "horse_female")
    assert result["convention"] == YONI_CONVENTION


def test_moon_longitude_integration():
    # 0° and 360° both normalize to Ashwini (Horse male).
    result = calculate_yoni_compatibility(0.0, 360.0)
    assert result["bride_nakshatra"]["name"] == "Ashwini"
    assert result["groom_nakshatra"]["name"] == "Ashwini"
    assert result["bride_yoni"] == "horse_male"
    assert result["groom_yoni"] == "horse_male"
    assert result["score"] == 4


def test_ashwini_and_bharani_integration():
    result = calculate_yoni_compatibility(0.0, 14.0)
    assert result["bride_yoni"] == "horse_male"
    assert result["groom_yoni"] == "elephant_male"
    assert result["score"] == 2
