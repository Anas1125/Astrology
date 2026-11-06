"""Gana Koota scoring using the selected directional table convention."""

from app.services.astrology.compatibility.gana import DEVA, MANUSHYA, RAKSHASA
from app.services.astrology.compatibility.nakshatra import calculate_moon_nakshatra
from app.services.astrology.compatibility.gana import get_gana

GANA_MAX_SCORE = 6

# Rows: bride's Gana; columns: groom's Gana.
GANA_SCORE_TABLE = {
    DEVA: {DEVA: 6, MANUSHYA: 6, RAKSHASA: 0},
    MANUSHYA: {DEVA: 5, MANUSHYA: 6, RAKSHASA: 0},
    RAKSHASA: {DEVA: 1, MANUSHYA: 0, RAKSHASA: 6},
}


def calculate_gana_score(bride_gana: str, groom_gana: str) -> dict:
    if bride_gana not in GANA_SCORE_TABLE:
        raise ValueError("Invalid bride Gana")
    if groom_gana not in GANA_SCORE_TABLE:
        raise ValueError("Invalid groom Gana")
    return {
        "koota": "Gana",
        "bride_gana": bride_gana,
        "groom_gana": groom_gana,
        "score": GANA_SCORE_TABLE[bride_gana][groom_gana],
        "maximum": GANA_MAX_SCORE,
        "convention": "saravali_maitreya_directional",
    }


def calculate_gana_compatibility(
    bride_moon_longitude: float, groom_moon_longitude: float
) -> dict:
    bride_nakshatra = calculate_moon_nakshatra(bride_moon_longitude)
    groom_nakshatra = calculate_moon_nakshatra(groom_moon_longitude)
    bride_gana = get_gana(bride_nakshatra["index"])
    groom_gana = get_gana(groom_nakshatra["index"])
    result = calculate_gana_score(bride_gana, groom_gana)
    return {
        **result,
        "bride_nakshatra": bride_nakshatra,
        "groom_nakshatra": groom_nakshatra,
    }
