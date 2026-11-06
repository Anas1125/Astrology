from datetime import date, datetime, timezone
import math
import os
from pathlib import Path

import pytest

from app.services.astrology.panchang import PanchangUnavailable, _karana_name, calculate_panchang_day, daytime_windows
from app.services.astrology.sweph import InvalidBirthData, SwissEphemerisProvider


@pytest.fixture(scope="module")
def native_provider():
    ephe = os.environ.get("SWISSEPH_EPHE_PATH")
    if not ephe or not Path(ephe).is_dir():
        pytest.skip("Set SWISSEPH_EPHE_PATH to external Swiss Ephemeris files for native Panchang integration")
    try:
        return SwissEphemerisProvider(ephe, os.environ.get("SWISSEPH_LIBRARY_PATH"))
    except Exception as exc:
        pytest.skip(f"The configured external Swiss native runtime is unavailable: {type(exc).__name__}")


@pytest.mark.integration
def test_panchang_matches_indian_meteorological_department_day_elements(native_provider):
    # IMD Rashtriya Panchang 2026-27, Chaitra Day 1 (22 March 2026),
    # Central Station 82°30'E, 23°11'N: Chaturthi, Bharani, Vaidhriti,
    # Vanij at sunrise, Sunday. IMD uses upper-limb apparent sunrise; this
    # service explicitly reports Swiss Ephemeris Hindu centre/no-refraction
    # sunrise, so sunrise/sunset times are expected to differ by about 4 min.
    result = calculate_panchang_day(
        date(2026, 3, 22), 23 + 11 / 60, 82.5, "Asia/Kolkata", native_provider,
        location_name="IMD Central Station reference",
    )
    assert result["tithi"] == {"index": 4, "name": "Chaturthi", "paksha": "Shukla"}
    assert result["vara"] == {"index": 0, "name": "Sunday"}
    assert result["nakshatra"]["name"] == "Bharani"
    assert result["yoga"]["name"] == "Vaidhriti"
    assert result["karana"]["name"] == "Vanija"
    assert result["sunrise"].startswith("2026-03-22T")
    assert result["sunset"].startswith("2026-03-22T")
    assert result["calculated_at"].endswith("+00:00")
    assert set(result["transitions"]) == {"tithi", "nakshatra", "yoga", "karana"}
    assert all(result["transitions"][key]["at"] > result["sunrise"] for key in result["transitions"])
    assert set(result["daytime_windows"]) == {"rahu_kalam", "yamagandam", "gulika_kalam", "abhijit_muhurta"}
    assert result["calculation"]["ephemeris"] == "Swiss Ephemeris files only; Moshier fallback refused"


@pytest.mark.parametrize(("half_index", "expected"), [
    (0, "Kimstughna"), (1, "Bava"), (7, "Vishti"), (8, "Bava"),
    (56, "Vishti"), (57, "Shakuni"), (58, "Chatushpada"), (59, "Naga"),
])
def test_karana_sequence_boundaries(half_index, expected):
    assert _karana_name(half_index) == expected


def test_daytime_windows_use_weekday_parts_and_equal_intervals():
    sunrise = datetime(2026, 3, 22, 6, tzinfo=timezone.utc)  # Sunday
    sunset = datetime(2026, 3, 22, 18, tzinfo=timezone.utc)
    result = daytime_windows(sunrise, sunset, 0)
    assert result["rahu_kalam"]["part"] == 8
    assert result["yamagandam"]["part"] == 5
    assert result["gulika_kalam"]["part"] == 7
    assert result["abhijit_muhurta"]["part"] == 8
    assert result["abhijit_muhurta"]["parts_in_daylight"] == 15
    for interval in result.values():
        start = datetime.fromisoformat(interval["start"])
        end = datetime.fromisoformat(interval["end"])
        assert (end - start).total_seconds() == pytest.approx(12 * 3600 / interval["parts_in_daylight"])


def test_daytime_windows_use_elapsed_time_across_dst():
    from zoneinfo import ZoneInfo

    zone = ZoneInfo("America/New_York")
    sunrise = datetime(2021, 3, 14, 6, 30, tzinfo=zone)
    sunset = datetime(2021, 3, 14, 19, 0, tzinfo=zone)
    result = daytime_windows(sunrise, sunset, 0)
    start = datetime.fromisoformat(result["abhijit_muhurta"]["start"])
    end = datetime.fromisoformat(result["abhijit_muhurta"]["end"])
    assert (end.astimezone(timezone.utc) - start.astimezone(timezone.utc)).total_seconds() == pytest.approx(12.5 * 3600 / 15)


@pytest.mark.integration
def test_panchang_timezone_keeps_selected_local_date_across_dst(native_provider):
    result = calculate_panchang_day(
        date(2021, 3, 14), 40.7128, -74.006, "America/New_York", native_provider,
        location_name="New York",
    )
    assert result["local_date"] == "2021-03-14"
    assert result["timezone"] == "America/New_York"
    assert result["sunrise"].startswith("2021-03-14T")
    assert result["sunset"].startswith("2021-03-14T")


@pytest.mark.parametrize(("latitude", "longitude"), [(91, 0), (math.nan, 0), (0, 181)])
def test_panchang_rejects_invalid_coordinates(native_provider, latitude, longitude):
    with pytest.raises(InvalidBirthData):
        calculate_panchang_day(
            date(2026, 3, 22), latitude, longitude, "Asia/Kolkata", native_provider,
            location_name="Test location",
        )


@pytest.mark.integration
def test_panchang_explicitly_fails_when_sunrise_is_not_found(native_provider):
    with pytest.raises(PanchangUnavailable):
        calculate_panchang_day(
            date(2026, 6, 21), 89.0, 0.0, "UTC", native_provider,
            location_name="High latitude",
        )
