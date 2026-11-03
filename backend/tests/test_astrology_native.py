"""Tests against the real swisseph-ffi C binding, when it is installed."""
from __future__ import annotations

from datetime import datetime, timezone
import importlib
import math
import os
from pathlib import Path

import pytest

from app.services.astrology.sweph import EphemerisUnavailable, SwissEphemerisProvider
from app.services.astrology.vedic import VedicAstrologyEngine
from app.services.astrology.western import WesternAstrologyEngine


@pytest.fixture(scope="module")
def native_ffi():
    try:
        return importlib.import_module("swisseph_ffi")
    except ImportError:
        pytest.skip("Install backend extra `.[astrology]` to run native Swiss Ephemeris tests")


@pytest.fixture(scope="module")
def native_swe(native_ffi):
    library_path = os.environ.get("SWISSEPH_LIBRARY_PATH")
    return native_ffi.SwissEph(library_path=library_path)


@pytest.fixture(scope="module")
def ephemeris_path():
    configured = os.environ.get("SWISSEPH_EPHE_PATH")
    if not configured:
        pytest.skip("Set SWISSEPH_EPHE_PATH to external .se1 data for Swiss-file integration tests")
    path = Path(configured).expanduser()
    required = ("sepl_18.se1", "semo_18.se1")
    missing = [name for name in required if not (path / name).is_file()]
    if missing:
        pytest.skip(f"Missing configured modern-date Swiss Ephemeris files: {', '.join(missing)}")
    return str(path)


def _calculate(native_ffi, swe, jd_ut: float, planet: int, flags: int):
    output = (native_ffi.c_double * 6)()
    error = native_ffi.create_string_buffer(256)
    returned_flags = swe.swe_calc_ut(jd_ut, planet, flags, output, error)
    assert not error.value, error.value.decode("utf-8", errors="replace")
    assert returned_flags >= 0
    assert all(math.isfinite(value) for value in output)
    return returned_flags, list(output)


def test_native_library_loads_and_reports_version_and_j2000(native_ffi, native_swe):
    version = native_ffi.create_string_buffer(32)
    native_swe.swe_version(version)
    assert version.value.decode("ascii") == "2.10.03"
    assert native_swe.swe_julday(2000, 1, 1, 12.0, native_ffi.SE_GREG_CAL) == pytest.approx(2451545.0)


def test_native_sun_and_moon_calculate_without_external_files(native_ffi, native_swe):
    jd_ut = native_swe.swe_julday(2000, 1, 1, 12.0, native_ffi.SE_GREG_CAL)
    flags = native_ffi.SEFLG_MOSEPH | native_ffi.SEFLG_SPEED
    sun_flags, sun = _calculate(native_ffi, native_swe, jd_ut, native_ffi.SE_SUN, flags)
    moon_flags, moon = _calculate(native_ffi, native_swe, jd_ut, native_ffi.SE_MOON, flags)
    assert sun_flags & native_ffi.SEFLG_MOSEPH
    assert moon_flags & native_ffi.SEFLG_MOSEPH
    assert 279.0 < sun[0] < 282.0
    assert 210.0 < moon[0] < 240.0


def test_native_lahiri_ayanamsa_matches_published_iae_reference(native_ffi, native_swe):
    # Indian Astronomical Ephemeris 2019 p. 429: 2000-01-01 12:00 TT.
    jd_tt = 2451545.0
    native_swe.swe_set_sid_mode(native_ffi.SE_SIDM_LAHIRI, 0.0, 0.0)
    actual = native_swe.swe_get_ayanamsa(jd_tt)
    reference = 23 + 51 / 60 + 25.5324 / 3600
    assert actual == pytest.approx(reference, abs=0.00002)


def test_native_sidereal_longitude_differs_from_tropical_by_lahiri(native_ffi, native_swe):
    jd_ut = native_swe.swe_julday(2000, 1, 1, 12.0, native_ffi.SE_GREG_CAL)
    # SEFLG_NONUT aligns tropical longitude with swe_get_ayanamsa_ut's mean
    # sidereal reference; apparent tropical longitude otherwise includes nutation.
    flags = native_ffi.SEFLG_MOSEPH | native_ffi.SEFLG_SPEED | native_ffi.SEFLG_NONUT
    _, tropical = _calculate(native_ffi, native_swe, jd_ut, native_ffi.SE_SUN, flags)
    native_swe.swe_set_sid_mode(native_ffi.SE_SIDM_LAHIRI, 0.0, 0.0)
    _, sidereal = _calculate(native_ffi, native_swe, jd_ut, native_ffi.SE_SUN, flags | native_ffi.SEFLG_SIDEREAL)
    ayanamsa = native_swe.swe_get_ayanamsa_ut(jd_ut)
    difference = (tropical[0] - sidereal[0]) % 360.0
    assert difference == pytest.approx(ayanamsa, abs=1e-7)


def test_native_houses_and_ascendant_match_documented_reference(native_ffi, native_swe):
    # Swiss Ephemeris manual sample: 2000-01-26 08:08 UT, 66.562N, 30E,
    # Placidus cusp 1 = 93°10'50.7734". House calculations need no .se1 files.
    jd_ut = native_swe.swe_julday(2000, 1, 26, 8 + 8 / 60, native_ffi.SE_GREG_CAL)
    cusps = (native_ffi.c_double * 13)()
    ascmc = (native_ffi.c_double * 10)()
    result = native_swe.swe_houses_ex(jd_ut, 0, 66.562, 30.0, ord("P"), cusps, ascmc)
    assert result >= 0
    reference = 93 + 10 / 60 + 50.7734 / 3600
    assert cusps[1] == pytest.approx(reference, abs=0.001)
    assert 0 <= ascmc[native_ffi.SE_ASC] < 360
    assert 0 <= ascmc[native_ffi.SE_MC] < 360


def test_provider_rejects_nonexistent_and_empty_ephemeris_paths(tmp_path):
    with pytest.raises(EphemerisUnavailable, match="files are missing"):
        SwissEphemerisProvider(str(tmp_path / "not-created"))
    with pytest.raises(EphemerisUnavailable, match="files are missing"):
        SwissEphemerisProvider(str(tmp_path))


def test_provider_reports_native_library_load_failure(native_ffi, tmp_path):
    (tmp_path / "sepl_18.se1").write_bytes(b"fixture marker")
    with pytest.raises(EphemerisUnavailable, match="ensure the native library loads"):
        SwissEphemerisProvider(str(tmp_path), str(tmp_path / "missing-libswe.dylib"), ffi_module=native_ffi)


def test_swiss_file_sun_moon_and_lahiri_calculations(native_ffi, ephemeris_path):
    provider = SwissEphemerisProvider(ephemeris_path, ffi_module=native_ffi)
    result = provider.calculate(datetime(2000, 1, 1, 12, tzinfo=timezone.utc), 13.0827, 80.2707, "sidereal", "P", "lahiri")
    by_name = {body["name"]: body for body in result["planets"]}
    assert set(("Sun", "Moon")) <= by_name.keys()
    assert all(body["flags"] & native_ffi.SEFLG_SWIEPH for body in (by_name["Sun"], by_name["Moon"]))
    assert all(not body["flags"] & native_ffi.SEFLG_MOSEPH for body in (by_name["Sun"], by_name["Moon"]))
    assert result["ayanamsa"] == pytest.approx(23.857, abs=0.01)
    assert len(result["houses"]) == 12
    assert 0 <= result["ascendant_longitude"] < 360


def test_missing_file_coverage_rejects_moshier_fallback(native_ffi, tmp_path):
    # A deliberately unrelated .se1 marker satisfies the provider's local
    # directory check but cannot provide valid coverage for this calculation.
    (tmp_path / "unrelated.se1").write_bytes(b"not a Swiss Ephemeris file")
    provider = SwissEphemerisProvider(str(tmp_path), ffi_module=native_ffi)
    with pytest.raises(EphemerisUnavailable, match="(?i)(file|fallback|ephemeris)"):
        provider.calculate(datetime(2000, 1, 1, 12, tzinfo=timezone.utc), 0.0, 0.0, "tropical", "P")


def test_swiss_file_house_reference(native_ffi, ephemeris_path):
    provider = SwissEphemerisProvider(ephemeris_path, ffi_module=native_ffi)
    result = provider.calculate(datetime(2000, 1, 26, 8, 8, tzinfo=timezone.utc), 66.562, 30.0, "tropical", "P")
    reference = 93 + 10 / 60 + 50.7734 / 3600
    assert result["houses"][0]["cusp_longitude"] == pytest.approx(reference, abs=0.001)


def test_vedic_d1_and_d9_from_real_native_provider(ephemeris_path, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "astrology_calculations_enabled", True)
    monkeypatch.setattr(settings, "swisseph_license_confirmed", True)
    provider = SwissEphemerisProvider(ephemeris_path)
    engine = VedicAstrologyEngine(provider)
    birth = {
        "birth_date": "2000-01-01", "birth_time": "17:30:00", "timezone": "Asia/Kolkata",
        "latitude": 13.0827, "longitude": 80.2707, "time_accuracy": "exact",
    }
    d1 = engine.calculate_chart(birth, {"house_system": "P", "division": "D1"})
    d9 = engine.calculate_chart(birth, {"house_system": "P", "division": "D9"})
    by_name = {planet["name"]: planet for planet in d1["planets"]}
    assert set(("Sun", "Moon", "Rahu", "Ketu")) <= by_name.keys()
    assert by_name["Rahu"]["node_model"] == "mean"
    assert by_name["Ketu"]["longitude"] == pytest.approx((by_name["Rahu"]["longitude"] + 180) % 360)
    assert by_name["Moon"]["name"] == "Moon"
    assert by_name["Moon"]["nakshatra"]["lord"] in {"Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury"}
    assert by_name["Moon"]["d9"]["rashi"]
    assert by_name["Moon"]["house"] in range(1, 13)
    assert d1["vimshottari_dasha"]["year_convention"] == "savana_360_day"
    assert d9["division"] == "D9"
    assert d9["ascendant"]["division_rashi"] == d9["ascendant"]["d9"]["rashi"]
    assert len(d9["division_houses"]) == 12


def test_western_tropical_reference_angles_and_whole_sign_houses(ephemeris_path, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "astrology_calculations_enabled", True)
    monkeypatch.setattr(settings, "swisseph_license_confirmed", True)
    engine = WesternAstrologyEngine(SwissEphemerisProvider(ephemeris_path))
    birth = {
        "birth_date": "2000-01-01", "birth_time": "12:00:00", "timezone": "UTC",
        "latitude": 0.0, "longitude": 0.0, "time_accuracy": "exact",
    }
    chart = engine.calculate_chart(birth, {"house_system": "W"})
    sun = next(planet for planet in chart["planets"] if planet["name"] == "Sun")

    # USNO approximate solar-coordinate algorithm, J2000.0 (JD 2451545.0 UT).
    # Its published accuracy is about 1 arcminute; compare in the apparent,
    # geocentric ecliptic-of-date frame with a tolerance reflecting that bound.
    g = math.radians(357.529)
    usno_sun_longitude = (280.459 + 1.915 * math.sin(g) + 0.020 * math.sin(2 * g)) % 360
    assert sun["longitude"] == pytest.approx(usno_sun_longitude, abs=1 / 60)

    # Independent GMST/mean-obliquity angle equations at J2000, Greenwich.
    # The Swiss house output is apparent-of-date, so allow 0.01 degree for
    # nutation/model differences from this compact reference calculation.
    jd = 2451545.0
    centuries = (jd - 2451545.0) / 36525.0
    gmst = (280.46061837 + 360.98564736629 * (jd - 2451545.0)
            + 0.000387933 * centuries**2 - centuries**3 / 38710000) % 360
    obliquity = 23.439291 - 0.0130042 * centuries
    radians = math.pi / 180
    mc_reference = math.degrees(math.atan2(math.sin(gmst * radians), math.cos(gmst * radians) * math.cos(obliquity * radians))) % 360
    asc_reference = (math.degrees(math.atan2(-math.cos(gmst * radians), math.cos(obliquity * radians) * math.sin(gmst * radians))) + 180) % 360
    assert chart["ascendant"]["longitude"] == pytest.approx(asc_reference, abs=0.01)
    assert chart["midheaven"]["longitude"] == pytest.approx(mc_reference, abs=0.01)
    assert chart["ascendant"]["house"] == 1
    assert chart["configuration"]["house_system_name"] == "Whole Sign"
    assert all((chart["houses"][(index + 1) % 12]["cusp_longitude"] - house["cusp_longitude"]) % 360 == pytest.approx(30) for index, house in enumerate(chart["houses"]))


def test_western_placidus_house_reference_in_native_chart(ephemeris_path, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "astrology_calculations_enabled", True)
    monkeypatch.setattr(settings, "swisseph_license_confirmed", True)
    engine = WesternAstrologyEngine(SwissEphemerisProvider(ephemeris_path))
    chart = engine.calculate_chart({
        "birth_date": "2000-01-26", "birth_time": "08:08:00", "timezone": "UTC",
        "latitude": 66.562, "longitude": 30.0, "time_accuracy": "exact",
    }, {"house_system": "P"})
    # Official Swiss Ephemeris manual example: cusp 1 is also the Ascendant.
    reference = 93 + 10 / 60 + 50.7734 / 3600
    assert chart["houses"][0]["cusp_longitude"] == pytest.approx(reference, abs=0.001)
    assert chart["ascendant"]["longitude"] == pytest.approx(reference, abs=0.001)
    assert all(1 <= planet["house"] <= 12 for planet in chart["planets"])


def test_venus_matches_astronomical_almanac_reference(native_ffi, native_swe, ephemeris_path):
    # Swiss Ephemeris manual, Astronomical Almanac 2016 pp. B68-B70:
    # 2016-04-17 12:00 UT1, Delta-T 68 s, JDE 2457496.000787;
    # apparent geocentric true-equinox-of-date RA 00h55m53.8912s,
    # Dec +04°23'25.333". swe_calc takes TT/JDE and EQUATORIAL output.
    native_swe.swe_set_ephe_path(os.fsencode(ephemeris_path))
    jd_tt = 2457496.000787
    positions = (native_ffi.c_double * 6)()
    error = native_ffi.create_string_buffer(256)
    flags = native_ffi.SEFLG_SWIEPH | native_ffi.SEFLG_SPEED | native_ffi.SEFLG_EQUATORIAL
    returned = native_swe.swe_calc(jd_tt, native_ffi.SE_VENUS, flags, positions, error)
    assert not error.value, error.value.decode("utf-8", errors="replace")
    assert returned >= 0
    assert returned & native_ffi.SEFLG_SWIEPH
    assert not returned & native_ffi.SEFLG_MOSEPH
    reference_ra = (55 / 60 + 53.8912 / 3600) * 15
    reference_dec = 4 + 23 / 60 + 25.333 / 3600
    assert positions[0] == pytest.approx(reference_ra, abs=0.001)
    assert positions[1] == pytest.approx(reference_dec, abs=0.001)
