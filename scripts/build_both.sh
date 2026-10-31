#!/bin/sh
# Reproducible DS and DSi BlocksDS build; does not write to Pokemon saves.
set -eu
cd "$(dirname "$0")/.."
make test-host test-syntax
for platform in ds dsi; do
    make "PLATFORM=$platform" check-sdk
    make "PLATFORM=$platform" -j2
    rom="dream_radar_${platform}.nds"
    test -s "$rom" || { echo "Missing build: $rom" >&2; exit 1; }
    python3 scripts/check_nds.py "$rom"
done
printf 'Finished: dream_radar_ds.nds and dream_radar_dsi.nds\n'
