# Vercel-compatible Swiss Ephemeris native library

AstroAI's Vercel Python 3.12 runtime rejected the `swisseph-ffi==1.0.0` bundled
`linux-x64/libswe.so` because it requires `GLIBC_2.38`. This directory holds an
x86-64 Linux build of the official Swiss Ephemeris C library compiled against
the manylinux2014 / glibc 2.17 baseline.

Build it from the repository root with:

```bash
bash backend/scripts/build_sweph_vercel_compatible.sh
```

The script downloads the pinned official Swiss Ephemeris 2.10.3 release source
(commit `af9823fe7b06ffefe3d3968fdc5680be8b5eec5f`), compiles it inside
`quay.io/pypa/manylinux2014_x86_64`, checks required C symbols, and fails if the
result requires a GLIBC symbol newer than 2.17. It writes:

`backend/native/linux-x64/libastroai-swe.so`

The library is loaded through the existing `swisseph-ffi` ctypes wrapper by
setting this Vercel Production environment variable:

`SWISSEPH_LIBRARY_PATH=native/linux-x64/libastroai-swe.so`

The path is resolved relative to the Vercel backend project root. `backend/vercel.json`
explicitly includes the native library in the FastAPI Function bundle.

The C library remains subject to the Swiss Ephemeris licensing terms. Preserve
the repository's `THIRD_PARTY_LICENSES/Swiss-Ephemeris-LICENSE.txt` and
`THIRD_PARTY_NOTICES.md` when redistributing this build.
