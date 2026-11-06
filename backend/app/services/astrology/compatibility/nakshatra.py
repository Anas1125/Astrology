"""Nakshatra calculations for Vedic compatibility."""

from app.services.astrology.sweph import nakshatra_details


def calculate_moon_nakshatra(sidereal_longitude: float) -> dict:
    """Calculate Nakshatra details from the Moon's D1 sidereal longitude."""
    details = nakshatra_details(sidereal_longitude)
    return {
        "index": details["index"],
        "name": details["name"],
        "pada": details["pada"],
        "lord": details["lord"],
        "degrees_remaining": details["degrees_remaining"],
        "remaining_fraction": details["remaining_fraction"],
    }
