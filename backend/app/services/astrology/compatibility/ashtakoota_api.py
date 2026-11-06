"""Strict saved-chart input extraction for Vedic Ashtakoota."""
import math


class CompatibilityChartError(ValueError):
    def __init__(self, reason: str, message: str):
        super().__init__(message)
        self.reason = reason
        self.message = message


def extract_d1_lahiri_moon_longitude(chart, run) -> float:
    """Extract the original Moon longitude from a saved Vedic D1 Lahiri chart."""
    if getattr(chart, "system", None) != "vedic" or getattr(chart, "division", None) != "D1":
        raise CompatibilityChartError(
            "vedic_d1_chart_required",
            "Ashtakoota requires a saved Vedic D1 chart. D9 positions cannot be used.",
        )

    chart_config = getattr(chart, "config", None) or {}
    if chart_config.get("division") != "D1":
        raise CompatibilityChartError(
            "vedic_d1_chart_required",
            "The saved chart configuration is not Vedic D1.",
        )

    result = getattr(run, "result", None)
    if not isinstance(result, dict):
        raise CompatibilityChartError(
            "d1_lahiri_moon_data_required",
            "The saved chart result is missing or malformed.",
        )

    if result.get("calculation_system") != "vedic" or result.get("division") != "D1":
        raise CompatibilityChartError(
            "vedic_d1_chart_required",
            "The saved result is not a Vedic D1 calculation.",
        )

    configuration = result.get("configuration")
    if not isinstance(configuration, dict):
        raise CompatibilityChartError(
            "d1_lahiri_moon_data_required",
            "The saved chart does not identify its zodiac configuration.",
        )

    ayanamsa_name = str(result.get("ayanamsa_name", "")).strip().casefold()
    ayanamsa_config = str(configuration.get("ayanamsa", "")).strip().casefold()
    if (
        configuration.get("zodiac") != "sidereal"
        or ayanamsa_name != "lahiri"
        or ayanamsa_config != "lahiri"
        or configuration.get("division") != "D1"
    ):
        raise CompatibilityChartError(
            "d1_lahiri_moon_data_required",
            "Ashtakoota requires a saved sidereal Lahiri D1 Moon position.",
        )

    planets = result.get("planets")
    if not isinstance(planets, list):
        raise CompatibilityChartError(
            "d1_lahiri_moon_data_required",
            "The saved D1 chart has no valid planet list.",
        )

    moons = [
        planet for planet in planets
        if isinstance(planet, dict) and planet.get("name") == "Moon"
    ]
    if len(moons) != 1:
        raise CompatibilityChartError(
            "d1_lahiri_moon_data_required",
            "The saved D1 chart must contain exactly one Moon position.",
        )

    longitude = moons[0].get("longitude")
    if (
        isinstance(longitude, bool)
        or not isinstance(longitude, (int, float))
        or not math.isfinite(float(longitude))
        or not 0 <= float(longitude) <= 360
    ):
        raise CompatibilityChartError(
            "d1_lahiri_moon_data_required",
            "The saved D1 Moon longitude is invalid.",
        )

    return float(longitude)
