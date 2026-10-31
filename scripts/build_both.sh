#!/bin/sh
# One DSi-enhanced NDS: DS-compatible fallback selected at runtime.
set -eu
cd "$(dirname "$0")/.."
if [ "${SKIP_HOST_TESTS:-0}" != 1 ]; then
    make test-host test-syntax
fi
rm -rf build
make check-sdk
make -j2
rom="dream_radar.nds"
test -s "$rom" || { echo "Missing build: $rom" >&2; exit 1; }
if [ "${SKIP_ROM_CHECK:-0}" != 1 ]; then
    python3 scripts/check_nds.py "$rom"
fi
printf 'Finished: dream_radar.nds (DS fallback and DSi enhanced)\n'
