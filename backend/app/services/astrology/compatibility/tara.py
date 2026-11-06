"""Tara Koota calculations using inclusive Nakshatra counting."""

from app.services.astrology.compatibility.nakshatra import calculate_moon_nakshatra

TARA_MAX_SCORE = 3
DIRECTION_SCORE = 1.5

TARA_NAMES = {
    1: "Janma", 2: "Sampat", 3: "Vipat", 4: "Kshema", 5: "Pratyari",
    6: "Sadhaka", 7: "Vadha", 8: "Mitra", 9: "Ati-Mitra",
}
UNFAVOURABLE_TARAS = {3, 5, 7}


def calculate_tara_direction(from_index: int, to_index: int) -> dict:
    for value in (from_index, to_index):
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError("Nakshatra indexes must be integers")
        if not 1 <= value <= 27:
            raise ValueError("Nakshatra indexes must be between 1 and 27")
    count = ((to_index - from_index) % 27) + 1
    remainder = count % 9 or 9
    favourable = remainder not in UNFAVOURABLE_TARAS
    return {
        "count": count,
        "tara_number": remainder,
        "tara_name": TARA_NAMES[remainder],
        "favourable": favourable,
        "score": DIRECTION_SCORE if favourable else 0,
    }


def calculate_tara_score(bride_nakshatra_index: int, groom_nakshatra_index: int) -> dict:
    bride_to_groom = calculate_tara_direction(bride_nakshatra_index, groom_nakshatra_index)
    groom_to_bride = calculate_tara_direction(groom_nakshatra_index, bride_nakshatra_index)
    return {
        "koota": "Tara",
        "bride_to_groom": bride_to_groom,
        "groom_to_bride": groom_to_bride,
        "score": bride_to_groom["score"] + groom_to_bride["score"],
        "maximum": TARA_MAX_SCORE,
        "convention": "inclusive_bidirectional_tara",
    }


def calculate_tara_compatibility(
    bride_moon_longitude: float, groom_moon_longitude: float
) -> dict:
    bride = calculate_moon_nakshatra(bride_moon_longitude)
    groom = calculate_moon_nakshatra(groom_moon_longitude)
    result = calculate_tara_score(bride["index"], groom["index"])
    return {**result, "bride_nakshatra": bride, "groom_nakshatra": groom}
