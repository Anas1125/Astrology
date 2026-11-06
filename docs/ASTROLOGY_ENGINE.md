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

### Local Vedic verification record (2026-11-03)

Native tests run in `backend/.venv` against Swiss Ephemeris 2.10.03 and the configured external `.se1` directory. The D1 regression profile is 2000-01-01 17:30 Asia/Kolkata (12:00 UT), Chennai (13.0827 N, 80.2707 E); native results require SWIEPH flags and reject Moshier fallback. The D1 Sun longitude converted from Lahiri to tropical agrees within 1 arcminute with the US Naval Observatory's approximate solar-coordinate algorithm. Two additional geocentric tropical Mars checks use the Swiss Ephemeris manual's JPL Horizons comparison values for 2016-10-25 00:00 TT and 1800-10-25 00:00 TT; the test tolerance is 0.001 degree and the 1800 profile explicitly allows the UTC/TT offset difference. The configured Placidus cusp/Ascendant is also checked against the documented Swiss Ephemeris manual example. References: [USNO approximate solar coordinates](https://aa.usno.navy.mil/faq/sun_approx), [Swiss Ephemeris manual and JPL comparison cases](https://www.astro.com/swisseph/swisseph.htm).

The native suite also verifies all 12 geocentric bodies plus mean Rahu and opposite Ketu are returned for the Chennai profile, every D1 result has valid sign/Nakshatra/Pada and house fields, D9 preserves planetary longitudes while assigning derived Navamsa signs and houses, and Dasha metadata records `savana_360_day` / 360 days. Separate algorithm tests exercise all Rashi boundaries, all 12 Navamsa starting-sign mappings and segment transitions, every Nakshatra/Pada boundary, Vimshottari sequence, 360-day durations and birth balance. IANA tests cover modern daylight-saving offsets, rejected ambiguous/nonexistent wall times, and New York local-mean-time conversion in 1883. These establish implementation/regression behavior; they are not independent reference validation of every planet at every profile.

Independent sign-off still needed: a trusted external ephemeris/almanac comparison for every requested planet (including mean lunar nodes) across several birth instants; an independent Vedic Ascendant/D1 house and D9 reference; independent Nakshatra/Pada and Navamsa convention fixtures; and a domain-reviewed Vimshottari balance/Antardasha reference for the configured Savana year. The current full-chart browser flow verifies API persistence, authenticated retrieval, and rendering, not astronomical truth. Production/legal release remains gated separately.

## Daily Panchang calculation

`POST /api/v1/panchang/daily` accepts an authenticated request with an explicit local date, location label, latitude, longitude, and IANA timezone. Saved profile locations can be selected in the frontend; users can also enter coordinates and timezone manually. No geocoder or coordinate inference is used. The endpoint calls the same Vedic engine provider gate. In normal startup, `ASTROLOGY_CALCULATIONS_ENABLED` and `SWISSEPH_LICENSE_CONFIRMED` must both be true before native initialization; the explicitly local `backend/run_local.py` development path is isolated by a separate development-only switch and loopback middleware. Defaults remain disabled and the endpoint returns 503 unless an authorized configuration is selected.

The daily elements are sampled at the local-date sunrise: Vara from the local weekday; Tithi from Moon–Sun sidereal elongation in 12° intervals; Nakshatra from Moon sidereal longitude in 13°20′ intervals; Yoga from the sum of Sun and Moon sidereal longitudes in 13°20′ intervals; Karana from each 6° half-tithi. The configured ayanamsa is Lahiri. Sunrise and sunset use the documented Swiss Ephemeris Hindu rising convention: the solar centre at the horizon, without refraction, geocentric and ignoring the Sun's small ecliptic latitude. Invalid or polar no-sunrise dates fail explicitly. Native flags are checked so missing Swiss files cannot silently fall back to Moshier.

This is a declared AstroAI convention, not a claim of equivalence with every regional Panchanga. In particular, the [IMD Rashtriya Panchang explanation](https://packolkata.imd.gov.in/panchang/en/explanation) documents upper-limb apparent sunrise and its own increasing ayanamsa. Our native regression uses its 22 March 2026 Central Station day elements (Chaturthi, Bharani, Vaidhriti, Vanij, Sunday) as an independent category check; the sunrise/sunset instant and exact convention differ and are described in the response. Festival observances, ending times, muhurta and regional calendar rules are not implemented.

## Vedic planetary sign dignity (provisional)

`GET /api/v1/astrology/charts/{chart_id}/vedic-dignity` analyzes the latest already-persisted result for an authenticated user's completed Vedic D1 chart. It performs no ephemeris calculation, does not accept birth details, does not include D9 placements, and rejects missing/duplicate/non-finite/classical-planet placements or a sign inconsistent with the stored longitude. It returns only Sun, Moon, Mars, Mercury, Jupiter, Venus, and Saturn. Rahu and Ketu are explicitly excluded. No migration is used.

The named ruleset is `parashari-bphs-ch3-web-witness-provisional-v1`. It encodes sign dignity, BPHS chapter 3 verses 49-54 as represented in the cited web witnesses: exaltation signs and peak degrees; debilitation at the opposite sign and corresponding degree; Moolatrikona ranges Sun Leo 0-20°, Moon Taurus 3-30°, Mars Aries 0-12°, Mercury Virgo 15-20°, Jupiter Sagittarius 0-10°, Venus Libra 0-15°, Saturn Aquarius 0-20°; and own signs. Moolatrikona intervals are start-inclusive/end-exclusive. In this transcription, Moon Taurus 0-3° and Mercury Virgo 0-15° are treated as the exaltation intervals where those rules meet Moolatrikona; the exact deep-exaltation degree is also returned separately. For the other listed exaltations, the code reports the exaltation sign and deep degree separately. Debilitation classification applies to the opposite sign, with the specified deep-debilitation degree separately indicated. The sign-lord relationship uses the permanent relationship rule at verse 55 (house lords from Moolatrikona and exaltation lord); it does not use temporary relationships from verses 56-58. Relationship classifications are not strength scores. The Dignity UI and response mark every result provisional and carry both web-witness source IDs, the chapter/verse locator, and ruleset ID/version.

Source status is deliberately **not verified at edition level**. One web page calls its English text its own Sanskrit translation, without verified translator/publication-edition metadata ([VedicPupil, BPHS chapter 3](https://vedicpupil.in/library/books/brihat-parashara-hora-shastra/chapter-3)). A second online translation/commentary gives a related chapter 3 witness and explanatory commentary ([Parāśara.net, BPHS chapter 3](https://parashara.net/index.php?page=chapter3)). The current source registry's Ranjan English-translation record still says exact volume, translator, printing, and printed passage need direct verification. These web witnesses support a provisional implementation only; they do not establish an approved print citation, source text reuse rights, commercial permission, or legal clearance. Editorial/source status is not scientific validation. No substantial source text is copied into AstroAI.

Shadbala is intentionally unavailable. BPHS chapter 27 describes six components, but the identified online renderings are not a verified edition and formula translation/numbering differences remain unresolved. A complete implementation needs a reviewed edition and translations for all six methods, including Uchcha and Sapta-vargaja plus other Sthana Bala subcomponents; Dig Bala; Kala Bala subcomponents using local day/night, lunar phase, weekday/hour and ayana/time; Cheshta Bala requiring appropriate mean/true longitude or motion-state conventions; Naisargika Bala constants; and Drik Bala requiring the selected aspect-strength interpretation and complete aspect geometry. It also needs explicit virupa/rupa unit conversions, source-specific thresholds, tested astronomical inputs, and independent reference charts. The API returns `shadbala.status=unavailable` and no score rather than calling dignity “strength.” An accessible chapter 27 witness enumerates these methods and subcomponents ([BPHS chapter 27 online text](https://vedic-astro.s3.amazonaws.com/books/bhrihat_parasara_hora_shastra.pdf)); it is not treated as permission or edition verification.

The real native test requires external `.se1` files, which remain outside this repository. It verifies the IMD day-element regression, date/timezone handling across a DST boundary, invalid coordinates, Karana sequence boundaries, and explicit failure when a sunrise cannot be found. Passing these tests does not clear either Swiss Ephemeris or wrapper licensing.

#### Daylight time windows added in the local Panchang

The API also returns Rahu Kalam, Yamagandam, and Gulika Kalam as the weekday-indexed eighths of sunrise-to-sunset, plus Abhijit as the eighth of fifteen equal daylight muhurtas. Durations are computed on UTC instants before conversion back to the selected IANA zone, so DST offset changes do not distort the elapsed daylight interval. The next Tithi, Nakshatra, Yoga, and Karana boundary times are found by a bounded Swiss-position search followed by bisection, and the response includes a UTC calculation timestamp. This is one published contemporary convention, not a universal regional rule; the [Dinam.org methodology](https://www.dinam.org/en/how-we-calculate/) is recorded as a contemporary implementation reference, not as an original classical citation or editorial approval. The API presents these as time windows only and makes no auspiciousness recommendation. Some regional almanacs omit or otherwise qualify Abhijit on particular weekdays; regional observance and event-specific muhurta selection remain unsupported.

Vimshottari results now include Pratyantardasha as a third nested period level. Subperiod durations are proportional to the configured Vimshottari lord-year weights and retain the explicit 360-day Savana convention. This is a deterministic extension of the existing implementation; it still needs independent domain-reviewed reference charts before being treated as independently validated.

### Local calculation gate and licensing

The current project virtualenv is Python 3.14.7 and has `swisseph-ffi==1.0.0` installed from the previously verified local wheel. The wheel metadata declares `AGPL-3.0-or-later`; it bundles an ARM64 `libswe.dylib` (Swiss Ephemeris 2.10.03) whose inspected dynamic dependencies are the macOS `libSystem` only. This wrapper licence is separate from Swiss Ephemeris's AGPL/professional dual-licensing terms. The local `.env` points `SWISSEPH_EPHE_PATH` at the existing external `~/Downloads/astroai-ephemeris-test/ephe` directory containing `sepl_18.se1` and `semo_18.se1`. The adapter explicitly configures this directory in the native library and refuses any result without the `SEFLG_SWIEPH` flag or with `SEFLG_MOSEPH`.

`backend/run_local.py` is an explicit development launcher. It binds Uvicorn to `127.0.0.1`, keeps `ASTROLOGY_CALCULATIONS_ENABLED=false` and `SWISSEPH_LICENSE_CONFIRMED=false`, and sets the separate `ASTROLOGY_LOCAL_AGPL_DEVELOPMENT_ENABLED=true` only for that process. The settings reject that local switch outside `APP_ENV=development`; middleware rejects calculation requests from non-loopback peers while it is active. Existing authentication and profile-ownership checks still apply. Normal backend startup does not opt in, and `.env.example` leaves the switch false. This local setting is an engineering isolation measure, **not a legal conclusion or licensing approval**. Do not expose this process to a LAN, proxy, tunnel, hosted frontend, or public users. Do not distribute the app or its modified components until the applicable AGPL source obligations have been reviewed and met. Consult qualified counsel about the wrapper AGPL, Swiss Ephemeris dual-license choice, ephemeris data terms, and any network use or distribution before deployment or sharing.

For a normal restart of the local service, keep `SWISSEPH_EPHE_PATH` in the ignored `backend/.env`; the environment file is resolved relative to the backend package, independent of the shell's current directory. Start it with `cd backend && ./.venv/bin/python run_local.py`. The local gate is opt-in via this launcher; simply restarting via `uvicorn app.main:app` does not enable calculations. The ignored local `.env` is machine-specific and must not be committed. The native runtime and ephemeris data remain outside the repository's tracked source files.

## Licensing gate

Swiss Ephemeris is offered under a dual-license choice: AGPL or a separately purchased Professional License. Astrodienst says the choice must be made before distribution or activation of a public service; its AGPL route requires the developer to put the whole software project under AGPL or a compatible license. The Professional License is subject to a signed contract. See [Astrodienst's licensing instructions](https://www.astro.com/swisseph/swephinfo_e.htm) and [Professional License contract](https://www.astro.com/swisseph/secont_e.pdf).

The Python wrapper has a separate license: the installed `swisseph-ffi==1.0.0` distribution metadata identifies it as `AGPL-3.0-or-later` ([release metadata](https://pypi.org/project/swisseph-ffi/1.0.0/), [upstream source](https://github.com/jayeshmepani/Swiss-Ephemeris-Python)). The inspected wheel contains platform-specific `libswe` binaries, including the ARM64 macOS dylib, but its installed `.dist-info` has no separate license file for that bundled native library. The wrapper project's upstream README describes the C library and ephemeris data as subject to Astrodienst's AGPL-or-Professional dual license. Treat the native binary and data rights as unresolved; do not infer that wrapper metadata relicenses them. A Swiss Ephemeris Professional License should not be assumed to change the wrapper's license or grant rights to redistribute it. AGPL section 13 addresses remote network interaction with modified versions; GNU's FAQ identifies interactive web applications as examples of programs designed for such interaction. This local loopback setting is not a legal exemption. Counsel must review both licenses, bundled native/data artifacts, source-offer obligations, and the exact planned service and distribution model. This is an engineering summary, not legal advice.

If these terms are unsuitable, evaluate a separately licensed calculation engine and repeat the independent accuracy and data-licensing gate; do not substitute a library based only on its license label. AstroAI has no commercial licensing clearance. Public calculation endpoints remain gated by `ASTROLOGY_CALCULATIONS_ENABLED` and `SWISSEPH_LICENSE_CONFIRMED`, both false in local environment configuration and false in production. The separate loopback-only local development switch is not public enablement and does not grant licensing rights.
