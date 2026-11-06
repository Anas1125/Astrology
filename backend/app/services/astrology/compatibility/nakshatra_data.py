"""Nakshatra metadata used by the compatibility engine."""

from app.services.astrology.sweph import NAKSHATRAS, NAKSHATRA_LORDS


def get_nakshatra_metadata(index: int) -> dict:
    """Return metadata for a 1-based Nakshatra index (1–27)."""
    if isinstance(index, bool) or not isinstance(index, int):
        raise ValueError("Nakshatra index must be an integer")
    if not 1 <= index <= 27:
        raise ValueError("Nakshatra index must be between 1 and 27")

    position = index - 1
    return {
        "index": index,
        "name": NAKSHATRAS[position],
        "lord": NAKSHATRA_LORDS[position % 9],
    }


def get_all_nakshatras() -> list[dict]:
    """Return all 27 Nakshatras in astronomical-engine order."""
    return [get_nakshatra_metadata(index) for index in range(1, 28)]
