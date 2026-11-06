"""Graha Maitri Koota: natural friendship of the two Moon-sign lords.

Scoring convention: Saravali's published mutual-relationship table:
friend/friend=5, friend/neutral=4, neutral/neutral=3,
friend/enemy=2, neutral/enemy=1, enemy/enemy=0.
"""

import math

from app.services.astrology.sweph import RASHIS

RASHI_LORDS = {
    "Mesha": "Mars",
    "Vrishabha": "Venus",
    "Mithuna": "Mercury",
    "Karka": "Moon",
    "Simha": "Sun",
    "Kanya": "Mercury",
    "Tula": "Venus",
    "Vrischika": "Mars",
    "Dhanu": "Jupiter",
    "Makara": "Saturn",
    "Kumbha": "Saturn",
    "Meena": "Jupiter",
}

FRIEND = "friend"
NEUTRAL = "neutral"
ENEMY = "enemy"

PLANETARY_RELATIONSHIPS = {
    "Sun": {
        "Moon": FRIEND, "Mars": FRIEND, "Mercury": NEUTRAL,
        "Jupiter": FRIEND, "Venus": ENEMY, "Saturn": ENEMY,
    },
    "Moon": {
        "Sun": FRIEND, "Mars": NEUTRAL, "Mercury": FRIEND,
        "Jupiter": NEUTRAL, "Venus": NEUTRAL, "Saturn": NEUTRAL,
    },
    "Mars": {
        "Sun": FRIEND, "Moon": FRIEND, "Mercury": ENEMY,
        "Jupiter": FRIEND, "Venus": NEUTRAL, "Saturn": NEUTRAL,
    },
    "Mercury": {
        "Sun": FRIEND, "Moon": ENEMY, "Mars": NEUTRAL,
        "Jupiter": NEUTRAL, "Venus": FRIEND, "Saturn": NEUTRAL,
    },
    "Jupiter": {
        "Sun": FRIEND, "Moon": FRIEND, "Mars": FRIEND,
        "Mercury": ENEMY, "Venus": ENEMY, "Saturn": NEUTRAL,
    },
    "Venus": {
        "Sun": ENEMY, "Moon": ENEMY, "Mars": NEUTRAL,
        "Mercury": FRIEND, "Jupiter": NEUTRAL, "Saturn": FRIEND,
    },
    "Saturn": {
        "Sun": ENEMY, "Moon": ENEMY, "Mars": ENEMY,
        "Mercury": FRIEND, "Jupiter": NEUTRAL, "Venus": FRIEND,
    },
}

GRAHA_MAITRI_MAX_SCORE = 5
GRAHA_MAITRI_CONVENTION = "saravali_mutual_relationships"

# Use frozensets because the two directional relationships are evaluated together.
_SCORE_BY_RELATIONSHIP_PAIR = {
    frozenset((FRIEND,)): 5,
    frozenset((FRIEND, NEUTRAL)): 4,
    frozenset((NEUTRAL,)): 3,
    frozenset((FRIEND, ENEMY)): 2,
    frozenset((NEUTRAL, ENEMY)): 1,
    frozenset((ENEMY,)): 0,
}


def get_rashi_lord(rashi_index: int) -> str:
    """Return the ruler for a 1-based Rashi index (1–12)."""
    if isinstance(rashi_index, bool) or not isinstance(rashi_index, int):
        raise ValueError("Rashi index must be an integer")
    if not 1 <= rashi_index <= 12:
        raise ValueError("Rashi index must be between 1 and 12")
    return RASHI_LORDS[RASHIS[rashi_index - 1]]


def get_planetary_relationship(first_planet: str, second_planet: str) -> str:
    """Return how the first planet naturally regards the second."""
    if first_planet not in PLANETARY_RELATIONSHIPS:
        raise ValueError("Invalid first planet")
    if second_planet not in PLANETARY_RELATIONSHIPS:
        raise ValueError("Invalid second planet")
    if first_planet == second_planet:
        return FRIEND
    return PLANETARY_RELATIONSHIPS[first_planet][second_planet]


def calculate_graha_maitri_score(
    bride_planet: str,
    groom_planet: str,
) -> dict:
    """Calculate Graha Maitri out of 5 from both directional friendships."""
    bride_view = get_planetary_relationship(bride_planet, groom_planet)
    groom_view = get_planetary_relationship(groom_planet, bride_planet)
    score = _SCORE_BY_RELATIONSHIP_PAIR[frozenset((bride_view, groom_view))]

    return {
        "koota": "Graha Maitri",
        "bride_planet": bride_planet,
        "groom_planet": groom_planet,
        "bride_regards_groom": bride_view,
        "groom_regards_bride": groom_view,
        "score": score,
        "maximum": GRAHA_MAITRI_MAX_SCORE,
        "convention": GRAHA_MAITRI_CONVENTION,
    }


def _moon_rashi_index(sidereal_longitude: float) -> int:
    """Convert a validated sidereal longitude to a 1-based Moon-sign index."""
    if isinstance(sidereal_longitude, bool) or not isinstance(sidereal_longitude, (int, float)):
        raise ValueError("Moon longitude must be a finite number from 0 to 360")
    longitude = float(sidereal_longitude)
    if not math.isfinite(longitude) or not 0 <= longitude <= 360:
        raise ValueError("Moon longitude must be a finite number from 0 to 360")
    return int((longitude % 360.0) // 30.0) + 1


def calculate_graha_maitri_compatibility(
    bride_moon_longitude: float,
    groom_moon_longitude: float,
) -> dict:
    """Calculate Graha Maitri from the two D1 sidereal Moon longitudes."""
    bride_rashi_index = _moon_rashi_index(bride_moon_longitude)
    groom_rashi_index = _moon_rashi_index(groom_moon_longitude)

    bride_rashi = RASHIS[bride_rashi_index - 1]
    groom_rashi = RASHIS[groom_rashi_index - 1]
    bride_planet = get_rashi_lord(bride_rashi_index)
    groom_planet = get_rashi_lord(groom_rashi_index)

    result = calculate_graha_maitri_score(bride_planet, groom_planet)
    return {
        **result,
        "bride_rashi": bride_rashi,
        "groom_rashi": groom_rashi,
        "bride_rashi_index": bride_rashi_index,
        "groom_rashi_index": groom_rashi_index,
    }
