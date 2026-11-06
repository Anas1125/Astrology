"""Location-aware Panchang day elements using the shared strict Swiss runtime.

This module deliberately exposes only the elements running at Hindu sunrise.
It does not calculate festivals, muhurta, or predictive interpretations.
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
import math
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.services.astrology.sweph import InvalidBirthData, SwissEphemerisProvider

PANCHANG_ENGINE_VERSION = "astroai-panchang/1.0.0"
_TITHI_NAMES = (
    "Pratipada", "Dvitiya", "Tritiya", "Chaturthi", "Panchami", "Shashthi", "Saptami",
    "Ashtami", "Navami", "Dashami", "Ekadashi", "Dwadashi", "Trayodashi", "Chaturdashi",
    "Purnima", "Pratipada", "Dvitiya", "Tritiya", "Chaturthi", "Panchami", "Shashthi",
    "Saptami", "Ashtami", "Navami", "Dashami", "Ekadashi", "Dwadashi", "Trayodashi",
    "Chaturdashi", "Amavasya",
)
_NAKSHATRA_NAMES = (
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashirsha", "Ardra", "Punarvasu", "Pushya",
    "Ashlesha", "Magha", "Purva Phalguni", "Uttara Phalguni", "Hasta", "Chitra", "Swati",
    "Vishakha", "Anuradha", "Jyeshtha", "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana",
    "Dhanishta", "Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada", "Revati",
)
_YOGA_NAMES = (
    "Vishkambha", "Priti", "Ayushman", "Saubhagya", "Shobhana", "Atiganda", "Sukarma", "Dhriti",
    "Shula", "Ganda", "Vriddhi", "Dhruva", "Vyaghata", "Harshana", "Vajra", "Siddhi", "Vyatipata",
    "Variyana", "Parigha", "Shiva", "Siddha", "Sadhya", "Shubha", "Shukla", "Brahma", "Indra", "Vaidhriti",
)
_REPEATING_KARANAS = ("Bava", "Balava", "Kaulava", "Taitila", "Garaja", "Vanija", "Vishti")
_WEEKDAYS = ("Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday")
# Daytime eighths used by the commonly published Indian Panchang convention.
# Values are one-based parts counted from local sunrise.
_DAYTIME_SEGMENTS = {
    "rahu_kalam": (8, 2, 7, 5, 6, 4, 3),
    "yamagandam": (5, 4, 3, 2, 1, 7, 6),
    "gulika_kalam": (7, 6, 5, 4, 3, 2, 1),
}


class PanchangUnavailable(RuntimeError):
    """The requested local day has no usable sunrise or Swiss result."""


def daytime_windows(sunrise: datetime, sunset: datetime, weekday_index: int) -> dict[str, dict[str, str | int]]:
    """Return conventional daytime intervals from sunrise-to-sunset divisions.

    Arithmetic is performed in UTC so DST transitions and varying local UTC
    offsets cannot distort the elapsed solar-day duration.
    """
    if sunrise.tzinfo is None or sunset.tzinfo is None or not 0 <= weekday_index <= 6:
        raise InvalidBirthData("Aware sunrise/sunset and a weekday index from 0 to 6 are required")
    start_utc, end_utc = sunrise.astimezone(timezone.utc), sunset.astimezone(timezone.utc)
    duration = end_utc - start_utc
    if duration.total_seconds() <= 0:
        raise PanchangUnavailable("Sunset must follow sunrise")
    zone = sunrise.tzinfo

    def interval(part: int, divisions: int) -> dict[str, str | int]:
        start = start_utc + duration * ((part - 1) / divisions)
        end = start_utc + duration * (part / divisions)
        return {"part": part, "parts_in_daylight": divisions,
                "start": start.astimezone(zone).isoformat(), "end": end.astimezone(zone).isoformat()}

    values = {name: interval(parts[weekday_index], 8) for name, parts in _DAYTIME_SEGMENTS.items()}
    # The eighth of fifteen equal daylight muhurtas straddles the solar day
    # midpoint. We expose the interval only, not an auspiciousness claim.
    values["abhijit_muhurta"] = interval(8, 15)
    return values


def _utc_julian_day(provider: SwissEphemerisProvider, instant: datetime) -> float:
    utc = instant.astimezone(timezone.utc)
    hour = utc.hour + utc.minute / 60 + utc.second / 3600 + utc.microsecond / 3_600_000_000
    return float(provider.swe.swe_julday(utc.year, utc.month, utc.day, hour, provider.ffi.SE_GREG_CAL))


def _julian_day_to_utc(value: float) -> datetime:
    return datetime(1970, 1, 1, tzinfo=timezone.utc) + timedelta(days=value - 2440587.5)


def _local_midnight(day: date, timezone_name: str) -> datetime:
    try:
        zone = ZoneInfo(timezone_name)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise InvalidBirthData("Unknown IANA timezone identifier") from exc
    local = datetime.combine(day, time.min).replace(tzinfo=zone, fold=0)
    if local.astimezone(timezone.utc).astimezone(zone).replace(tzinfo=None) != local.replace(tzinfo=None):
        raise InvalidBirthData("Local midnight does not exist for this date and timezone")
    return local


def _solar_event(provider: SwissEphemerisProvider, start_jd: float, latitude: float, longitude: float, event_flag: int) -> float:
    ffi = provider.ffi
    geopos = (ffi.c_double * 3)(longitude, latitude, 0.0)
    result = (ffi.c_double * 1)()
    error = ffi.create_string_buffer(256)
    # The ephemeris manual defines Hindu sunrise as the Sun's centre at the
    # horizon without refraction, using the geocentric position and ignoring
    # the Sun's small ecliptic latitude.
    flags = event_flag | ffi.SE_BIT_HINDU_RISING
    code = provider.swe.swe_rise_trans(
        start_jd, ffi.SE_SUN, None, ffi.SEFLG_SWIEPH, flags, geopos, 0.0, 15.0, result, error,
    )
    if code != 0 or not math.isfinite(result[0]) or result[0] <= 0:
        detail = error.value.decode("utf-8", errors="replace") if error.value else "sunrise or sunset was not found"
        raise PanchangUnavailable(detail)
    return float(result[0])


def _sidereal_sun_moon(provider: SwissEphemerisProvider, jd_ut: float) -> tuple[float, float]:
    ffi = provider.ffi
    provider.swe.swe_set_sid_mode(ffi.SE_SIDM_LAHIRI, 0.0, 0.0)
    flags = ffi.SEFLG_SWIEPH | ffi.SEFLG_SPEED | ffi.SEFLG_SIDEREAL
    longitudes: list[float] = []
    for body in (ffi.SE_SUN, ffi.SE_MOON):
        values = (ffi.c_double * 6)()
        error = ffi.create_string_buffer(256)
        returned_flags = provider.swe.swe_calc_ut(jd_ut, body, flags, values, error)
        if error.value or returned_flags < 0 or returned_flags & ffi.SEFLG_SWIEPH == 0 or returned_flags & ffi.SEFLG_MOSEPH:
            raise PanchangUnavailable("Swiss Ephemeris file calculation failed; fallback calculation was refused")
        if not math.isfinite(values[0]):
            raise PanchangUnavailable("Swiss Ephemeris returned an invalid longitude")
        longitudes.append(float(values[0] % 360))
    return longitudes[0], longitudes[1]


def _karana_name(half_tithi_index: int) -> str:
    if half_tithi_index == 0:
        return "Kimstughna"
    if half_tithi_index >= 57:
        return ("Shakuni", "Chatushpada", "Naga")[half_tithi_index - 57]
    return _REPEATING_KARANAS[(half_tithi_index - 1) % len(_REPEATING_KARANAS)]


def _element_indices(provider: SwissEphemerisProvider, jd_ut: float) -> dict[str, int]:
    sun, moon = _sidereal_sun_moon(provider, jd_ut)
    elongation = (moon - sun) % 360.0
    return {
        "tithi": min(29, int(elongation / 12.0)),
        "nakshatra": min(26, int(moon / (360.0 / 27.0))),
        "yoga": min(26, int(((sun + moon) % 360.0) / (360.0 / 27.0))),
        "karana": min(59, int(elongation / 6.0)),
    }


def _next_element_transitions(provider: SwissEphemerisProvider, start_jd: float, timezone_name: str) -> dict[str, dict[str, str | int]]:
    """Find the next angular-boundary transition for each computed limb."""
    transitions: dict[str, dict[str, str | int]] = {}
    previous_jd = start_jd
    previous = _element_indices(provider, previous_jd)
    pending = set(previous)
    step = 1.0 / 24.0
    # Four days bounds the search while comfortably spanning any next limb
    # boundary under the configured geocentric lunar motion.
    for hour in range(1, 97):
        current_jd = start_jd + hour * step
        current = _element_indices(provider, current_jd)
        for key in tuple(pending):
            if current[key] == previous[key]:
                continue
            old_index = previous[key]
            low, high = previous_jd, current_jd
            for _ in range(36):
                midpoint = (low + high) / 2.0
                if _element_indices(provider, midpoint)[key] == old_index:
                    low = midpoint
                else:
                    high = midpoint
            new_index = current[key]
            transition_utc = _julian_day_to_utc(high)
            transition_local = transition_utc.astimezone(ZoneInfo(timezone_name))
            if key == "tithi":
                transition_name = _TITHI_NAMES[new_index]
                transition_data = {"at": transition_local.isoformat(), "next_index": new_index + 1,
                                   "next_name": transition_name, "next_paksha": "Shukla" if new_index < 15 else "Krishna"}
            elif key == "nakshatra":
                transition_data = {"at": transition_local.isoformat(), "next_index": new_index + 1,
                                   "next_name": _NAKSHATRA_NAMES[new_index]}
            elif key == "yoga":
                transition_data = {"at": transition_local.isoformat(), "next_index": new_index + 1,
                                   "next_name": _YOGA_NAMES[new_index]}
            else:
                transition_data = {"at": transition_local.isoformat(), "next_index": new_index + 1,
                                   "next_name": _karana_name(new_index)}
            transitions[key] = transition_data
            pending.remove(key)
        if not pending:
            return transitions
        previous_jd, previous = current_jd, current
    raise PanchangUnavailable("The next Panchang element transition could not be determined")


def calculate_panchang_day(
    local_date: date,
    latitude: float,
    longitude: float,
    timezone_name: str,
    provider: SwissEphemerisProvider,
    *,
    location_name: str,
) -> dict:
    """Calculate the five Panchang limbs at local Hindu sunrise for a date."""
    if not math.isfinite(latitude) or not -90 <= latitude <= 90:
        raise InvalidBirthData("Latitude must be finite and between -90 and 90 degrees")
    if not math.isfinite(longitude) or not -180 <= longitude <= 180:
        raise InvalidBirthData("Longitude must be finite and between -180 and 180 degrees")
    if not location_name.strip() or len(location_name.strip()) > 160:
        raise InvalidBirthData("A location name of 1 to 160 characters is required")
    midnight_local = _local_midnight(local_date, timezone_name)
    start_jd = _utc_julian_day(provider, midnight_local)
    # Follow the Swiss Ephemeris example's longitude-adjusted starting point.
    search_jd = start_jd - longitude / 360.0
    with provider._lock:
        sunrise_jd = _solar_event(provider, search_jd, latitude, longitude, provider.ffi.SE_CALC_RISE)
        sunset_jd = _solar_event(provider, sunrise_jd, latitude, longitude, provider.ffi.SE_CALC_SET)
        sunrise_utc, sunset_utc = _julian_day_to_utc(sunrise_jd), _julian_day_to_utc(sunset_jd)
        zone = ZoneInfo(timezone_name)
        sunrise_local, sunset_local = sunrise_utc.astimezone(zone), sunset_utc.astimezone(zone)
        if sunrise_local.date() != local_date or sunset_local.date() != local_date:
            raise PanchangUnavailable("A sunrise and sunset on the selected local date could not be identified")
        sun_lon, moon_lon = _sidereal_sun_moon(provider, sunrise_jd)
        windows = daytime_windows(sunrise_local, sunset_local, (sunrise_local.weekday() + 1) % 7)
        transitions = _next_element_transitions(provider, sunrise_jd, timezone_name)

    elongation = (moon_lon - sun_lon) % 360.0
    tithi_index = min(29, int(elongation / 12.0))
    nakshatra_index = min(26, int(moon_lon / (360.0 / 27.0)))
    yoga_index = min(26, int(((sun_lon + moon_lon) % 360.0) / (360.0 / 27.0)))
    karana_index = min(59, int(elongation / 6.0))
    vara_index = (sunrise_local.weekday() + 1) % 7
    return {
        "local_date": local_date.isoformat(),
        "calculated_at": datetime.now(timezone.utc).isoformat(),
        "location_name": location_name.strip(),
        "timezone": timezone_name,
        "sunrise": sunrise_local.isoformat(),
        "sunset": sunset_local.isoformat(),
        "daytime_windows": windows,
        "transitions": transitions,
        "elements_at": "sunrise",
        "tithi": {"index": tithi_index + 1, "name": _TITHI_NAMES[tithi_index], "paksha": "Shukla" if tithi_index < 15 else "Krishna"},
        "vara": {"index": vara_index, "name": _WEEKDAYS[vara_index]},
        "nakshatra": {"index": nakshatra_index + 1, "name": _NAKSHATRA_NAMES[nakshatra_index], "longitude": moon_lon},
        "yoga": {"index": yoga_index + 1, "name": _YOGA_NAMES[yoga_index]},
        "karana": {"index": karana_index + 1, "name": _karana_name(karana_index)},
        "calculation": {
            "engine_version": PANCHANG_ENGINE_VERSION,
            "provider_engine_version": provider.ephemeris_version,
            "ayanamsa": "lahiri",
            "longitude_frame": "sidereal",
            "sunrise_convention": "Swiss Ephemeris Hindu rising: solar centre at horizon, no refraction, geocentric, solar ecliptic latitude ignored",
            "daily_element_convention": "five limbs evaluated at sunrise local to the selected IANA timezone",
            "transition_convention": "next boundaries for Tithi, Nakshatra, Yoga and Karana are found from strict Swiss sidereal longitudes by bounded hourly search and bisection",
            "daytime_window_convention": "Rahu Kalam, Yamagandam and Gulika Kalam use weekday-indexed eighths of sunrise-to-sunset; Abhijit is the eighth of fifteen equal daylight muhurtas. Returned as time windows only, not auspiciousness advice.",
            "daytime_window_methodology_reference": "Dinam.org how-we-calculate methodology (contemporary implementation reference; regional conventions may differ)",
            "ephemeris": "Swiss Ephemeris files only; Moshier fallback refused",
        },
    }
