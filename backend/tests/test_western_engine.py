from datetime import date, time
import math

import pytest

from app.core.config import settings
from app.services.astrology.base import EngineUnavailable
from app.services.astrology.sweph import InvalidBirthData, UnsupportedHouseSystem
from app.services.astrology.western import (
    ASPECT_ANGLES,
    DEFAULT_ASPECT_ORBS,
    WesternAstrologyEngine,
    calculate_aspects,
)


def _houses(start=0.0):
    return [{"number": index + 1, "cusp_longitude": (start + index * 30.0) % 360} for index in range(12)]


def _planet(name, longitude, speed=0.0):
    return {"name": name, "longitude": longitude, "longitude_speed_deg_per_day": speed, "retrograde": speed < 0}


class FakeProvider:
    ephemeris_version = "fixture-ephemeris/1"

    def calculate(self, utc, latitude, longitude, zodiac, house_system):
        if not -90 <= latitude <= 90:
            raise InvalidBirthData("Latitude must be between -90 and 90 degrees")
        if not -180 <= longitude <= 180:
            raise InvalidBirthData("Longitude must be between -180 and 180 degrees")
        if house_system == "P" and abs(latitude) > 66:
            raise UnsupportedHouseSystem("Placidus houses are unavailable at this latitude; try Whole Sign (W)")
        return {
            "utc_datetime": utc.isoformat(), "julian_day_ut": 2451545.0,
            "zodiac": zodiac, "house_system": house_system,
            "calculation_flags": {"requested": 258, "houses": 0, "apparent": True, "geocentric": True, "ephemeris": "SWIEPH"},
            "planets": [_planet("Sun", 15.0, 0.98), _planet("Moon", 75.0, 13.0), _planet("Mars", 345.0, -0.2)],
            "houses": _houses(), "ascendant_longitude": 10.0, "midheaven_longitude": 280.0,
            "engine_version": "shared-provider/fixture", "ephemeris_version": self.ephemeris_version,
        }


@pytest.fixture
def western(monkeypatch):
    monkeypatch.setattr(settings, "astrology_calculations_enabled", True)
    monkeypatch.setattr(settings, "swisseph_license_confirmed", True)
    return WesternAstrologyEngine(FakeProvider())


def _birth(**overrides):
    data = {
        "birth_date": date(2000, 1, 1), "birth_time": time(12), "timezone": "UTC",
        "latitude": 0.0, "longitude": 0.0, "time_accuracy": "exact",
    }
    data.update(overrides)
    return data


def test_chart_uses_tropical_positions_angles_houses_motion_and_metadata(western):
    result = western.calculate_chart(_birth(), {"house_system": "P"})
    sun, moon, mars = result["planets"]
    assert result["zodiac"] == "tropical"
    assert sun["sign"] == "Aries" and sun["degrees_in_sign"] == pytest.approx(15)
    assert sun["house"] == 1
    assert mars["house"] == 12
    assert mars["retrograde"] is True
    assert result["ascendant"]["longitude"] == 10
    assert result["ascendant"]["house"] == 1
    assert result["midheaven"]["sign"] == "Capricorn"
    assert result["configuration"]["house_system"] == "P"
    assert result["configuration"]["house_system_name"] == "Placidus"
    assert result["configuration"]["aspect_orbs"] == DEFAULT_ASPECT_ORBS
    assert result["western_engine_version"] == "astroai-western/1.0.0"
    assert moon["longitude"] == 75


@pytest.mark.parametrize("angle,name", [(0, "conjunction"), (60, "sextile"), (90, "square"), (120, "trine"), (180, "opposition")])
def test_each_major_aspect_is_detected(angle, name):
    result = calculate_aspects([_planet("Sun", 0), _planet("Moon", float(angle))])
    assert len(result) == 1
    assert result[0]["aspect"] == name
    assert result[0]["orb"] == pytest.approx(0)
    assert result[0]["motion"] == "exact"


def test_aspect_orb_boundary_includes_limit_and_excludes_outside():
    at_limit = calculate_aspects([_planet("Sun", 0), _planet("Venus", 66)], {"sextile": 6})
    outside = calculate_aspects([_planet("Sun", 0), _planet("Venus", 66.00001)], {"sextile": 6})
    assert [(row["aspect"], row["orb"]) for row in at_limit] == [("sextile", pytest.approx(6))]
    assert outside == []


def test_applying_and_separating_are_derived_from_relative_speed():
    applying = calculate_aspects([_planet("Sun", 0, 1), _planet("Mars", 62, -1)], {"sextile": 3})[0]
    separating = calculate_aspects([_planet("Sun", 0, 1), _planet("Mars", 62, 1)], {"sextile": 3})[0]
    assert applying["motion"] == "applying" and applying["applying"] is True
    assert separating["motion"] == "separating" and separating["applying"] is False


def test_missing_speed_marks_aspect_motion_unknown():
    result = calculate_aspects([{"name": "Sun", "longitude": 0}, {"name": "Moon", "longitude": 2}], {"conjunction": 3})
    assert result[0]["motion"] == "unknown"
    assert result[0]["applying"] is None


def test_partial_orb_configuration_retains_documented_defaults():
    result = calculate_aspects([_planet("Sun", 0), _planet("Moon", 10)], {"conjunction": 10})
    assert result[0]["allowed_orb"] == 10
    assert set(ASPECT_ANGLES) == set(DEFAULT_ASPECT_ORBS)


@pytest.mark.parametrize("latitude,longitude", [(91, 0), (0, 181), (math.nan, 0)])
def test_invalid_coordinates_are_rejected(western, latitude, longitude):
    with pytest.raises(InvalidBirthData):
        western.calculate_chart(_birth(latitude=latitude, longitude=longitude), {})


@pytest.mark.parametrize("birth_time,time_accuracy", [(None, "unknown"), ("bad-time", "exact")])
def test_missing_or_invalid_birth_time_is_rejected(western, birth_time, time_accuracy):
    with pytest.raises(InvalidBirthData):
        western.calculate_chart(_birth(birth_time=birth_time, time_accuracy=time_accuracy), {})


def test_unsupported_house_system_and_polar_placidus_have_clear_errors(western):
    with pytest.raises(UnsupportedHouseSystem, match="Supported systems"):
        western.calculate_chart(_birth(), {"house_system": "?"})
    with pytest.raises(UnsupportedHouseSystem, match="try Whole Sign"):
        western.calculate_chart(_birth(latitude=67), {"house_system": "P"})


def test_nonfinite_aspect_orbs_are_rejected(western):
    with pytest.raises(InvalidBirthData, match="finite values"):
        western.calculate_chart(_birth(), {"aspect_orbs": {"conjunction": math.nan}})


def test_public_calculation_remains_guarded_by_runtime_and_license_flags(monkeypatch):
    monkeypatch.setattr(settings, "astrology_calculations_enabled", False)
    monkeypatch.setattr(settings, "swisseph_license_confirmed", False)
    with pytest.raises(EngineUnavailable, match="disabled"):
        WesternAstrologyEngine(FakeProvider()).get_provider()
