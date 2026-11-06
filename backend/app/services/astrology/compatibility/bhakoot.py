"""Bhakoot Koota using the two D1 sidereal Moon signs.

Base convention: relative inclusive sign-count pairs 2/12, 5/9 and 6/8
score zero; all other pairs score seven. Dosha cancellation is deliberately
not applied here: the result reports the base score and cancellation status
as unresolved for a later, separately documented evaluation.
"""

import math

from app.services.astrology.sweph import RASHIS

BHAKOOT_MAX_SCORE = 7
BHAKOOT_DOSHA_PAIRS = {(2, 12), (5, 9), (6, 8)}
BHAKOOT_CONVENTION = "inclusive_bidirectional_moon_rashi_base_score"


def _validate_rashi_index(rashi_index: int) -> None:
    if isinstance(rashi_index, bool) or not isinstance(rashi_index, int):
        raise ValueError("Rashi index must be an integer")
    if not 1 <= rashi_index <= 12:
        raise ValueError("Rashi index must be between 1 and 12")


def calculate_bhakoot_score(
    bride_rashi_index: int,
    groom_rashi_index: int,
) -> dict:
    """Calculate base Bhakoot score from 1-based bride/groom Moon Rashi indexes.

    Counts are inclusive: same sign is 1/1. The two directional counts
    together form the familiar 1/1, 2/12, 3/11, 4/10, 5/9, 6/8 or 7/7 pair.
    """
    _validate_rashi_index(bride_rashi_index)
    _validate_rashi_index(groom_rashi_index)

    bride_to_groom = ((groom_rashi_index - bride_rashi_index) % 12) + 1
    groom_to_bride = ((bride_rashi_index - groom_rashi_index) % 12) + 1
    relationship = tuple(sorted((bride_to_groom, groom_to_bride)))
    dosha = relationship in BHAKOOT_DOSHA_PAIRS
    score = 0 if dosha else BHAKOOT_MAX_SCORE

    dosha_name = {
        (2, 12): "Dwidwadash (2/12)",
        (5, 9): "Nav Pancham (5/9)",
        (6, 8): "Shadashtak (6/8)",
    }.get(relationship)

    return {
        "koota": "Bhakoot",
        "bride_rashi_index": bride_rashi_index,
        "groom_rashi_index": groom_rashi_index,
        "bride_rashi": RASHIS[bride_rashi_index - 1],
        "groom_rashi": RASHIS[groom_rashi_index - 1],
        "bride_to_groom_count": bride_to_groom,
        "groom_to_bride_count": groom_to_bride,
        "relationship": f"{relationship[0]}/{relationship[1]}",
        "dosha": dosha,
        "dosha_type": dosha_name,
        "score": score,
        "maximum": BHAKOOT_MAX_SCORE,
        "convention": BHAKOOT_CONVENTION,
        "cancellation_evaluated": False,
        "cancellation_status": "not_evaluated",
    }


def _moon_rashi_index(sidereal_longitude: float) -> int:
    """Convert a finite D1 sidereal longitude into a 1-based Moon Rashi index."""
    if (
        isinstance(sidereal_longitude, bool)
        or not isinstance(sidereal_longitude, (int, float))
    ):
        raise ValueError("Moon longitude must be a finite number from 0 to 360")

    longitude = float(sidereal_longitude)
    if not math.isfinite(longitude) or not 0 <= longitude <= 360:
        raise ValueError("Moon longitude must be a finite number from 0 to 360")

    normalized = longitude % 360.0
    return int(normalized // 30.0) + 1


def calculate_bhakoot_compatibility(
    bride_moon_longitude: float,
    groom_moon_longitude: float,
) -> dict:
    """Calculate base Bhakoot from two D1 sidereal Moon longitudes."""
    bride_rashi_index = _moon_rashi_index(bride_moon_longitude)
    groom_rashi_index = _moon_rashi_index(groom_moon_longitude)
    return calculate_bhakoot_score(bride_rashi_index, groom_rashi_index)
