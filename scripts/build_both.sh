#!/bin/sh
# One DSi-enhanced NDS: DS-compatible fallback selected at runtime.
set -eu
cd "$(dirname "$0")/.."
if [ "${SKIP_HOST_TESTS:-0}" != 1 ]; then
    make test-host test-syntax
fi
rm -rf build
# Compile source-derived title-pane geometry into the ROM. Native original
# CLPA keyframes are optional private SD/FAT overrides, never public assets.
if command -v python3 >/dev/null 2>&1; then
    python3 tools/stage_title_ui.py ui_mapping/original_pane_geometry.json nitrofs/title.drui
    python3 tools/stage_title_ui.py ui_mapping/original_pane_geometry.json nitrofs/scanlist.drui --layout MnIf_S_ScanList.bclyt
    python3 tools/stage_title_ui.py ui_mapping/original_pane_geometry.json nitrofs/mainmenu.drui --layout MnIf_S_MainMenuList.bclyt --offset-y 24
    python3 tools/stage_title_ui.py ui_mapping/original_pane_geometry.json nitrofs/shoplist.drui --layout MnIf_S_ShopList.bclyt
elif [ ! -s nitrofs/title.drui ] || [ ! -s nitrofs/scanlist.drui ] || [ ! -s nitrofs/mainmenu.drui ] || [ ! -s nitrofs/shoplist.drui ]; then
    echo "Stage both title.drui and scanlist.drui before entering the SDK-only Docker image" >&2
    exit 1
fi
make check-sdk
make -j2
rom="dream_radar.nds"
test -s "$rom" || { echo "Missing build: $rom" >&2; exit 1; }
if [ "${SKIP_ROM_CHECK:-0}" != 1 ]; then
    python3 scripts/check_nds.py "$rom"
fi
printf 'Finished: dream_radar.nds (DS fallback and DSi enhanced)\n'
