import pytest

from app.services.astrology.compatibility.ashtakoota import (
    ASHTAKOOTA_MAX_SCORE,
    ASHTAKOOTA_METHOD,
    calculate_ashtakoota,
)


def test_ashtakoota_returns_all_eight_kootas():
    result = calculate_ashtakoota(0.0, 14.0)

    assert result["completed_kootas"] == 8
    assert len(result["factors"]) == 8
    assert {factor["koota"] for factor in result["factors"]} == {
        "Varna",
        "Vashya",
        "Tara",
        "Yoni",
        "Graha Maitri",
        "Gana",
        "Bhakoot",
        "Nadi",
    }


def test_ashtakoota_total_matches_component_scores():
    result = calculate_ashtakoota(0.0, 14.0)

    assert result["total_score"] == sum(
        factor["score"] for factor in result["factors"]
    )
    assert result["maximum_score"] == ASHTAKOOTA_MAX_SCORE == 36


def test_ashtakoota_known_same_moon_sign_example():
    # Both longitudes are in Mesha; this is a calculation fixture,
    # not a claim that identical charts receive 36 points.
    result = calculate_ashtakoota(0.0, 14.0)

    scores = {factor["koota"]: factor["score"] for factor in result["factors"]}
    assert scores == {
        "Varna": 1,
        "Vashya": 2,
        "Tara": 3,
        "Yoni": 2,
        "Graha Maitri": 5,
        "Gana": 6,
        "Bhakoot": 7,
        "Nadi": 8,
    }
    assert result["total_score"] == 34


def test_all_factor_scores_stay_within_their_maximums():
    result = calculate_ashtakoota(0.0, 14.0)

    for factor in result["factors"]:
        assert 0 <= factor["score"] <= factor["maximum"]


def test_each_component_convention_is_exposed():
    result = calculate_ashtakoota(0.0, 14.0)

    assert set(result["conventions"]) == {
        factor["koota"] for factor in result["factors"]
    }
    assert all(result["conventions"].values())


def test_bhakoot_cancellation_is_not_assumed():
    result = calculate_ashtakoota(0.0, 35.0)

    assert result["bhakoot_cancellation"]["evaluated"] is False
    assert result["bhakoot_cancellation"]["status"] == "not_evaluated"


def test_no_automatic_compatibility_verdict_is_returned():
    result = calculate_ashtakoota(0.0, 14.0)

    assert result["method"] == ASHTAKOOTA_METHOD
    assert result["interpretation_status"] == "not_assigned"
    assert "compatibility_label" not in result


@pytest.mark.parametrize(
    "invalid",
    [float("nan"), float("inf"), -1, 361, "not-a-number", True],
)
def test_invalid_bride_longitude_is_rejected(invalid):
    with pytest.raises(ValueError):
        calculate_ashtakoota(invalid, 0.0)


@pytest.mark.parametrize(
    "invalid",
    [float("nan"), float("inf"), -1, 361, "not-a-number", True],
)
def test_invalid_groom_longitude_is_rejected(invalid):
    with pytest.raises(ValueError):
        calculate_ashtakoota(0.0, invalid)
