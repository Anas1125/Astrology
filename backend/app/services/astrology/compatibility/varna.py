"""Varna Koota based on the D1 sidereal Moon sign.

Convention: the Moon-sign classifications and groom-equal-or-higher scoring
table attributed to Muhurta Chintamani v.22 and Bharatiya Jyotish p.609.
The traditional Varna labels are technical categories in this astrology
calculation; they do not describe a person's social identity or worth.
"""

import math

from app.services.astrology.sweph import RASHIS

BRAHMIN = "Brahmin"
KSHATRIYA = "Kshatriya"
VAISHYA = "Vaishya"
SHUDRA = "Shudra"

# Classical order from highest to lowest for this scoring convention.
VARNA_RANKS = {
    BRAHMIN: 4,
    KSHATRIYA: 3,
    VAISHYA: 2,
    SHUDRA: 1,
}

VARNA_BY_RASHI = {
    "Mesha": KSHATRIYA,
    "Vrishabha": VAISHYA,
    "Mithuna": SHUDRA,
    "Karka": BRAHMIN,
    "Simha": KSHATRIYA,
    "Kanya": VAISHYA,
    "Tula": SHUDRA,
    "Vrischika": BRAHMIN,
    "Dhanu": KSHATRIYA,
    "Makara": VAISHYA,
    "Kumbha": SHUDRA,
    "Meena": BRAHMIN,
}

VARNA_MAX_SCORE = 1
VARNA_CONVENTION = "muhurta_chintamani_bharatiya_jyotish_groom_equal_or_higher"


def get_varna(rashi_index: int) -> str:
    """Return the Varna classification for a 1-based Moon Rashi index."""
    if isinstance(rashi_index, bool) or not isinstance(rashi_index, int):
        raise ValueError("Rashi index must be an integer")
    if not 1 <= rashi_index <= 12:
        raise ValueError("Rashi index must be between 1 and 12")

    return VARNA_BY_RASHI[RASHIS[rashi_index - 1]]


def calculate_varna_score(bride_varna: str, groom_varna: str) -> dict:
    """Award 1 point when groom's Varna rank is equal to or above bride's."""
    if bride_varna not in VARNA_RANKS:
        raise ValueError("Invalid bride Varna")
    if groom_varna not in VARNA_RANKS:
        raise ValueError("Invalid groom Varna")

    score = int(VARNA_RANKS[groom_varna] >= VARNA_RANKS[bride_varna])
    return {
        "koota": "Varna",
        "bride_varna": bride_varna,
        "groom_varna": groom_varna,
        "bride_rank": VARNA_RANKS[bride_varna],
        "groom_rank": VARNA_RANKS[groom_varna],
        "score": score,
        "maximum": VARNA_MAX_SCORE,
        "convention": VARNA_CONVENTION,
    }


def _moon_rashi_index(sidereal_longitude: float) -> int:
    """Convert a finite D1 sidereal Moon longitude to a 1-based Rashi index."""
    if (
        isinstance(sidereal_longitude, bool)
        or not isinstance(sidereal_longitude, (int, float))
    ):
        raise ValueError("Moon longitude must be a finite number from 0 to 360")

    longitude = float(sidereal_longitude)
    if not math.isfinite(longitude) or not 0 <= longitude <= 360:
        raise ValueError("Moon longitude must be a finite number from 0 to 360")

    return int((longitude % 360.0) // 30.0) + 1


def calculate_varna_compatibility(
    bride_moon_longitude: float,
    groom_moon_longitude: float,
) -> dict:
    """Calculate Varna Koota from both D1 sidereal Moon longitudes."""
    bride_rashi_index = _moon_rashi_index(bride_moon_longitude)
    groom_rashi_index = _moon_rashi_index(groom_moon_longitude)

    bride_rashi = RASHIS[bride_rashi_index - 1]
    groom_rashi = RASHIS[groom_rashi_index - 1]
    bride_varna = get_varna(bride_rashi_index)
    groom_varna = get_varna(groom_rashi_index)

    result = calculate_varna_score(bride_varna, groom_varna)
    return {
        **result,
        "bride_rashi": bride_rashi,
        "groom_rashi": groom_rashi,
        "bride_rashi_index": bride_rashi_index,
        "groom_rashi_index": groom_rashi_index,
    }
