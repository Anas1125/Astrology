"""Yoni Koota using a sex-specific 27-variant Yoni Chakra.

Reference convention: the full bride-row/groom-column matrix reproduced by
CosmiqeAI (source labels the matrix as from Muhurta Chintamani, Vivaha
Prakarana). This is one documented table; other published Yoni tables differ.
"""

from app.services.astrology.sweph import NAKSHATRAS
from app.services.astrology.compatibility.nakshatra import calculate_moon_nakshatra

# Each Nakshatra maps to one of 27 sex-specific Yoni variants.
# The order follows NAKSHATRAS in sweph.py.
YONI_BY_NAKSHATRA = {
    "Ashwini": "horse_male",
    "Bharani": "elephant_male",
    "Krittika": "sheep_female",
    "Rohini": "serpent_male",
    "Mrigashirsha": "serpent_female",
    "Ardra": "dog_female",
    "Punarvasu": "cat_female",
    "Pushya": "sheep_male",
    "Ashlesha": "cat_male",
    "Magha": "rat_male",
    "Purva Phalguni": "rat_female",
    "Uttara Phalguni": "cow_male",
    "Hasta": "buffalo_female",
    "Chitra": "tiger_female",
    "Swati": "buffalo_male",
    "Vishakha": "tiger_male",
    "Anuradha": "deer_female",
    "Jyeshtha": "deer_male",
    "Mula": "dog_male",
    "Purva Ashadha": "monkey_male",
    "Uttara Ashadha": "mongoose_male",
    "Shravana": "monkey_female",
    "Dhanishta": "lion_female",
    "Shatabhisha": "horse_female",
    "Purva Bhadrapada": "lion_male",
    "Uttara Bhadrapada": "cow_female",
    "Revati": "elephant_female",
}

YONI_LABELS = {
    "horse_male": "Horse (male)",
    "elephant_male": "Elephant (male)",
    "sheep_female": "Sheep (female)",
    "serpent_male": "Serpent (male)",
    "serpent_female": "Serpent (female)",
    "dog_female": "Dog (female)",
    "cat_female": "Cat (female)",
    "sheep_male": "Sheep (male)",
    "cat_male": "Cat (male)",
    "rat_male": "Rat (male)",
    "rat_female": "Rat (female)",
    "cow_male": "Cow (male)",
    "buffalo_female": "Buffalo (female)",
    "tiger_female": "Tiger (female)",
    "buffalo_male": "Buffalo (male)",
    "tiger_male": "Tiger (male)",
    "deer_female": "Deer (female)",
    "deer_male": "Deer (male)",
    "dog_male": "Dog (male)",
    "monkey_male": "Monkey (male)",
    "mongoose_male": "Mongoose (male)",
    "monkey_female": "Monkey (female)",
    "lion_female": "Lion (female)",
    "horse_female": "Horse (female)",
    "lion_male": "Lion (male)",
    "cow_female": "Cow (female)",
    "elephant_female": "Elephant (female)",
}

# Matrix order is the same as YONI_ORDER. Rows are bride; columns are groom.
YONI_ORDER = (
    "horse_male", "elephant_male", "sheep_female", "serpent_male",
    "serpent_female", "dog_female", "cat_female", "sheep_male",
    "cat_male", "rat_male", "rat_female", "cow_male",
    "buffalo_female", "tiger_female", "buffalo_male", "tiger_male",
    "deer_female", "deer_male", "dog_male", "monkey_male",
    "mongoose_male", "monkey_female", "lion_female", "horse_female",
    "lion_male", "cow_female", "elephant_female",
)

_YONI_SCORE_ROWS = (
    (4, 2, 3, 2, 2, 2, 3, 3, 3, 3, 3, 2, 0, 1, 0, 1, 3, 3, 2, 2, 2, 2, 1, 4, 1, 2, 2),
    (2, 4, 3, 2, 2, 2, 3, 3, 3, 2, 2, 3, 3, 1, 3, 1, 3, 3, 2, 2, 2, 2, 0, 2, 0, 3, 4),
    (3, 3, 4, 2, 2, 2, 3, 4, 3, 2, 2, 3, 3, 1, 3, 1, 3, 3, 2, 0, 2, 0, 1, 3, 1, 3, 3),
    (2, 2, 2, 4, 4, 2, 1, 2, 1, 1, 1, 2, 2, 2, 2, 2, 2, 2, 2, 1, 0, 1, 2, 2, 2, 2, 2),
    (2, 2, 2, 4, 4, 2, 1, 2, 1, 1, 1, 2, 2, 2, 2, 2, 2, 2, 2, 1, 0, 1, 2, 2, 2, 2, 2),
    (2, 2, 2, 2, 2, 4, 1, 2, 1, 1, 1, 2, 2, 2, 2, 2, 0, 0, 4, 2, 2, 2, 2, 2, 2, 2, 2),
    (3, 3, 3, 1, 1, 1, 4, 3, 4, 0, 0, 3, 3, 2, 3, 2, 3, 3, 1, 2, 2, 2, 2, 3, 2, 3, 3),
    (3, 3, 4, 2, 2, 2, 3, 4, 3, 2, 2, 3, 3, 1, 3, 1, 3, 3, 2, 0, 2, 0, 1, 3, 1, 3, 3),
    (3, 3, 3, 1, 1, 1, 4, 3, 4, 0, 0, 3, 3, 2, 3, 2, 3, 3, 1, 2, 2, 2, 2, 3, 2, 3, 3),
    (3, 2, 2, 1, 1, 1, 0, 2, 0, 4, 4, 3, 3, 2, 3, 2, 3, 3, 1, 2, 1, 2, 2, 3, 2, 3, 2),
    (3, 2, 2, 1, 1, 1, 0, 2, 0, 4, 4, 3, 3, 2, 3, 2, 3, 3, 1, 2, 1, 2, 2, 3, 2, 3, 2),
    (2, 3, 3, 2, 2, 2, 3, 3, 3, 3, 3, 4, 3, 0, 3, 0, 3, 3, 2, 2, 2, 2, 1, 2, 1, 4, 3),
    (0, 3, 3, 2, 2, 2, 3, 3, 3, 3, 3, 3, 4, 1, 4, 1, 3, 3, 2, 2, 2, 2, 1, 0, 1, 3, 3),
    (1, 1, 1, 2, 2, 2, 2, 1, 2, 2, 2, 0, 1, 4, 1, 4, 1, 1, 2, 2, 2, 2, 3, 1, 3, 0, 1),
    (0, 3, 3, 2, 2, 2, 3, 3, 3, 3, 3, 3, 4, 1, 4, 1, 3, 3, 2, 2, 2, 2, 1, 0, 1, 3, 3),
    (1, 1, 1, 2, 2, 2, 2, 1, 2, 2, 2, 0, 1, 4, 1, 4, 1, 1, 2, 2, 2, 2, 3, 1, 3, 0, 1),
    (3, 3, 3, 2, 2, 0, 3, 3, 3, 3, 3, 3, 3, 1, 3, 1, 4, 4, 0, 2, 2, 2, 1, 3, 1, 3, 3),
    (3, 3, 3, 2, 2, 0, 3, 3, 3, 3, 3, 3, 3, 1, 3, 1, 4, 4, 0, 2, 2, 2, 1, 3, 1, 3, 3),
    (2, 2, 2, 2, 2, 4, 1, 2, 1, 1, 1, 2, 2, 2, 2, 2, 0, 0, 4, 2, 2, 2, 2, 2, 2, 2, 2),
    (2, 2, 0, 1, 1, 2, 2, 0, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 4, 2, 4, 2, 2, 2, 2, 2),
    (2, 2, 2, 0, 0, 2, 2, 2, 2, 1, 1, 2, 2, 2, 2, 2, 2, 2, 2, 2, 4, 2, 2, 2, 2, 2, 2),
    (2, 2, 0, 1, 1, 2, 2, 0, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 4, 2, 4, 2, 2, 2, 2, 2),
    (1, 0, 1, 2, 2, 2, 2, 1, 2, 2, 2, 1, 1, 3, 1, 3, 1, 1, 2, 2, 2, 2, 4, 1, 4, 1, 0),
    (4, 2, 3, 2, 2, 2, 3, 3, 3, 3, 3, 2, 0, 1, 0, 1, 3, 3, 2, 2, 2, 2, 1, 4, 1, 2, 2),
    (1, 0, 1, 2, 2, 2, 2, 1, 2, 2, 2, 1, 1, 3, 1, 3, 1, 1, 2, 2, 2, 2, 4, 1, 4, 1, 0),
    (2, 3, 3, 2, 2, 2, 3, 3, 3, 3, 3, 4, 3, 0, 3, 0, 3, 3, 2, 2, 2, 2, 1, 2, 1, 4, 3),
    (2, 4, 3, 2, 2, 2, 3, 3, 3, 2, 2, 3, 3, 1, 3, 1, 3, 3, 2, 2, 2, 2, 0, 2, 0, 3, 4),
)

YONI_SCORE_TABLE = {
    bride: dict(zip(YONI_ORDER, row, strict=True))
    for bride, row in zip(YONI_ORDER, _YONI_SCORE_ROWS, strict=True)
}

YONI_MAX_SCORE = 4
YONI_CONVENTION = "cosmiqeai_muhurta_chintamani_27_variant_matrix"


def get_yoni(nakshatra_index: int) -> str:
    """Return a sex-specific Yoni code for a 1-based Nakshatra index."""
    if isinstance(nakshatra_index, bool) or not isinstance(nakshatra_index, int):
        raise ValueError("Nakshatra index must be an integer")
    if not 1 <= nakshatra_index <= 27:
        raise ValueError("Nakshatra index must be between 1 and 27")

    nakshatra_name = NAKSHATRAS[nakshatra_index - 1]
    return YONI_BY_NAKSHATRA[nakshatra_name]


def calculate_yoni_score(bride_yoni: str, groom_yoni: str) -> dict:
    """Calculate Yoni Koota from the published 27-by-27 matrix."""
    if bride_yoni not in YONI_SCORE_TABLE:
        raise ValueError("Invalid bride Yoni")
    if groom_yoni not in YONI_SCORE_TABLE:
        raise ValueError("Invalid groom Yoni")

    score = YONI_SCORE_TABLE[bride_yoni][groom_yoni]
    return {
        "koota": "Yoni",
        "bride_yoni": bride_yoni,
        "groom_yoni": groom_yoni,
        "bride_yoni_label": YONI_LABELS[bride_yoni],
        "groom_yoni_label": YONI_LABELS[groom_yoni],
        "score": score,
        "maximum": YONI_MAX_SCORE,
        "convention": YONI_CONVENTION,
    }


def calculate_yoni_compatibility(
    bride_moon_longitude: float,
    groom_moon_longitude: float,
) -> dict:
    """Calculate Yoni Koota from both D1 sidereal Moon longitudes."""
    bride_nakshatra = calculate_moon_nakshatra(bride_moon_longitude)
    groom_nakshatra = calculate_moon_nakshatra(groom_moon_longitude)

    bride_yoni = get_yoni(bride_nakshatra["index"])
    groom_yoni = get_yoni(groom_nakshatra["index"])
    result = calculate_yoni_score(bride_yoni, groom_yoni)

    return {
        **result,
        "bride_nakshatra": bride_nakshatra,
        "groom_nakshatra": groom_nakshatra,
    }
