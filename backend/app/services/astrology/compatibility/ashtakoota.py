"""Aggregate all eight Ashtakoota calculations into one report.

This orchestrator combines the currently selected, explicitly labelled
component conventions. It does not change the scoring tables themselves.
Bhakoot cancellation is not evaluated by the current Bhakoot module and is
surfaced as such in the aggregate report.
"""

from app.services.astrology.compatibility.bhakoot import (
    calculate_bhakoot_compatibility,
)
from app.services.astrology.compatibility.gana_scoring import (
    calculate_gana_compatibility,
)
from app.services.astrology.compatibility.graha_maitri import (
    calculate_graha_maitri_compatibility,
)
from app.services.astrology.compatibility.nadi_scoring import (
    calculate_nadi_compatibility,
)
from app.services.astrology.compatibility.tara import (
    calculate_tara_compatibility,
)
from app.services.astrology.compatibility.varna import (
    calculate_varna_compatibility,
)
from app.services.astrology.compatibility.vashya import (
    calculate_vashya_compatibility,
)
from app.services.astrology.compatibility.yoni import (
    calculate_yoni_compatibility,
)

ASHTAKOOTA_MAX_SCORE = 36
ASHTAKOOTA_METHOD = "vedic_ashtakoota"


def calculate_ashtakoota(
    bride_moon_longitude: float,
    groom_moon_longitude: float,
) -> dict:
    """Calculate all eight Kootas from two D1 sidereal Moon longitudes.

    The longitudes must be in the same sidereal zodiac and ayanamsa.
    Each component retains its own convention label and detailed result.
    """
    factors = [
        calculate_varna_compatibility(
            bride_moon_longitude, groom_moon_longitude
        ),
        calculate_vashya_compatibility(
            bride_moon_longitude, groom_moon_longitude
        ),
        calculate_tara_compatibility(
            bride_moon_longitude, groom_moon_longitude
        ),
        calculate_yoni_compatibility(
            bride_moon_longitude, groom_moon_longitude
        ),
        calculate_graha_maitri_compatibility(
            bride_moon_longitude, groom_moon_longitude
        ),
        calculate_gana_compatibility(
            bride_moon_longitude, groom_moon_longitude
        ),
        calculate_bhakoot_compatibility(
            bride_moon_longitude, groom_moon_longitude
        ),
        calculate_nadi_compatibility(
            bride_moon_longitude, groom_moon_longitude
        ),
    ]

    total_score = 0.0
    total_maximum = 0
    conventions = {}

    for factor in factors:
        score = factor.get("score")
        maximum = factor.get("maximum")
        koota = factor.get("koota")

        if not isinstance(koota, str) or not koota:
            raise ValueError("A Koota result is missing its name")
        if (
            isinstance(score, bool)
            or not isinstance(score, (int, float))
            or not 0 <= score <= maximum
        ):
            raise ValueError(f"Invalid score returned by {koota}")
        if isinstance(maximum, bool) or not isinstance(maximum, int) or maximum <= 0:
            raise ValueError(f"Invalid maximum returned by {koota}")

        total_score += score
        total_maximum += maximum
        conventions[koota] = factor.get("convention")

    if total_maximum != ASHTAKOOTA_MAX_SCORE:
        raise ValueError(
            f"Expected eight Kootas to total 36 points; got {total_maximum}"
        )

    bhakoot = next(factor for factor in factors if factor["koota"] == "Bhakoot")

    return {
        "method": ASHTAKOOTA_METHOD,
        "calculation_basis": "D1 sidereal Moon longitudes",
        "total_score": total_score,
        "maximum_score": ASHTAKOOTA_MAX_SCORE,
        "completed_kootas": len(factors),
        "factors": factors,
        "conventions": conventions,
        "bhakoot_cancellation": {
            "dosha_detected": bhakoot["dosha"],
            "evaluated": bhakoot["cancellation_evaluated"],
            "status": bhakoot["cancellation_status"],
            "note": "Bhakoot cancellation rules have not been evaluated.",
        },
        "interpretation_status": "not_assigned",
    }
