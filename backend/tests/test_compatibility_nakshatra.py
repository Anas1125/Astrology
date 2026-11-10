import pytest

from app.services.astrology.compatibility.gana import (
    DEVA,
    MANUSHYA,
    RAKSHASA,
    GANA_BY_NAKSHATRA,
    get_gana,
)
from app.services.astrology.compatibility.gana_scoring import (
    calculate_gana_compatibility,
    calculate_gana_score,
)
from app.services.astrology.compatibility.graha_maitri import (
    FRIEND,
    NEUTRAL,
    ENEMY,
    RASHI_LORDS,
    PLANETARY_RELATIONSHIPS,
    get_rashi_lord,
    get_planetary_relationship,
)
from app.services.astrology.compatibility.nadi import (
    ADI,
    MADHYA,
    ANTYA,
    NADI_BY_NAKSHATRA,
    get_nadi,
)
from app.services.astrology.compatibility.nadi_scoring import (
    calculate_nadi_score,
    calculate_nadi_compatibility,
)
from app.services.astrology.compatibility.nakshatra import (
    calculate_moon_nakshatra,
)
from app.services.astrology.compatibility.nakshatra_data import (
    get_all_nakshatras,
    get_nakshatra_metadata,
)
from app.services.astrology.compatibility.tara import (
    calculate_tara_direction,
    calculate_tara_score,
    calculate_tara_compatibility,
)

def test_catalogue_contains_27_nakshatras():
    assert len(get_all_nakshatras()) == 27


def test_first_nakshatra():
    result = get_nakshatra_metadata(1)

    assert result["name"] == "Ashwini"
    assert result["lord"] == "Ketu"


def test_ninth_nakshatra():
    result = get_nakshatra_metadata(9)

    assert result["name"] == "Ashlesha"
    assert result["lord"] == "Mercury"


def test_tenth_nakshatra_restarts_lord_sequence():
    result = get_nakshatra_metadata(10)

    assert result["name"] == "Magha"
    assert result["lord"] == "Ketu"


def test_last_nakshatra():
    result = get_nakshatra_metadata(27)

    assert result["name"] == "Revati"
    assert result["lord"] == "Mercury"


@pytest.mark.parametrize("index", [0, 28, -1, 100])
def test_invalid_nakshatra_index(index):
    with pytest.raises(ValueError):
        get_nakshatra_metadata(index)


@pytest.mark.parametrize("index", [1.5, "1", True])
def test_non_integer_nakshatra_index(index):
    with pytest.raises(ValueError):
        get_nakshatra_metadata(index)


def test_calculate_ashwini_nakshatra():
    result = calculate_moon_nakshatra(0.0)

    assert result["index"] == 1
    assert result["name"] == "Ashwini"
    assert result["pada"] == 1
    assert result["lord"] == "Ketu"


def test_calculate_bharani_nakshatra():
    result = calculate_moon_nakshatra(14.0)

    assert result["index"] == 2
    assert result["name"] == "Bharani"
    assert result["lord"] == "Venus"


def test_calculate_revati_nakshatra():
    result = calculate_moon_nakshatra(359.0)

    assert result["index"] == 27
    assert result["name"] == "Revati"
    assert result["lord"] == "Mercury"


def test_nakshatra_has_four_padas():
    result = calculate_moon_nakshatra(10.0)

    assert 1 <= result["pada"] <= 4


def test_gana_mapping_contains_all_27_nakshatras():
    assert len(GANA_BY_NAKSHATRA) == 27


def test_each_gana_has_nine_nakshatras():
    assert list(GANA_BY_NAKSHATRA.values()).count(DEVA) == 9
    assert list(GANA_BY_NAKSHATRA.values()).count(MANUSHYA) == 9
    assert list(GANA_BY_NAKSHATRA.values()).count(RAKSHASA) == 9


def test_gana_examples():
    assert get_gana(1) == DEVA
    assert get_gana(2) == MANUSHYA
    assert get_gana(3) == RAKSHASA
    assert get_gana(27) == DEVA


def test_gana_rejects_invalid_index():
    import pytest

    for value in (0, 28, -1, 1.5, "1", True):
        with pytest.raises(ValueError):
            get_gana(value)

def test_same_gana_scores_six():
    for gana in (DEVA, MANUSHYA, RAKSHASA):
        result = calculate_gana_score(gana, gana)
        assert result["score"] == 6


def test_deva_bride_manushya_groom_scores_six():
    result = calculate_gana_score(DEVA, MANUSHYA)
    assert result["score"] == 6


def test_manushya_bride_deva_groom_scores_five():
    result = calculate_gana_score(MANUSHYA, DEVA)
    assert result["score"] == 5


def test_rakshasa_bride_deva_groom_scores_one():
    result = calculate_gana_score(RAKSHASA, DEVA)
    assert result["score"] == 1


def test_invalid_gana_is_rejected():
    import pytest

    with pytest.raises(ValueError):
        calculate_gana_score("Invalid", DEVA)


def test_result_includes_scoring_convention():
    result = calculate_gana_score(DEVA, DEVA)

    assert result["maximum"] == 6
    assert result["convention"] == "saravali_maitreya_directional"


def test_gana_compatibility_from_moon_longitudes():
    result = calculate_gana_compatibility(0.0, 14.0)

    assert result["bride_nakshatra"]["name"] == "Ashwini"
    assert result["groom_nakshatra"]["name"] == "Bharani"
    assert result["bride_gana"] == DEVA
    assert result["groom_gana"] == MANUSHYA
    assert result["score"] == 6


def test_nadi_mapping_contains_all_27_nakshatras():
    assert len(NADI_BY_NAKSHATRA) == 27


def test_each_nadi_has_nine_nakshatras():
    values = list(NADI_BY_NAKSHATRA.values())

    assert values.count(ADI) == 9
    assert values.count(MADHYA) == 9
    assert values.count(ANTYA) == 9


def test_nadi_examples():
    assert get_nadi(1) == ADI
    assert get_nadi(2) == MADHYA
    assert get_nadi(3) == ANTYA
    assert get_nadi(27) == ANTYA


def test_nadi_rejects_invalid_index():
    import pytest

    for value in (0, 28, -1, 1.5, "1", True):
        with pytest.raises(ValueError):
            get_nadi(value)

def test_same_nadi_scores_zero():
    for nadi in (ADI, MADHYA, ANTYA):
        result = calculate_nadi_score(nadi, nadi)
        assert result["score"] == 0


def test_different_nadi_scores_eight():
    result = calculate_nadi_score(ADI, MADHYA)
    assert result["score"] == 8


def test_nadi_score_is_symmetric():
    first = calculate_nadi_score(ADI, ANTYA)
    second = calculate_nadi_score(ANTYA, ADI)

    assert first["score"] == second["score"] == 8


def test_invalid_nadi_is_rejected():
    import pytest

    with pytest.raises(ValueError):
        calculate_nadi_score("Invalid", ADI)


def test_nadi_result_has_correct_maximum():
    result = calculate_nadi_score(ADI, MADHYA)

    assert result["maximum"] == 8
    assert result["convention"] == "basic_nadi_koota"


def test_nadi_compatibility_from_moon_longitudes():
    result = calculate_nadi_compatibility(0.0, 14.0)

    assert result["bride_nakshatra"]["name"] == "Ashwini"
    assert result["groom_nakshatra"]["name"] == "Bharani"

    assert result["bride_nadi"] == ADI
    assert result["groom_nadi"] == MADHYA

    assert result["score"] == 8


def test_same_nakshatra_scores_three():
    result = calculate_tara_score(1, 1)

    assert result["score"] == 3


def test_ashwini_to_pushya_tara():
    result = calculate_tara_score(1, 8)

    assert result["bride_to_groom"]["tara_number"] == 8
    assert result["groom_to_bride"]["tara_number"] == 3
    assert result["score"] == 1.5


def test_favourable_tara_positions():
    for index in (1, 2, 4, 6, 8, 9):
        result = calculate_tara_direction(1, index)
        assert result["favourable"] is True


def test_unfavourable_tara_positions():
    for index in (3, 5, 7):
        result = calculate_tara_direction(1, index)
        assert result["favourable"] is False
        assert result["score"] == 0


def test_tara_wraps_after_revati():
    result = calculate_tara_direction(27, 1)

    assert result["count"] == 2
    assert result["tara_number"] == 2
    assert result["tara_name"] == "Sampat"


def test_tara_rejects_invalid_indexes():
    import pytest

    for value in (0, 28, -1, 1.5, "1", True):
        with pytest.raises(ValueError):
            calculate_tara_direction(value, 1)


def test_tara_score_never_exceeds_three():
    for bride in range(1, 28):
        for groom in range(1, 28):
            result = calculate_tara_score(bride, groom)
            assert 0 <= result["score"] <= 3


def test_tara_compatibility_from_moon_longitudes():
    result = calculate_tara_compatibility(0.0, 14.0)

    assert result["bride_nakshatra"]["name"] == "Ashwini"
    assert result["groom_nakshatra"]["name"] == "Bharani"
    assert result["score"] == 3.0


def test_all_twelve_rashis_have_lords():
    assert len(RASHI_LORDS) == 12


def test_rashi_lord_examples():
    assert get_rashi_lord(1) == "Mars"
    assert get_rashi_lord(2) == "Venus"
    assert get_rashi_lord(4) == "Moon"
    assert get_rashi_lord(10) == "Saturn"
    assert get_rashi_lord(12) == "Jupiter"


def test_invalid_rashi_index():
    import pytest

    for value in (0, 13, -1, 1.5, "1", True):
        with pytest.raises(ValueError):
            get_rashi_lord(value)


def test_planetary_relationship_examples():
    assert get_planetary_relationship("Sun", "Mars") == FRIEND
    assert get_planetary_relationship("Sun", "Mercury") == NEUTRAL
    assert get_planetary_relationship("Sun", "Saturn") == ENEMY


def test_planetary_friendship_is_directional():
    assert get_planetary_relationship("Mars", "Mercury") == ENEMY
    assert get_planetary_relationship("Mercury", "Mars") == NEUTRAL


def test_same_planet_is_friendly_to_itself():
    for planet in PLANETARY_RELATIONSHIPS:
        assert get_planetary_relationship(planet, planet) == FRIEND
