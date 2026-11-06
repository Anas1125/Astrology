"""Western tropical natal chart derivations using the shared astronomy provider."""
from datetime import date, time
import math
from typing import Any

from app.core.config import settings
from app.services.astrology.base import AstrologyEngine, EngineUnavailable, ephemeris_failure_code
from app.services.astrology.sweph import (
    EphemerisUnavailable,
    InvalidBirthData,
    SwissEphemerisProvider,
    UnsupportedHouseSystem,
    local_birth_time_to_utc,
)

WESTERN_ENGINE_VERSION = "astroai-western/1.0.0"
HOUSE_SYSTEM_NAMES = {
    "P": "Placidus", "W": "Whole Sign", "K": "Koch", "R": "Regiomontanus",
    "C": "Campanus", "E": "Equal (Ascendant)", "O": "Porphyry", "B": "Alcabitius",
    "M": "Morinus", "A": "Equal (MC)", "V": "Vehlow Equal", "X": "Meridian",
    "H": "Horizon", "T": "Polich/Page",
}
ASPECT_ANGLES = {
    "conjunction": 0.0,
    "sextile": 60.0,
    "square": 90.0,
    "trine": 120.0,
    "opposition": 180.0,
}
DEFAULT_ASPECT_ORBS = {name: 6.0 for name in ASPECT_ANGLES}
TROPICAL_SIGNS = (
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio",
    "Sagittarius", "Capricorn", "Aquarius", "Pisces",
)
SUPPORTED_HOUSE_SYSTEMS = frozenset(HOUSE_SYSTEM_NAMES)


def _house_for_longitude(longitude: float, houses: list[dict[str, Any]]) -> int:
    if len(houses) != 12 or not math.isfinite(longitude):
        raise InvalidBirthData("Twelve house cusps and a finite longitude are required")
    target = longitude % 360.0
    cusps = [float(house["cusp_longitude"]) % 360.0 for house in houses]
    for index, start in enumerate(cusps):
        end = cusps[(index + 1) % 12]
        span = (end - start) % 360.0
        offset = (target - start) % 360.0
        if offset < span or math.isclose(offset, 0.0, abs_tol=1e-10):
            return index + 1
    raise InvalidBirthData("House cusps do not define valid longitude sectors")


def _signed_separation(first: float, second: float) -> float:
    return (second - first + 180.0) % 360.0 - 180.0


def calculate_aspects(planets: list[dict[str, Any]], aspect_orbs: dict[str, float] | None = None) -> list[dict[str, Any]]:
    """Find major aspects and classify motion from Swiss longitudinal speeds."""
    orbs = dict(DEFAULT_ASPECT_ORBS)
    if aspect_orbs:
        if set(aspect_orbs) - set(ASPECT_ANGLES):
            raise InvalidBirthData("Only conjunction, sextile, square, trine and opposition orbs are supported")
        try:
            normalized = {name: float(value) for name, value in aspect_orbs.items()}
        except (TypeError, ValueError) as exc:
            raise InvalidBirthData("Aspect orbs must be numeric values") from exc
        if any(not math.isfinite(value) or not 0 <= value <= 15 for value in normalized.values()):
            raise InvalidBirthData("Aspect orbs must be finite values between 0 and 15 degrees")
        orbs.update(normalized)
    aspects: list[dict[str, Any]] = []
    for index, first in enumerate(planets):
        for second in planets[index + 1:]:
            signed = _signed_separation(float(first["longitude"]), float(second["longitude"]))
            relative_speed = None
            if first.get("longitude_speed_deg_per_day") is not None and second.get("longitude_speed_deg_per_day") is not None:
                relative_speed = float(second["longitude_speed_deg_per_day"]) - float(first["longitude_speed_deg_per_day"])
            for name, angle in ASPECT_ANGLES.items():
                targets = (0.0,) if angle == 0 else ((-180.0, 180.0) if angle == 180 else (-angle, angle))
                target = min(targets, key=lambda candidate: abs(signed - candidate))
                signed_orb = signed - target
                orb = abs(signed_orb)
                allowed = orbs[name]
                if orb > allowed and not math.isclose(orb, allowed, abs_tol=1e-12):
                    continue
                if orb <= 1e-9:
                    motion = "exact"
                    applying = False
                elif relative_speed is None or not math.isfinite(relative_speed):
                    motion = "unknown"
                    applying = None
                else:
                    applying = signed_orb * relative_speed < 0
                    motion = "applying" if applying else "separating"
                aspects.append({
                    "planet_a": first["name"],
                    "planet_b": second["name"],
                    "aspect": name,
                    "angle": angle,
                    "separation": min(abs(signed), 360.0 - abs(signed)),
                    "orb": orb,
                    "allowed_orb": allowed,
                    "motion": motion,
                    "applying": applying,
                })
    return aspects


def _position_details(longitude: float) -> dict[str, Any]:
    normalized = longitude % 360.0
    sign_index = int(normalized / 30.0)
    return {
        "longitude": normalized,
        "sign_index": sign_index,
        "sign": TROPICAL_SIGNS[sign_index],
        "degrees_in_sign": normalized % 30.0,
    }


class WesternAstrologyEngine(AstrologyEngine):
    """Tropical natal chart configuration over the shared Swiss Ephemeris provider."""

    def __init__(self, provider: SwissEphemerisProvider | None = None):
        self.provider = provider

    def _provider(self) -> SwissEphemerisProvider:
        if not settings.astrology_calculations_enabled:
            local_agpl = settings.app_env == "development" and settings.astrology_local_agpl_development_enabled
            if not local_agpl:
                raise EngineUnavailable("Astrology calculations are disabled until licensing/runtime verification is completed", reason_code="feature_disabled")
        if not settings.swisseph_license_confirmed and not (
            settings.app_env == "development" and settings.astrology_local_agpl_development_enabled
        ):
            raise EngineUnavailable("Swiss Ephemeris licensing has not been confirmed; public calculations remain disabled", reason_code="license_unconfirmed")
        try:
            return self.provider or SwissEphemerisProvider(settings.swisseph_ephe_path, settings.swisseph_library_path)
        except EphemerisUnavailable as exc:
            raise EngineUnavailable(str(exc), reason_code=ephemeris_failure_code(str(exc))) from exc

    def get_provider(self) -> SwissEphemerisProvider:
        return self._provider()

    def calculate_chart(self, birth_data: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
        limited_chart = birth_data.get("time_accuracy") == "unknown" or birth_data.get("birth_time") is None
        birth_date = birth_data.get("birth_date")
        birth_time = birth_data.get("birth_time")
        try:
            if isinstance(birth_date, str):
                birth_date = date.fromisoformat(birth_date)
            if isinstance(birth_time, str):
                birth_time = time.fromisoformat(birth_time) if birth_time else None
        except ValueError as exc:
            raise InvalidBirthData("Birth date or local birth time has an invalid format") from exc
        if not isinstance(birth_date, date):
            raise InvalidBirthData("A valid birth date is required")
        if limited_chart:
            utc = local_birth_time_to_utc(birth_date, time(12, 0), birth_data.get("timezone"))
        else:
            if not isinstance(birth_time, time):
                raise InvalidBirthData("A valid local birth time is required")
            utc = local_birth_time_to_utc(birth_date, birth_time, birth_data.get("timezone"))
        latitude = birth_data.get("latitude")
        longitude = birth_data.get("longitude")
        try:
            latitude, longitude = float(latitude), float(longitude)
        except (TypeError, ValueError) as exc:
            raise InvalidBirthData("Birth latitude and longitude are required numeric coordinates") from exc
        house_system = config.get("house_system", "P")
        if house_system not in SUPPORTED_HOUSE_SYSTEMS:
            choices = ", ".join(f"{code} ({name})" for code, name in HOUSE_SYSTEM_NAMES.items())
            raise UnsupportedHouseSystem(f"Unsupported house system {house_system!r}. Supported systems: {choices}")
        provider = self._provider()
        try:
            result = provider.calculate(utc, latitude, longitude, "tropical", house_system)
        except UnsupportedHouseSystem:
            raise
        except EphemerisUnavailable as exc:
            raise EngineUnavailable(str(exc), reason_code=ephemeris_failure_code(str(exc))) from exc

        planets = [dict(planet) for planet in result["planets"]]
        for planet in planets:
            planet.update(_position_details(float(planet["longitude"])))
            if not limited_chart:
                planet["house"] = _house_for_longitude(planet["longitude"], result["houses"])
            else:
                planet["position_time_assumption"] = "local_noon_estimate"
        aspect_orbs = dict(DEFAULT_ASPECT_ORBS)
        aspect_orbs.update(config.get("aspect_orbs") or {})
        aspects = calculate_aspects(planets, aspect_orbs)
        result["planets"] = planets
        if limited_chart:
            result["houses"] = []
            result["ascendant"] = None
            result["midheaven"] = None
            result.pop("ascendant_longitude", None)
            result.pop("midheaven_longitude", None)
        else:
            ascendant = _position_details(float(result["ascendant_longitude"]))
            ascendant["house"] = _house_for_longitude(ascendant["longitude"], result["houses"])
            midheaven = _position_details(float(result["midheaven_longitude"]))
            result["houses"] = [
                {**house, **_position_details(float(house["cusp_longitude"]))}
                for house in result["houses"]
            ]
            result["ascendant"] = ascendant
            result["midheaven"] = midheaven
        result["aspects"] = aspects
        result["calculation_system"] = "western"
        result["western_engine_version"] = WESTERN_ENGINE_VERSION
        result["time_accuracy"] = birth_data.get("time_accuracy")
        result["calculation_mode"] = "limited_date_only" if limited_chart else "full_timed"
        result["precision_note"] = (
            "Birth time unknown: planetary positions and aspects are estimated for local noon on the recorded date. "
            "Houses, Ascendant and Midheaven are omitted."
            if limited_chart else
            "Approximate birth time; angles and house cusps inherit the supplied time uncertainty." if birth_data.get("time_accuracy") == "approximate" else None
        )
        result["configuration"] = {
            "zodiac": "tropical",
            "house_system": None if limited_chart else house_system,
            "aspect_orbs": aspect_orbs,
            "aspect_motion_method": "relative geocentric ecliptic longitude speed",
            **({"time_assumption": "local_noon_estimate"} if limited_chart else {"house_system_name": HOUSE_SYSTEM_NAMES[house_system]}),
        }
        return result

    def calculate_planetary_positions(self, birth_data: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
        return self.calculate_chart(birth_data, config)["planets"]

    def calculate_houses(self, birth_data: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
        return self.calculate_chart(birth_data, config)["houses"]

    def calculate_transits(self, birth_data: dict[str, Any], at_time: str, config: dict[str, Any]) -> dict[str, Any]:
        raise EngineUnavailable("Transits are outside this calculation phase")

    def calculate_compatibility(self, first: dict[str, Any], second: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
        raise EngineUnavailable("Compatibility is outside this calculation phase")
