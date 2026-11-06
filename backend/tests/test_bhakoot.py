import pytest

from app.services.astrology.compatibility.bhakoot import (
    BHAKOOT_CONVENTION,
    BHAKOOT_DOSHA_PAIRS,
    calculate_bhakoot_compatibility,
    calculate_bhakoot_score,
)


@pytest.mark.parametrize(
    ("bride", "groom", "relationship", "expected_score", "dosha_type"),
    [
        (1, 1, "1/1", 7, None),      # same sign
        (1, 8, "6/8", 0, "Shadashtak (6/8)"),
        (1, 2, "2/12", 0, "Dwidwadash (2/12)"),
        (1, 5, "5/9", 0, "Nav Pancham (5/9)"),
        (1, 3, "3/11", 7, None),
        (1, 4, "4/10", 7, None),
        (1, 7, "7/7", 7, None),
        (12, 1, "2/12", 0, "Dwidwadash (2/12)"),
        (5, 9, "5/9", 0, "Nav Pancham (5/9)"),
        (6, 1, "6/8", 0, "Shadashtak (6/8)"),
    ],
)
def test_bhakoot_base_score(bride, groom, relationship, expected_score, dosha_type):
    result = calculate_bhakoot_score(bride, groom)
    assert result["relationship"] == relationship
    assert result["score"] == expected_score
    assert result["maximum"] == 7
    assert result["dosha"] is (dosha_type is not None)
    assert result["dosha_type"] == dosha_type


def test_bhakoot_relationship_is_symmetric():
    for bride in range(1, 13):
        for groom in range(1, 13):
            forward = calculate_bhakoot_score(bride, groom)
            reverse = calculate_bhakoot_score(groom, bride)
            assert forward["score"] == reverse["score"]
            assert forward["relationship"] == reverse["relationship"]
            assert forward["dosha"] == reverse["dosha"]


def test_all_twelve_by_twelve_combinations_have_valid_scores():
    for bride in range(1, 13):
        for groom in range(1, 13):
            result = calculate_bhakoot_score(bride, groom)
            assert result["score"] in (0, 7)
            assert result["maximum"] == 7


def test_dosha_cancellation_is_not_silently_applied():
    result = calculate_bhakoot_score(1, 2)
    assert result["dosha"] is True
    assert result["score"] == 0
    assert result["cancellation_evaluated"] is False
    assert result["cancellation_status"] == "not_evaluated"


def test_result_records_convention():
    result = calculate_bhakoot_score(1, 1)
    assert result["convention"] == BHAKOOT_CONVENTION


@pytest.mark.parametrize("value", [0, 13, -1, 1.5, "1", True])
def test_invalid_rashi_index_rejected(value):
    with pytest.raises(ValueError):
        calculate_bhakoot_score(value, 1)


def test_moon_longitude_integration_aries_and_taurus():
    result = calculate_bhakoot_compatibility(0.0, 35.0)
    assert result["bride_rashi"] == "Mesha"
    assert result["groom_rashi"] == "Vrishabha"
    assert result["relationship"] == "2/12"
    assert result["dosha"] is True
    assert result["score"] == 0


def test_moon_longitude_integration_aries_and_gemini():
    result = calculate_bhakoot_compatibility(0.0, 65.0)
    assert result["bride_rashi"] == "Mesha"
    assert result["groom_rashi"] == "Mithuna"
    assert result["relationship"] == "3/11"
    assert result["dosha"] is False
    assert result["score"] == 7


def test_360_degrees_wraps_to_first_rashi():
    result = calculate_bhakoot_compatibility(360.0, 0.0)
    assert result["bride_rashi"] == "Mesha"
    assert result["relationship"] == "1/1"
    assert result["score"] == 7


@pytest.mark.parametrize(
    "value",
    [float("nan"), float("inf"), -1, 361, "12", True],
)
def test_invalid_moon_longitude_rejected(value):
    with pytest.raises(ValueError):
        calculate_bhakoot_compatibility(value, 0.0)
