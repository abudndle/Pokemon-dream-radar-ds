#!/bin/sh
# Compile isolated Nintendo DS and DSi ROMs without touching Pokemon save files.
# CI sets SKIP_HOST_TESTS=1 and SKIP_ROM_CHECK=1 in the compiler-only image.
set -eu
cd "$(dirname "$0")/.."
if [ "${SKIP_HOST_TESTS:-0}" != 1 ]; then
    make test-host test-syntax
fi
for platform in ds dsi; do
    # Platform-specific defines and linker specs require clean ARM object files.
    rm -rf build
    make "PLATFORM=$platform" check-sdk
    make "PLATFORM=$platform" -j2
    rom="dream_radar_${platform}.nds"
    test -s "$rom" || { echo "Missing build: $rom" >&2; exit 1; }
    if [ "${SKIP_ROM_CHECK:-0}" != 1 ]; then
        python3 scripts/check_nds.py "$rom"
    fi
done
printf 'Finished: dream_radar_ds.nds and dream_radar_dsi.nds\n'
