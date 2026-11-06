"""Vashya Koota based on the D1 sidereal Moon longitude.

The implementation uses five Vashya groups and the directional bride-row /
groom-column score table reproduced by freehoroscopesonline.in. Sagittarius
and Capricorn are split at 15 degrees, as described by Drik Panchang.
"""

import math

from app.services.astrology.sweph import RASHIS

CHATASHPADA = "Chatushpada"
MANAVA = "Manava"
JALACHARA = "Jalachara"
VANACHARA = "Vanachara"
KEETA = "Keeta"

VALID_VASHYAS = {
    CHATASHPADA,
    MANAVA,
    JALACHARA,
    VANACHARA,
    KEETA,
}

VASHYA_MAX_SCORE = 2
VASHYA_CONVENTION = "freehoroscopesonline_directional_bride_rows"

# Rows are bride's Vashya; columns are groom's Vashya.
# The table is directional: for example, Chatushpada -> Vanachara is 1.5,
# while Vanachara -> Chatushpada is 0.
VASHYA_SCORE_TABLE = {
    CHATASHPADA: {
        CHATASHPADA: 2,
        MANAVA: 1,
        JALACHARA: 1,
        VANACHARA: 1.5,
        KEETA: 1,
    },
    MANAVA: {
        CHATASHPADA: 1,
        MANAVA: 2,
        JALACHARA: 1.5,
        VANACHARA: 0,
        KEETA: 1,
    },
    JALACHARA: {
        CHATASHPADA: 1,
        MANAVA: 1.5,
        JALACHARA: 2,
        VANACHARA: 1,
        KEETA: 1,
    },
    VANACHARA: {
        CHATASHPADA: 0,
        MANAVA: 0,
        JALACHARA: 0,
        VANACHARA: 2,
        KEETA: 0,
    },
    KEETA: {
        CHATASHPADA: 1,
        MANAVA: 1,
        JALACHARA: 1,
        VANACHARA: 0,
        KEETA: 2,
    },
}

# Fixed classifications for signs that do not change within the sign.
_FIXED_VASHYA_BY_RASHI = {
    "Mesha": CHATASHPADA,
    "Vrishabha": CHATASHPADA,
    "Mithuna": MANAVA,
    "Karka": JALACHARA,
    "Simha": VANACHARA,
    "Kanya": MANAVA,
    "Tula": MANAVA,
    "Vrischika": KEETA,
    "Kumbha": MANAVA,
    "Meena": JALACHARA,
}


def get_vashya(rashi_index: int, degrees_in_rashi: float) -> str:
    """Return a Vashya group from a 1-based Rashi index and 0–30° position."""
    if isinstance(rashi_index, bool) or not isinstance(rashi_index, int):
        raise ValueError("Rashi index must be an integer")
    if not 1 <= rashi_index <= 12:
        raise ValueError("Rashi index must be between 1 and 12")

    if (
        isinstance(degrees_in_rashi, bool)
        or not isinstance(degrees_in_rashi, (int, float))
    ):
        raise ValueError("Degrees in Rashi must be a finite number from 0 to 30")

    degrees = float(degrees_in_rashi)
    if not math.isfinite(degrees) or not 0 <= degrees < 30:
        raise ValueError("Degrees in Rashi must be at least 0 and less than 30")

    rashi_name = RASHIS[rashi_index - 1]

    if rashi_name == "Dhanu":
        return MANAVA if degrees < 15 else CHATASHPADA

    if rashi_name == "Makara":
        return CHATASHPADA if degrees < 15 else JALACHARA

    return _FIXED_VASHYA_BY_RASHI[rashi_name]


def calculate_vashya_score(bride_vashya: str, groom_vashya: str) -> dict:
    """Calculate directional Vashya Koota score out of 2."""
    if bride_vashya not in VALID_VASHYAS:
        raise ValueError("Invalid bride Vashya group")
    if groom_vashya not in VALID_VASHYAS:
        raise ValueError("Invalid groom Vashya group")

    score = VASHYA_SCORE_TABLE[bride_vashya][groom_vashya]
    return {
        "koota": "Vashya",
        "bride_vashya": bride_vashya,
        "groom_vashya": groom_vashya,
        "score": score,
        "maximum": VASHYA_MAX_SCORE,
        "convention": VASHYA_CONVENTION,
    }


def _moon_rashi_and_degrees(sidereal_longitude: float) -> tuple[int, float]:
    """Convert a finite 0–360° longitude into Rashi index and in-sign degrees."""
    if (
        isinstance(sidereal_longitude, bool)
        or not isinstance(sidereal_longitude, (int, float))
    ):
        raise ValueError("Moon longitude must be a finite number from 0 to 360")

    longitude = float(sidereal_longitude)
    if not math.isfinite(longitude) or not 0 <= longitude <= 360:
        raise ValueError("Moon longitude must be a finite number from 0 to 360")

    normalized = longitude % 360.0
    rashi_index = int(normalized // 30.0) + 1
    degrees_in_rashi = normalized - ((rashi_index - 1) * 30.0)
    return rashi_index, degrees_in_rashi


def calculate_vashya_compatibility(
    bride_moon_longitude: float,
    groom_moon_longitude: float,
) -> dict:
    """Calculate Vashya from both D1 sidereal Moon longitudes."""
    bride_rashi_index, bride_degrees = _moon_rashi_and_degrees(
        bride_moon_longitude
    )
    groom_rashi_index, groom_degrees = _moon_rashi_and_degrees(
        groom_moon_longitude
    )

    bride_rashi = RASHIS[bride_rashi_index - 1]
    groom_rashi = RASHIS[groom_rashi_index - 1]
    bride_vashya = get_vashya(bride_rashi_index, bride_degrees)
    groom_vashya = get_vashya(groom_rashi_index, groom_degrees)

    result = calculate_vashya_score(bride_vashya, groom_vashya)
    return {
        **result,
        "bride_rashi": bride_rashi,
        "groom_rashi": groom_rashi,
        "bride_rashi_index": bride_rashi_index,
        "groom_rashi_index": groom_rashi_index,
        "bride_degrees_in_rashi": bride_degrees,
        "groom_degrees_in_rashi": groom_degrees,
    }
