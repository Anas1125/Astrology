"""Vedic chart derivations over the provider-independent Swiss astronomy adapter."""
from __future__ import annotations

from datetime import date, datetime, time, timedelta
import math
from typing import Any

from app.core.config import settings
from app.services.astrology.base import AstrologyEngine, EngineUnavailable, ephemeris_failure_code
from app.services.astrology.sweph import (
    EphemerisUnavailable,
    InvalidBirthData,
    NAKSHATRA_LORDS,
    NAKSHATRA_LORD_YEARS,
    RASHIS,
    SwissEphemerisProvider,
    local_birth_time_to_utc,
    nakshatra_details,
)

VEDIC_ENGINE_VERSION = "astroai-vedic/1.0.0"
SAVANA_YEAR_DAYS = 360
NAVAMSA_WIDTH = 30.0 / 9.0
_RASHI_INDEX = {name: index for index, name in enumerate(RASHIS)}
_LORD_YEARS = dict(zip(NAKSHATRA_LORDS, NAKSHATRA_LORD_YEARS))


def rashi_index(longitude: float) -> int:
    if not math.isfinite(longitude):
        raise InvalidBirthData("Longitude must be finite")
    return int((longitude % 360.0) / 30.0)


def navamsa_details(longitude: float) -> dict[str, Any]:
    """Map a sidereal longitude to D9 using movable/fixed/dual sign starts."""
    if not math.isfinite(longitude):
        raise InvalidBirthData("Longitude must be finite")
    normalized = longitude % 360.0
    sign = int(normalized / 30.0)
    within_sign = normalized - sign * 30.0
    scaled_segment = within_sign * 9.0 / 30.0
    nearest_boundary = round(scaled_segment)
    if math.isclose(scaled_segment, nearest_boundary, rel_tol=0.0, abs_tol=1e-12):
        scaled_segment = float(nearest_boundary)
    segment = min(8, int(scaled_segment))
    modality = sign % 3  # Aries, Taurus, Gemini repeat movable/fixed/dual.
    start_sign = sign if modality == 0 else (sign + (8 if modality == 1 else 4)) % 12
    navamsa_sign = (start_sign + segment) % 12
    segment_offset = within_sign - segment * NAVAMSA_WIDTH
    return {
        "segment": segment + 1,
        "rashi_index": navamsa_sign,
        "rashi": RASHIS[navamsa_sign],
        "longitude": (navamsa_sign * 30.0 + segment_offset * 9.0) % 360.0,
    }


def house_for_longitude(longitude: float, cusps: list[dict[str, Any]]) -> int:
    """Return the house sector between successive configured cusp longitudes."""
    if len(cusps) != 12 or not math.isfinite(longitude):
        raise InvalidBirthData("Twelve house cusps and a finite longitude are required")
    target = longitude % 360.0
    values = [float(cusp["cusp_longitude"]) % 360.0 for cusp in cusps]
    for index, start in enumerate(values):
        end = values[(index + 1) % 12]
        span = (end - start) % 360.0
        offset = (target - start) % 360.0
        if offset < span or math.isclose(offset, 0.0, abs_tol=1e-10):
            return index + 1
    # Degenerate cusp data is an engine error, never an invented house.
    raise InvalidBirthData("House cusps do not form valid longitude sectors")


def vimshottari_dasha(moon_longitude: float, birth_utc: datetime, year_convention: str = "savana_360_day") -> dict[str, Any]:
    if year_convention != "savana_360_day":
        raise InvalidBirthData("Only the explicitly configured 360-day Savana year is supported")
    if birth_utc.tzinfo is None:
        raise InvalidBirthData("Dasha birth instant must be timezone-aware")
    details = nakshatra_details(moon_longitude)
    first_index = NAKSHATRA_LORDS.index(details["lord"])
    cycle = list(NAKSHATRA_LORDS[first_index:] + NAKSHATRA_LORDS[:first_index])
    first_years = _LORD_YEARS[cycle[0]]
    elapsed_fraction = 1.0 - details["remaining_fraction"]
    first_period_days = first_years * SAVANA_YEAR_DAYS
    elapsed_days = first_period_days * elapsed_fraction
    first_nominal_start = birth_utc - timedelta(days=elapsed_days)
    cursor = birth_utc
    mahadashas: list[dict[str, Any]] = []
    antardashas: list[dict[str, Any]] = []
    pratyantardashas: list[dict[str, Any]] = []
    total_vimshottari_years = sum(NAKSHATRA_LORD_YEARS)

    for md_index, lord in enumerate(cycle):
        full_days = _LORD_YEARS[lord] * SAVANA_YEAR_DAYS
        nominal_start = first_nominal_start if md_index == 0 else cursor
        nominal_end = nominal_start + timedelta(days=full_days)
        md_start = birth_utc if md_index == 0 else nominal_start
        md_end = nominal_end
        mahadashas.append({
            "lord": lord,
            "start": md_start.isoformat(),
            "nominal_start": nominal_start.isoformat(),
            "end": md_end.isoformat(),
            "full_duration_days": full_days,
            "full_duration_years": _LORD_YEARS[lord],
            "balance_days_at_birth": max(0.0, (md_end - birth_utc).total_seconds() / 86400) if md_index == 0 else None,
        })

        ad_cycle = list(NAKSHATRA_LORDS[NAKSHATRA_LORDS.index(lord):] + NAKSHATRA_LORDS[:NAKSHATRA_LORDS.index(lord)])
        ad_cursor = nominal_start
        for ad_lord in ad_cycle:
            ad_days = full_days * _LORD_YEARS[ad_lord] / total_vimshottari_years
            ad_end = ad_cursor + timedelta(days=ad_days)
            if ad_end > birth_utc:
                visible_start = max(ad_cursor, birth_utc)
                antardashas.append({
                    "mahadasha_lord": lord,
                    "lord": ad_lord,
                    "start": visible_start.isoformat(),
                    "nominal_start": ad_cursor.isoformat(),
                    "end": ad_end.isoformat(),
                    "full_duration_days": ad_days,
                    "elapsed_days_at_birth": max(0.0, (birth_utc - ad_cursor).total_seconds() / 86400) if ad_cursor < birth_utc else 0.0,
                    "remaining_days_at_birth": max(0.0, (ad_end - birth_utc).total_seconds() / 86400) if ad_cursor < birth_utc else None,
                })
            pd_cycle = list(NAKSHATRA_LORDS[NAKSHATRA_LORDS.index(ad_lord):] + NAKSHATRA_LORDS[:NAKSHATRA_LORDS.index(ad_lord)])
            pd_cursor = ad_cursor
            for pd_lord in pd_cycle:
                pd_days = ad_days * _LORD_YEARS[pd_lord] / total_vimshottari_years
                pd_end = pd_cursor + timedelta(days=pd_days)
                if pd_end > birth_utc:
                    pratyantardashas.append({
                        "mahadasha_lord": lord,
                        "antardasha_lord": ad_lord,
                        "lord": pd_lord,
                        "start": max(pd_cursor, birth_utc).isoformat(),
                        "nominal_start": pd_cursor.isoformat(),
                        "end": pd_end.isoformat(),
                        "full_duration_days": pd_days,
                        "elapsed_days_at_birth": max(0.0, (birth_utc - pd_cursor).total_seconds() / 86400) if pd_cursor < birth_utc else 0.0,
                        "remaining_days_at_birth": max(0.0, (pd_end - birth_utc).total_seconds() / 86400) if pd_cursor < birth_utc else None,
                    })
                pd_cursor = pd_end
            ad_cursor = ad_end
        cursor = nominal_end

    return {
        "system": "vimshottari",
        "year_convention": year_convention,
        "year_length_days": SAVANA_YEAR_DAYS,
        "starting_nakshatra": details["name"],
        "starting_lord": cycle[0],
        "birth_nakshatra_remaining_fraction": details["remaining_fraction"],
        "birth_balance_days": mahadashas[0]["balance_days_at_birth"],
        "mahadashas": mahadashas,
        "antardashas": antardashas,
        "pratyantardashas": pratyantardashas,
    }


class VedicAstrologyEngine(AstrologyEngine):
    """Vedic chart configuration over the shared Swiss Ephemeris provider."""

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
        provider = self._provider()
        birth_date = birth_data.get("birth_date")
        if isinstance(birth_date, str):
            try:
                birth_date = date.fromisoformat(birth_date)
            except ValueError as exc:
                raise InvalidBirthData("Birth date has an invalid format") from exc
        if not isinstance(birth_date, date):
            raise InvalidBirthData("A valid birth date is required")
        if limited_chart:
            if config.get("division", "D1") != "D1":
                raise InvalidBirthData("D9 Navamsa requires a known birth time; use D1 Rashi for a date-only chart")
            utc = local_birth_time_to_utc(birth_date, time(12, 0), birth_data.get("timezone"))
        else:
            birth_time = birth_data["birth_time"]
            if isinstance(birth_time, str):
                try:
                    birth_time = time.fromisoformat(birth_time)
                except ValueError as exc:
                    raise InvalidBirthData("Birth time has an invalid format") from exc
            utc = local_birth_time_to_utc(birth_date, birth_time, birth_data.get("timezone"))
        house_system = config.get("house_system", "P")
        division = config.get("division", "D1")
        if division not in {"D1", "D9"}:
            raise InvalidBirthData("Supported Vedic divisions are D1 and D9")
        if birth_data.get("latitude") is None or birth_data.get("longitude") is None:
            raise InvalidBirthData("Birth latitude and longitude are required")
        try:
            result = provider.calculate(utc, float(birth_data["latitude"]), float(birth_data["longitude"]), "sidereal", house_system, "lahiri")
        except EphemerisUnavailable as exc:
            raise EngineUnavailable(str(exc), reason_code=ephemeris_failure_code(str(exc))) from exc
        planets = [dict(planet) for planet in result["planets"]]
        # Mean lunar node is used consistently; Ketu is exactly opposite Rahu.
        ffi = getattr(provider, "ffi", None)
        if ffi is None or not hasattr(ffi, "SE_MEAN_NODE"):
            raise EngineUnavailable("The configured Swiss Ephemeris binding lacks SE_MEAN_NODE for Rahu")
        node_flags = result["calculation_flags"]["requested"]
        node_values = (ffi.c_double * 6)()
        error = ffi.create_string_buffer(256)
        returned = provider.swe.swe_calc_ut(result["julian_day_ut"], ffi.SE_MEAN_NODE, node_flags, node_values, error)
        if error.value or returned < 0 or returned & ffi.SEFLG_SWIEPH == 0 or returned & ffi.SEFLG_MOSEPH:
            message = error.value.decode("utf-8", errors="replace") if error.value else "Swiss ephemeris files unavailable for lunar node; fallback calculation was refused"
            raise EngineUnavailable(message)
        rahu_lon = float(node_values[0] % 360.0)
        planets.extend([
            {"name": "Rahu", "longitude": rahu_lon, "latitude": float(node_values[1]), "distance_au": float(node_values[2]), "longitude_speed_deg_per_day": float(node_values[3]), "retrograde": float(node_values[3]) < 0, "latitude_speed_deg_per_day": float(node_values[4]), "distance_speed_au_per_day": float(node_values[5]), "flags": int(returned), "node_model": "mean"},
            {"name": "Ketu", "longitude": (rahu_lon + 180.0) % 360.0, "latitude": -float(node_values[1]), "distance_au": float(node_values[2]), "longitude_speed_deg_per_day": float(node_values[3]), "retrograde": float(node_values[3]) < 0, "flags": int(returned), "node_model": "mean_opposite"},
        ])

        for planet in planets:
            nakshatra = nakshatra_details(planet["longitude"])
            planet["nakshatra"] = nakshatra
            planet.update({f"nakshatra_{key}": value for key, value in nakshatra.items() if key != "name"})
            planet["nakshatra_name"] = nakshatra["name"]
            planet["rashi"] = nakshatra["rashi"]
            planet["degrees_in_rashi"] = nakshatra["degrees_in_rashi"]
            planet["rashi_index"] = _RASHI_INDEX[planet["rashi"]]
            if not limited_chart:
                planet["house"] = house_for_longitude(planet["longitude"], result["houses"])
                planet["d9"] = navamsa_details(planet["longitude"])
            else:
                planet["position_time_assumption"] = "local_noon_estimate"
        result["planets"] = planets

        if limited_chart:
            # No Ascendant, house cusps, divisional chart or birth-time-based dasha is inferred.
            result["houses"] = []
            result["division_houses"] = []
            result["ascendant"] = None
            result["midheaven"] = None
            result.pop("ascendant_longitude", None)
            result.pop("midheaven_longitude", None)
            for planet in planets:
                planet["division_longitude"] = planet["longitude"]
                planet["division_rashi"] = planet["rashi"]
                planet["division_rashi_index"] = planet["rashi_index"]
        else:
            asc = {"longitude": result["ascendant_longitude"], **nakshatra_details(result["ascendant_longitude"])}
            asc["rashi_index"] = _RASHI_INDEX[asc["rashi"]]
            asc["d9"] = navamsa_details(result["ascendant_longitude"])
            result["ascendant"] = asc
            result["midheaven"] = {"longitude": result["midheaven_longitude"], **nakshatra_details(result["midheaven_longitude"])}
            if division == "D9":
                d9_cusps = [dict(cusp, cusp_longitude=navamsa_details(cusp["cusp_longitude"])["longitude"]) for cusp in result["houses"]]
                for planet in planets:
                    planet["division_longitude"] = planet["d9"]["longitude"]
                    planet["division_rashi"] = planet["d9"]["rashi"]
                    planet["division_rashi_index"] = planet["d9"]["rashi_index"]
                    planet["division_house"] = house_for_longitude(planet["division_longitude"], d9_cusps)
                asc["division_longitude"] = asc["d9"]["longitude"]
                asc["division_rashi"] = asc["d9"]["rashi"]
                asc["division_house"] = house_for_longitude(asc["division_longitude"], d9_cusps)
                result["division_houses"] = [{**cusp, "rashi": RASHIS[int(cusp["cusp_longitude"] / 30.0)]} for cusp in d9_cusps]
            else:
                for planet in planets:
                    planet["division_longitude"] = planet["longitude"]
                    planet["division_rashi"] = planet["rashi"]
                    planet["division_rashi_index"] = planet["rashi_index"]
                    planet["division_house"] = planet["house"]
                asc["division_longitude"] = asc["longitude"]
                asc["division_rashi"] = asc["rashi"]
                asc["division_house"] = house_for_longitude(asc["longitude"], result["houses"])
                result["division_houses"] = result["houses"]

        result["calculation_system"] = "vedic"
        result["division"] = division
        result["ayanamsa_name"] = "Lahiri"
        result["time_accuracy"] = birth_data.get("time_accuracy")
        result["calculation_mode"] = "limited_date_only" if limited_chart else "full_timed"
        result["precision_note"] = (
            "Birth time unknown: planetary positions are estimated for local noon on the recorded date. "
            "Sign and nakshatra details near a transition may differ; Ascendant, houses, D9 and Vimshottari dasha are omitted."
            if limited_chart else
            "Approximate birth time; angles and house cusps inherit the supplied time uncertainty." if birth_data.get("time_accuracy") == "approximate" else None
        )
        if not limited_chart:
            year_convention = config.get("dasha_year_convention", "savana_360_day")
            result["vimshottari_dasha"] = vimshottari_dasha(next(p["longitude"] for p in planets if p["name"] == "Moon"), utc, year_convention)
        result["configuration"] = {
            "zodiac": "sidereal", "ayanamsa": "lahiri", "house_system": None if limited_chart else house_system,
            "division": division, "node_model": "mean",
            **({"time_assumption": "local_noon_estimate"} if limited_chart else {"dasha_year_convention": config.get("dasha_year_convention", "savana_360_day"), "d9_house_convention": "configured house cusps transformed into navamsa"}),
        }
        result["vedic_engine_version"] = VEDIC_ENGINE_VERSION
        return result

    def calculate_planetary_positions(self, birth_data: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
        return self.calculate_chart(birth_data, config)["planets"]

    def calculate_houses(self, birth_data: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
        return self.calculate_chart(birth_data, config)["houses"]

    def calculate_transits(self, birth_data: dict[str, Any], at_time: str, config: dict[str, Any]) -> dict[str, Any]:
        raise EngineUnavailable("Transits are outside this calculation phase")

    def calculate_compatibility(self, first: dict[str, Any], second: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
        raise EngineUnavailable("Compatibility is outside this calculation phase")
