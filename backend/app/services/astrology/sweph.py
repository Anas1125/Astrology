"""Low-level Swiss Ephemeris provider; imported lazily and replaceable at the adapter boundary."""
from __future__ import annotations

from datetime import date, datetime, time, timezone
from importlib import import_module
import math
import os
from pathlib import Path
import hashlib
from threading import RLock
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


ENGINE_VERSION = "astroai-swe-provider/1.0.0"
PLANETS = (
    ("Sun", "SE_SUN"), ("Moon", "SE_MOON"), ("Mercury", "SE_MERCURY"),
    ("Venus", "SE_VENUS"), ("Mars", "SE_MARS"), ("Jupiter", "SE_JUPITER"),
    ("Saturn", "SE_SATURN"), ("Uranus", "SE_URANUS"), ("Neptune", "SE_NEPTUNE"),
    ("Pluto", "SE_PLUTO"),
)
NAKSHATRAS = (
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashirsha", "Ardra", "Punarvasu",
    "Pushya", "Ashlesha", "Magha", "Purva Phalguni", "Uttara Phalguni", "Hasta",
    "Chitra", "Swati", "Vishakha", "Anuradha", "Jyeshtha", "Mula",
    "Purva Ashadha", "Uttara Ashadha", "Shravana", "Dhanishta", "Shatabhisha",
    "Purva Bhadrapada", "Uttara Bhadrapada", "Revati",
)
RASHIS = (
    "Mesha", "Vrishabha", "Mithuna", "Karka", "Simha", "Kanya", "Tula", "Vrischika",
    "Dhanu", "Makara", "Kumbha", "Meena",
)
NAKSHATRA_LORDS = ("Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury")
NAKSHATRA_LORD_YEARS = (7, 20, 6, 10, 7, 18, 16, 19, 17)


class EphemerisUnavailable(RuntimeError):
    pass


class InvalidBirthData(ValueError):
    pass


class UnsupportedHouseSystem(InvalidBirthData):
    """The requested house system cannot be calculated for this input."""


def local_birth_time_to_utc(birth_date: date, birth_time: time | None, timezone_name: str | None) -> datetime:
    if birth_time is None:
        raise InvalidBirthData("Birth time is missing; chart angles and houses cannot be calculated")
    if not timezone_name:
        raise InvalidBirthData("An IANA timezone is required to convert the local birth time")
    if birth_time.tzinfo is not None:
        raise InvalidBirthData("Birth time must be a local wall-clock time without a UTC offset")
    try:
        tz = ZoneInfo(timezone_name)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise InvalidBirthData("Unknown IANA timezone identifier") from exc

    local_naive = datetime.combine(birth_date, birth_time)
    candidates: list[datetime] = []
    for fold in (0, 1):
        candidate = local_naive.replace(tzinfo=tz, fold=fold)
        round_trip = candidate.astimezone(timezone.utc).astimezone(tz).replace(tzinfo=None)
        if round_trip == local_naive:
            utc_candidate = candidate.astimezone(timezone.utc)
            if utc_candidate not in candidates:
                candidates.append(utc_candidate)
    if not candidates:
        raise InvalidBirthData("Local birth time does not exist because of a daylight-saving transition")
    if len(candidates) > 1:
        raise InvalidBirthData("Local birth time is ambiguous because of a daylight-saving transition")
    return candidates[0]


def julian_day_from_utc(instant: datetime) -> float:
    """Gregorian UT Julian Day, independent of Swiss Ephemeris library state."""
    if instant.tzinfo is None:
        raise ValueError("UTC instant must be timezone-aware")
    value = instant.astimezone(timezone.utc)
    year, month = value.year, value.month
    if month <= 2:
        year -= 1
        month += 12
    century = year // 100
    correction = 2 - century + century // 4
    day_fraction = (value.hour + value.minute / 60 + value.second / 3600 + value.microsecond / 3_600_000_000) / 24
    return (int(365.25 * (year + 4716)) + int(30.6001 * (month + 1)) + value.day + day_fraction + correction - 1524.5)


def nakshatra_details(sidereal_longitude: float) -> dict[str, Any]:
    if not isinstance(sidereal_longitude, (int, float)) or not 0 <= float(sidereal_longitude) <= 360:
        raise InvalidBirthData("Sidereal longitude must be a finite value between 0 and 360 degrees")
    longitude = sidereal_longitude % 360.0
    span = 360.0 / 27.0
    pada_span = span / 4.0
    scaled = longitude / span
    nearest_boundary = round(scaled)
    if math.isclose(scaled, nearest_boundary, rel_tol=0.0, abs_tol=1e-12):
        scaled = float(nearest_boundary)
    index = min(26, int(scaled))
    within = max(0.0, longitude - index * span)
    lord_index = index % len(NAKSHATRA_LORDS)
    return {
        "index": index + 1,
        "name": NAKSHATRAS[index],
        "pada": min(4, int(min(3.0, math.floor(within / pada_span + 1e-12))) + 1),
        "lord": NAKSHATRA_LORDS[lord_index],
        "remaining_fraction": max(0.0, min(1.0, (span - within) / span)),
        "degrees_remaining": span - within,
        "rashi": RASHIS[int(longitude / 30.0)],
        "degrees_in_rashi": longitude % 30.0,
    }


class SwissEphemerisProvider:
    """Strict Swiss Ephemeris C API wrapper. It never permits Moshier fallback."""

    def __init__(self, ephemeris_path: str | None, library_path: str | None = None, ffi_module=None):
        if not ephemeris_path:
            raise EphemerisUnavailable("Set SWISSEPH_EPHE_PATH to a directory containing Swiss Ephemeris files")
        path = Path(ephemeris_path).expanduser().resolve()
        if not path.is_dir() or not any(path.glob("*.se1")):
            raise EphemerisUnavailable(f"Swiss Ephemeris data files are missing from {path}")
        resolved_library_path = (
            str(Path(library_path).expanduser().resolve()) if library_path else None
        )
        try:
            self.ffi = ffi_module or import_module("swisseph_ffi")
            self.swe = self.ffi.SwissEph(library_path=resolved_library_path)
        except Exception as exc:
            library_error = getattr(getattr(self, "ffi", None), "SwissEphLibraryNotFoundError", None)
            known_load_error = isinstance(exc, (ImportError, OSError, AttributeError, RuntimeError))
            wrapper_load_error = isinstance(library_error, type) and isinstance(exc, library_error)
            if not (known_load_error or wrapper_load_error):
                raise
            raise EphemerisUnavailable(
                "Install the optional backend extra `.[astrology]` and ensure the native library loads"
            ) from exc
        self.ephemeris_path = str(path)
        self.swe.swe_set_ephe_path(os.fsencode(path))
        version_buffer = self.ffi.create_string_buffer(32)
        self.swe.swe_version(version_buffer)
        library_version = version_buffer.value.decode("ascii", errors="replace")
        file_manifest = sorted((item.name, item.stat().st_size, item.stat().st_mtime_ns) for item in path.glob("*.se1"))
        self.ephemeris_version = f"{library_version}+{hashlib.sha256(repr(file_manifest).encode()).hexdigest()[:12]}"
        self._lock = RLock()

    def calculate(self, utc_instant: datetime, latitude: float, longitude: float, zodiac: str, house_system: str, ayanamsa: str | None = None) -> dict[str, Any]:
        if not -90 <= latitude <= 90:
            raise InvalidBirthData("Latitude must be between -90 and 90 degrees")
        if not -180 <= longitude <= 180:
            raise InvalidBirthData("Longitude must be between -180 and 180 degrees")
        if house_system not in {"P", "W", "K", "R", "C", "E", "O", "B", "M", "A", "V", "X", "H", "T"}:
            raise InvalidBirthData("Unsupported Swiss Ephemeris house-system code")
        if zodiac not in {"tropical", "sidereal"}:
            raise ValueError("zodiac must be tropical or sidereal")
        with self._lock:
            constants = self.ffi
            sidereal = zodiac == "sidereal"
            if sidereal:
                if ayanamsa != "lahiri":
                    raise ValueError("Only the Lahiri ayanamsa is configured in this phase")
                self.swe.swe_set_sid_mode(constants.SE_SIDM_LAHIRI, 0.0, 0.0)
            utc = utc_instant.astimezone(timezone.utc)
            decimal_hour = utc.hour + utc.minute / 60 + utc.second / 3600 + utc.microsecond / 3_600_000_000
            jd_ut = self.swe.swe_julday(utc.year, utc.month, utc.day, decimal_hour, constants.SE_GREG_CAL)
            julian_reference = julian_day_from_utc(utc)
            if abs(jd_ut - julian_reference) > 2e-7:
                raise EphemerisUnavailable("Swiss Ephemeris Julian Day disagrees with the independent Gregorian conversion")
            requested_flags = constants.SEFLG_SWIEPH | constants.SEFLG_SPEED
            if sidereal:
                requested_flags |= constants.SEFLG_SIDEREAL
            planets: list[dict[str, Any]] = []
            for name, constant_name in PLANETS:
                xx = (constants.c_double * 6)()
                error = constants.create_string_buffer(256)
                returned_flags = self.swe.swe_calc_ut(jd_ut, getattr(constants, constant_name), requested_flags, xx, error)
                if error.value:
                    raise EphemerisUnavailable(error.value.decode("utf-8", errors="replace"))
                if returned_flags < 0 or returned_flags & constants.SEFLG_SWIEPH == 0 or returned_flags & constants.SEFLG_MOSEPH:
                    raise EphemerisUnavailable(f"Swiss Ephemeris files unavailable for {name}; fallback calculation was refused")
                row = {
                    "name": name,
                    "longitude": float(xx[0] % 360.0),
                    "latitude": float(xx[1]),
                    "distance_au": float(xx[2]),
                    "longitude_speed_deg_per_day": float(xx[3]),
                    "retrograde": float(xx[3]) < 0,
                    "latitude_speed_deg_per_day": float(xx[4]),
                    "distance_speed_au_per_day": float(xx[5]),
                    "flags": int(returned_flags),
                }
                planets.append(row)
            cusps = (constants.c_double * 13)()
            ascmc = (constants.c_double * 10)()
            house_flags = constants.SEFLG_SIDEREAL if sidereal else 0
            house_error = self.swe.swe_houses_ex(jd_ut, house_flags, latitude, longitude, ord(house_system), cusps, ascmc)
            if house_error < 0:
                raise UnsupportedHouseSystem(
                    f"Swiss Ephemeris could not calculate {house_system} houses for this date and location; "
                    "try Whole Sign (W) or Equal (E) houses"
                )
            houses = [{"number": index, "cusp_longitude": float(cusps[index] % 360.0)} for index in range(1, 13)]
            result: dict[str, Any] = {
                "julian_day_ut": float(jd_ut),
                "utc_datetime": utc.isoformat(),
                "zodiac": zodiac,
                "house_system": house_system,
                "calculation_flags": {"requested": requested_flags, "houses": house_flags, "apparent": True, "geocentric": True, "ephemeris": "SWIEPH"},
                "planets": planets,
                "houses": houses,
                "ascendant_longitude": float(ascmc[constants.SE_ASC] % 360.0),
                "midheaven_longitude": float(ascmc[constants.SE_MC] % 360.0),
                "ephemeris_version": self.ephemeris_version,
                "engine_version": ENGINE_VERSION,
            }
            if sidereal:
                result["ayanamsa"] = float(self.swe.swe_get_ayanamsa_ut(jd_ut))
            return result
