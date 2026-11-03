from datetime import date, datetime, time, timezone
import math

import pytest

from app.services.astrology.sweph import (
    EphemerisUnavailable,
    InvalidBirthData,
    SwissEphemerisProvider,
    julian_day_from_utc,
    local_birth_time_to_utc,
    nakshatra_details,
)
from app.services.astrology.vedic import (
    NAVAMSA_WIDTH,
    navamsa_details,
    rashi_index,
    vimshottari_dasha,
)


def test_julian_day_j2000_noon_reference():
    # Standard J2000 epoch reference: 2000-01-01 12:00 TT/UT convention.
    assert julian_day_from_utc(datetime(2000, 1, 1, 12, tzinfo=timezone.utc)) == pytest.approx(2451545.0, abs=1e-9)


def test_iana_timezone_uses_historical_daylight_saving_rules():
    summer = local_birth_time_to_utc(date(2000, 7, 1), time(12), "America/New_York")
    winter = local_birth_time_to_utc(date(2000, 1, 1), time(12), "America/New_York")
    assert summer == datetime(2000, 7, 1, 16, tzinfo=timezone.utc)
    assert winter == datetime(2000, 1, 1, 17, tzinfo=timezone.utc)


def test_nonexistent_and_ambiguous_local_times_are_rejected():
    with pytest.raises(InvalidBirthData, match="does not exist"):
        local_birth_time_to_utc(date(2021, 3, 14), time(2, 30), "America/New_York")
    with pytest.raises(InvalidBirthData, match="ambiguous"):
        local_birth_time_to_utc(date(2021, 11, 7), time(1, 30), "America/New_York")


def test_missing_time_is_never_assumed():
    with pytest.raises(InvalidBirthData, match="missing"):
        local_birth_time_to_utc(date(1990, 1, 1), None, "Asia/Kolkata")


def test_nakshatra_and_pada_boundaries():
    assert nakshatra_details(0)["name"] == "Ashwini"
    assert nakshatra_details(0)["pada"] == 1
    assert nakshatra_details(360 / 108)["pada"] == 2
    assert nakshatra_details(360 / 27)["name"] == "Bharani"
    assert nakshatra_details(360)["rashi"] == "Mesha"
    assert nakshatra_details(0)["lord"] == "Ketu"
    assert nakshatra_details(0)["remaining_fraction"] == pytest.approx(1)
    assert nakshatra_details(360 / 27)["lord"] == "Venus"


@pytest.mark.parametrize("index", range(12))
def test_rashi_boundaries(index):
    boundary = index * 30.0
    assert rashi_index(boundary % 360) == index
    assert rashi_index((boundary - 1e-8) % 360) == (index - 1) % 12


@pytest.mark.parametrize("sign", range(12))
def test_navamsa_start_sign_mapping_for_all_rashis(sign):
    expected = sign if sign % 3 == 0 else (sign + (8 if sign % 3 == 1 else 4)) % 12
    assert navamsa_details(sign * 30.0)["rashi_index"] == expected


@pytest.mark.parametrize("sign", range(12))
@pytest.mark.parametrize("segment", range(1, 9))
def test_navamsa_segment_boundaries(sign, segment):
    boundary = sign * 30.0 + segment * NAVAMSA_WIDTH
    below = navamsa_details(boundary - 1e-8)
    at = navamsa_details(boundary)
    assert below["segment"] == segment
    assert at["segment"] == segment + 1
    assert at["rashi_index"] == (below["rashi_index"] + 1) % 12


def test_navamsa_last_segment_wraps_at_sign_boundary():
    assert navamsa_details(30 - 1e-8)["segment"] == 9
    assert navamsa_details(30)["segment"] == 1


def test_nakshatra_boundary_lords_padas_and_fraction():
    span = 360.0 / 27
    for index in range(27):
        start = index * span
        assert nakshatra_details(start)["index"] == index + 1
        assert nakshatra_details(start + span - 1e-9)["index"] == index + 1
        assert nakshatra_details(start + span)["index"] == (index + 1) % 27 + 1
        for pada in range(1, 4):
            assert nakshatra_details(start + pada * span / 4)["pada"] == pada + 1


def test_vimshottari_sequence_duration_and_birth_balance():
    birth = datetime(2000, 1, 1, tzinfo=timezone.utc)
    result = vimshottari_dasha(0, birth)
    assert result["year_convention"] == "savana_360_day"
    assert result["year_length_days"] == 360
    assert result["starting_lord"] == "Ketu"
    assert [item["lord"] for item in result["mahadashas"]] == ["Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury"]
    assert [item["full_duration_years"] for item in result["mahadashas"]] == [7, 20, 6, 10, 7, 18, 16, 19, 17]
    assert result["birth_balance_days"] == pytest.approx(7 * 360)
    first_md_ads = [item for item in result["antardashas"] if item["mahadasha_lord"] == "Ketu"]
    assert [item["lord"] for item in first_md_ads] == ["Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury"]
    assert first_md_ads[0]["start"] == birth.isoformat()


def test_vimshottari_partial_antardasha_and_invalid_convention():
    birth = datetime(2000, 1, 1, tzinfo=timezone.utc)
    moon = 360.0 / 27 / 2
    result = vimshottari_dasha(moon, birth)
    assert result["starting_lord"] == "Ketu"
    assert 0 < result["birth_balance_days"] < 7 * 360
    first_ad = result["antardashas"][0]
    assert first_ad["elapsed_days_at_birth"] > 0
    assert first_ad["remaining_days_at_birth"] < first_ad["full_duration_days"]
    with pytest.raises(InvalidBirthData, match="Only the explicitly configured"):
        vimshottari_dasha(0, birth, "365_day")


@pytest.mark.parametrize("value", [-0.1, 360.1, math.nan, math.inf])
def test_nakshatra_rejects_invalid_longitudes(value):
    with pytest.raises(InvalidBirthData):
        nakshatra_details(value)


def test_ephemeris_directory_is_required(tmp_path):
    with pytest.raises(EphemerisUnavailable, match="files are missing"):
        SwissEphemerisProvider(str(tmp_path))


class FakeSwiss:
    def __init__(self, library_path=None):
        self.library_path = library_path
        self.flags = []

    def swe_set_ephe_path(self, path):
        self.path = path

    def swe_version(self, buffer):
        buffer.value = b"2.10.03"

    def swe_julday(self, year, month, day, hour, calendar):
        return 2451545.0

    def swe_calc_ut(self, jd, planet, flags, xx, error):
        self.flags.append(flags)
        for index, value in enumerate((float(planet * 20), 0.1, 1.0, -0.2, 0.0, 0.0)):
            xx[index] = value
        return flags

    def swe_houses_ex(self, jd, flags, latitude, longitude, system, cusps, ascmc):
        for index in range(1, 13):
            cusps[index] = index * 30.0
        ascmc[0], ascmc[1] = 42.0, 132.0
        return 0

    def swe_set_sid_mode(self, mode, t0, ayan_t0):
        self.sidereal_mode = mode

    def swe_get_ayanamsa_ut(self, jd):
        return 23.85


class FakeFfi:
    from ctypes import c_double, create_string_buffer
    SE_GREG_CAL = 1
    SE_SUN, SE_MOON, SE_MERCURY, SE_VENUS, SE_MARS = range(5)
    SE_JUPITER, SE_SATURN, SE_URANUS, SE_NEPTUNE, SE_PLUTO = range(5, 10)
    SE_ASC, SE_MC = 0, 1
    SE_SIDM_LAHIRI = 1
    SEFLG_SWIEPH, SEFLG_MOSEPH, SEFLG_SPEED, SEFLG_SIDEREAL = 2, 4, 256, 65536
    SwissEph = FakeSwiss


def test_provider_returns_planets_houses_and_flags_without_fallback(tmp_path):
    (tmp_path / "sepl_18.se1").write_bytes(b"fixture marker")
    provider = SwissEphemerisProvider(str(tmp_path), ffi_module=FakeFfi)
    result = provider.calculate(datetime(2000, 1, 1, 12, tzinfo=timezone.utc), 0, 0, "tropical", "P")
    assert len(result["planets"]) == 10
    assert len(result["houses"]) == 12
    assert result["ascendant_longitude"] == 42
    assert result["planets"][0]["retrograde"] is True
    assert result["calculation_flags"]["ephemeris"] == "SWIEPH"


def test_provider_rejects_invalid_coordinates(tmp_path):
    (tmp_path / "sepl_18.se1").write_bytes(b"fixture marker")
    provider = SwissEphemerisProvider(str(tmp_path), ffi_module=FakeFfi)
    with pytest.raises(InvalidBirthData, match="Latitude"):
        provider.calculate(datetime(2000, 1, 1, 12, tzinfo=timezone.utc), 91, 0, "tropical", "P")


def test_provider_rejects_moshier_fallback(tmp_path):
    (tmp_path / "sepl_18.se1").write_bytes(b"fixture marker")

    class FallbackSwiss(FakeSwiss):
        def swe_calc_ut(self, jd, planet, flags, xx, error):
            super().swe_calc_ut(jd, planet, flags, xx, error)
            return (flags & ~FakeFfi.SEFLG_SWIEPH) | FakeFfi.SEFLG_MOSEPH

    class FallbackFfi(FakeFfi):
        SwissEph = FallbackSwiss

    provider = SwissEphemerisProvider(str(tmp_path), ffi_module=FallbackFfi)
    with pytest.raises(EphemerisUnavailable, match="fallback calculation was refused"):
        provider.calculate(datetime(2000, 1, 1, 12, tzinfo=timezone.utc), 0, 0, "tropical", "P")


@pytest.mark.integration
@pytest.mark.skipif(
    __import__("os").environ.get("SWISSEPH_EPHE_PATH") is None,
    reason="Set SWISSEPH_EPHE_PATH and install the optional .[astrology] extra for native integration references",
)
def test_swiss_house_reference_from_official_swetest_fixture():
    # Astro.com Swiss Ephemeris documentation example: 2000-01-26 08:08 UT,
    # longitude 30E, latitude 66.562N, Placidus cusp 1 = 93°10'50.7734".
    provider = SwissEphemerisProvider(__import__("os").environ["SWISSEPH_EPHE_PATH"])
    result = provider.calculate(datetime(2000, 1, 26, 8, 8, tzinfo=timezone.utc), 66.562, 30.0, "tropical", "P")
    reference = 93 + 10 / 60 + 50.7734 / 3600
    assert result["houses"][0]["cusp_longitude"] == pytest.approx(reference, abs=0.001)
