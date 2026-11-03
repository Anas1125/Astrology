# Astrology calculation engine

AstroAI keeps Vedic and Western calculation configuration behind independent adapters and shares the low-level astronomical provider in `backend/app/services/astrology/sweph.py`. The provider uses `swisseph-ffi==1.0.0`, a raw `ctypes` binding to Swiss Ephemeris 2.10.03. It requests Swiss Ephemeris flags explicitly, checks returned flags, and rejects Moshier fallback. The Vedic adapter derives Lahiri sidereal D1 and D9 placements, Rashi, Nakshatra/lord/Pada, configured-cusp houses, mean Rahu/Ketu, and Vimshottari Mahadasha/Antardasha. The Western adapter derives tropical signs, configured Placidus/Whole Sign and other supported Swiss houses, planetary house placements, five major aspects and applying/separating status from relative longitude speeds. Transits remain unsupported.

## macOS ARM64 development setup

Use a supported Python interpreter (the wrapper's published target range includes Python 3.10–3.14; validate the complete AstroAI runtime on the chosen version). From `backend/`:

```sh
python3.14 -m venv .venv
.venv/bin/python -m pip install -e '.[dev,astrology]'
```

The package publisher documents a bundled `macos-arm64/libswe.dylib`; no separate system Swiss library should be necessary. `SWISSEPH_LIBRARY_PATH` is an optional explicit path override to the shared library itself. Verify a selected library before runtime use:

```sh
file /path/to/libswe.dylib
otool -L /path/to/libswe.dylib
codesign -dv --verbose=2 /path/to/libswe.dylib
```

The native library and ephemeris data are distinct. `.se1` files are not bundled by the Python wrapper and must be obtained/provisioned separately. Keep them outside the repository; for example:

```sh
mkdir -p "$HOME/Library/Application Support/AstroAI/ephe"
```

Place authorized files such as `sepl_18.se1` (planetary data) and `semo_18.se1` (Moon data) in that directory for modern-date calculations. Configure the process environment (or local ignored `.env`) with:

```dotenv
SWISSEPH_EPHE_PATH=/Users/you/Library/Application Support/AstroAI/ephe
SWISSEPH_LIBRARY_PATH=
ASTROLOGY_CALCULATIONS_ENABLED=false
SWISSEPH_LICENSE_CONFIRMED=false
```

For containers, install the `astrology` extra as the backend image does, and mount the externally provisioned ephemeris directory read-only at a fixed container path. Set `SWISSEPH_EPHE_PATH` to that mount. Do not add `.se1` files or native libraries to source control; `.gitignore` excludes these artifacts.

## Tests and readiness

`backend/tests/test_astrology_native.py` exercises the real wrapper when installed. Library loading, version, J2000 Julian Day, Moshier-only Sun/Moon calls (for a no-data native smoke check), Lahiri, tropical/sidereal delta and a documented house/Ascendant case need only the native library. Swiss-file position tests include the Swiss manual's Astronomical Almanac Venus RA/Dec case; strict missing-coverage checks also use the actual library. These tests additionally require configured `.se1` files and report explicit skip reasons when prerequisites are absent. Fake-provider tests remain in `test_astrology_calculations.py` for deterministic adapter behavior.

Before any chart endpoint is enabled, run the native suite with both the library and files present; verify Sun and Moon returned `SEFLG_SWIEPH` (not `SEFLG_MOSEPH`), reference positions against independently published values using matching time scales/frames/flags, house and Lahiri references, timezone/DST cases, invalid/missing/insufficient data behavior, and ownership/API regression tests. A package install or wrapper-reported version alone does not demonstrate calculation accuracy.

## Vedic divisions and Vimshottari configuration

The Vedic chart route accepts D1 or D9 explicitly:

```http
POST /api/v1/astrology/charts/vedic
Authorization: Bearer <access-token>
Content-Type: application/json

{"profile_id":"<owned-profile-uuid>","house_system":"P","division":"D9","dasha_year_convention":"savana_360_day"}
```

Omitting `division` defaults to D1. Navamsa maps each sign's nine equal segments using movable/fixed/dual starting signs. D9 house assignment applies the configured Swiss house system to D1 cusps transformed into D9 longitudes. The selected convention is included in the result/configuration. Vimshottari uses the traditional nine-lord sequence with a fixed **360-day Savana year**; this is an explicit product setting and not claimed as a universal year convention. The first Mahadasha and Antardasha are reported with elapsed/balance fields when birth occurs within the period. Lunar nodes use the mean-node model; Ketu is exactly opposite Rahu.

These outputs are implemented and tested but not publicly available: both calculation flags remain false pending final licensing review and deployment approval. Results should not be represented as commercially cleared or production-ready until that gate is resolved.

The package metadata declares AGPL-3.0-or-later. Swiss Ephemeris separately uses an AGPL or Professional License model. Their licenses, possible AGPL network-source obligations, and commercial SaaS deployment terms require professional legal review. AstroAI has no commercial licensing clearance. Both `ASTROLOGY_CALCULATIONS_ENABLED` and `SWISSEPH_LICENSE_CONFIRMED` stay false; calculation endpoints must remain disabled until runtime, accuracy and legal gates are cleared.
