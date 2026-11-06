"""Traditional Nadi classifications for the 27 Nakshatras."""

from app.services.astrology.sweph import NAKSHATRAS

ADI = "Adi"
MADHYA = "Madhya"
ANTYA = "Antya"

NADI_BY_NAKSHATRA = {
    "Ashwini": ADI, "Bharani": MADHYA, "Krittika": ANTYA,
    "Rohini": ANTYA, "Mrigashira": MADHYA, "Ardra": ADI,
    "Punarvasu": ADI, "Pushya": MADHYA, "Ashlesha": ANTYA,
    "Magha": ANTYA, "Purva Phalguni": MADHYA, "Uttara Phalguni": ADI,
    "Hasta": ADI, "Chitra": MADHYA, "Swati": ANTYA,
    "Vishakha": ANTYA, "Anuradha": MADHYA, "Jyeshtha": ADI,
    "Mula": ADI, "Purva Ashadha": MADHYA, "Uttara Ashadha": ANTYA,
    "Shravana": ANTYA, "Dhanishta": MADHYA, "Shatabhisha": ADI,
    "Purva Bhadrapada": ADI, "Uttara Bhadrapada": MADHYA, "Revati": ANTYA,
}


def get_nadi(nakshatra_index: int) -> str:
    """Return the Nadi for a 1-based Nakshatra index."""
    if isinstance(nakshatra_index, bool) or not isinstance(nakshatra_index, int):
        raise ValueError("Nakshatra index must be an integer")
    if not 1 <= nakshatra_index <= 27:
        raise ValueError("Nakshatra index must be between 1 and 27")
    return NADI_BY_NAKSHATRA[NAKSHATRAS[nakshatra_index - 1]]
