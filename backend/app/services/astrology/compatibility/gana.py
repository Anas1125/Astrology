"""Traditional Gana classifications for the 27 Nakshatras."""

from app.services.astrology.sweph import NAKSHATRAS

DEVA = "Deva"
MANUSHYA = "Manushya"
RAKSHASA = "Rakshasa"

GANA_BY_NAKSHATRA = {
    "Ashwini": DEVA, "Bharani": MANUSHYA, "Krittika": RAKSHASA,
    "Rohini": MANUSHYA, "Mrigashira": DEVA, "Ardra": MANUSHYA,
    "Punarvasu": DEVA, "Pushya": DEVA, "Ashlesha": RAKSHASA,
    "Magha": RAKSHASA, "Purva Phalguni": MANUSHYA,
    "Uttara Phalguni": MANUSHYA, "Hasta": DEVA, "Chitra": RAKSHASA,
    "Swati": DEVA, "Vishakha": RAKSHASA, "Anuradha": DEVA,
    "Jyeshtha": RAKSHASA, "Mula": RAKSHASA,
    "Purva Ashadha": MANUSHYA, "Uttara Ashadha": MANUSHYA,
    "Shravana": DEVA, "Dhanishta": RAKSHASA, "Shatabhisha": RAKSHASA,
    "Purva Bhadrapada": MANUSHYA, "Uttara Bhadrapada": MANUSHYA,
    "Revati": DEVA,
}


def get_gana(nakshatra_index: int) -> str:
    """Return the Gana for a 1-based Nakshatra index."""
    if isinstance(nakshatra_index, bool) or not isinstance(nakshatra_index, int):
        raise ValueError("Nakshatra index must be an integer")
    if not 1 <= nakshatra_index <= 27:
        raise ValueError("Nakshatra index must be between 1 and 27")
    return GANA_BY_NAKSHATRA[NAKSHATRAS[nakshatra_index - 1]]
