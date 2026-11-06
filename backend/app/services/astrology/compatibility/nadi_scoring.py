"""Basic Nadi Koota scoring."""

from app.services.astrology.compatibility.nadi import ADI, MADHYA, ANTYA, get_nadi
from app.services.astrology.compatibility.nakshatra import calculate_moon_nakshatra

NADI_MAX_SCORE = 8
VALID_NADIS = {ADI, MADHYA, ANTYA}


def calculate_nadi_score(bride_nadi: str, groom_nadi: str) -> dict:
    if bride_nadi not in VALID_NADIS:
        raise ValueError("Invalid bride Nadi")
    if groom_nadi not in VALID_NADIS:
        raise ValueError("Invalid groom Nadi")
    return {
        "koota": "Nadi",
        "bride_nadi": bride_nadi,
        "groom_nadi": groom_nadi,
        "score": NADI_MAX_SCORE if bride_nadi != groom_nadi else 0,
        "maximum": NADI_MAX_SCORE,
        "convention": "basic_nadi_koota",
    }


def calculate_nadi_compatibility(
    bride_moon_longitude: float, groom_moon_longitude: float
) -> dict:
    bride_nakshatra = calculate_moon_nakshatra(bride_moon_longitude)
    groom_nakshatra = calculate_moon_nakshatra(groom_moon_longitude)
    bride_nadi = get_nadi(bride_nakshatra["index"])
    groom_nadi = get_nadi(groom_nakshatra["index"])
    result = calculate_nadi_score(bride_nadi, groom_nadi)
    return {
        **result,
        "bride_nakshatra": bride_nakshatra,
        "groom_nakshatra": groom_nakshatra,
    }
