#!/usr/bin/env bash
set -euo pipefail

# Build the official Swiss Ephemeris C library for Vercel's Linux x86-64
# Python runtime. The manylinux2014 toolchain targets glibc 2.17 compatibility.

REPO_ROOT="$(git rev-parse --show-toplevel)"
OUTPUT_DIR="${REPO_ROOT}/backend/native/linux-x64"
mkdir -p "${OUTPUT_DIR}"

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker is required. Install/start Docker Desktop, then rerun this script." >&2
  exit 1
fi

docker run --rm --platform linux/amd64 \
  -v "${OUTPUT_DIR}:/out" \
  quay.io/pypa/manylinux2014_x86_64:latest \
  /bin/bash -euo pipefail -c '
    command -v gcc
    command -v make
    command -v curl
    command -v readelf
    command -v objdump

    SOURCE_COMMIT="af9823fe7b06ffefe3d3968fdc5680be8b5eec5f"
    curl --fail --location --retry 3 \
      "https://github.com/aloistr/swisseph/archive/${SOURCE_COMMIT}.tar.gz" \
      --output /tmp/swisseph-source.tar.gz

    mkdir -p /tmp/swisseph-source
    tar -xzf /tmp/swisseph-source.tar.gz \
      --strip-components=1 -C /tmp/swisseph-source
    cd /tmp/swisseph-source

    OBJECTS="swedate.o swehouse.o swejpl.o swemmoon.o swemplan.o sweph.o swephlib.o swecl.o swehel.o"
    make -j2 CFLAGS="-O2 -Wall -fPIC" ${OBJECTS}

    gcc -shared -Wl,--no-undefined \
      -Wl,-soname,libastroai-swe.so \
      -o /out/libastroai-swe.so \
      ${OBJECTS} -lm -ldl

    chmod 755 /out/libastroai-swe.so
    ldd -r /out/libastroai-swe.so

    for symbol in swe_version swe_calc_ut swe_houses_ex swe_rise_trans swe_set_ephe_path; do
      if ! nm -D --defined-only /out/libastroai-swe.so | grep -Eq "[[:space:]]${symbol}$"; then
        echo "Missing required Swiss Ephemeris symbol: ${symbol}" >&2
        exit 1
      fi
    done

    MAX_GLIBC="$(objdump -T /out/libastroai-swe.so | grep -oE "GLIBC_[0-9]+(\\.[0-9]+)+" | sort -Vu | tail -n 1 || true)"
    echo "Maximum required glibc symbol version: ${MAX_GLIBC:-none}"
    if [ -n "${MAX_GLIBC}" ]; then
      LATEST="$(printf "%s\\n" "${MAX_GLIBC}" "GLIBC_2.17" | sort -V | tail -n 1)"
      if [ "${LATEST}" != "GLIBC_2.17" ]; then
        echo "Built library exceeds the manylinux2014 GLIBC_2.17 baseline." >&2
        exit 1
      fi
    fi

    file /out/libastroai-swe.so
    sha256sum /out/libastroai-swe.so
  '

echo
echo "Built: ${OUTPUT_DIR}/libastroai-swe.so"
echo "Next: set Vercel Production SWISSEPH_LIBRARY_PATH=native/linux-x64/libastroai-swe.so"
