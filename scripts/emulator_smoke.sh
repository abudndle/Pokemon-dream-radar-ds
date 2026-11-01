#!/usr/bin/env bash
# Actual Linux Nintendo DS emulator capture, not an asset/mockup screenshot.
set -euo pipefail
if [[ $# -ne 2 ]]; then
  echo "Usage: bash scripts/emulator_smoke.sh /path/to/game.nds output-directory" >&2
  exit 2
fi
rom="$(realpath "$1")"
outdir="$(realpath -m "$2")"
mkdir -p "$outdir"
if [[ ! -s "$rom" ]]; then
  echo "ROM missing or empty: $rom" >&2
  exit 1
fi
emulator="$(command -v desmume-cli || true)"
if [[ -z "$emulator" && -x /usr/games/desmume-cli ]]; then emulator=/usr/games/desmume-cli; fi
if [[ -z "$emulator" ]]; then
  echo "DeSmuME CLI not installed; no screenshot has been produced" >&2
  exit 1
fi
for app in xdotool import identify; do
  command -v "$app" >/dev/null || { echo "Missing $app" >&2; exit 1; }
done
export SDL_AUDIODRIVER=dummy
export SDL_RENDER_DRIVER=software
export LIBGL_ALWAYS_SOFTWARE=1
export SDL_VIDEO_X11_DGAMOUSE=0
printf 'Emulator: %s\nROM: %s\nDISPLAY: %s\n' "$emulator" "$rom" "${DISPLAY:-unset}" >"$outdir/runtime.log"
"$emulator" --disable-sound --disable-limiter "$rom" >"$outdir/emulator.log" 2>&1 &
pid=$!
cleanup() {
  kill "$pid" 2>/dev/null || true
  wait "$pid" 2>/dev/null || true
}
trap cleanup EXIT
window=""
for attempt in $(seq 1 35); do
  if ! kill -0 "$pid" 2>/dev/null; then
    echo "DeSmuME exited before opening a game window" >&2
    cat "$outdir/emulator.log" >&2
    exit 1
  fi
  window="$(xdotool search --onlyvisible --name '[Dd]e[Ss][Mm]u[Mm][Ee]' 2>/dev/null | head -n 1 || true)"
  if [[ -n "$window" ]]; then break; fi
  sleep 1
done
if [[ -z "$window" ]]; then
  echo "No visible emulator window after 35s; cannot claim a boot screenshot" >&2
  xwininfo -root -tree >"$outdir/window-tree.txt" 2>&1 || true
  exit 1
fi
echo "Window XID: $window" >>"$outdir/runtime.log"
xwininfo -id "$window" >>"$outdir/runtime.log" 2>&1 || true
snapshot() {
  local name="$1"
  kill -0 "$pid" 2>/dev/null || { echo "Emulator exited before $name" >&2; exit 1; }
  import -silent -window "$window" "$outdir/$name.png"
  identify "$outdir/$name.png" >>"$outdir/runtime.log"
}
# Capture actual DeSmuME window, never reference art or synthetic mockups.
sleep 7
snapshot 01-title
# Hold keys across several VBlanks and send a release before the next press.
send_ds_key() {
  local name="$1"
  xdotool windowfocus "$window" 2>/dev/null || true
  xdotool keydown --window "$window" "$name"
  sleep 0.35
  xdotool keyup --window "$window" "$name"
}
# DS Start -> Burnet introduction on a fresh save.
send_ds_key Return
sleep 4
snapshot 02-after-start
if cmp -s "$outdir/01-title.png" "$outdir/02-after-start.png"; then
  echo "DS Start did not advance the real emulator; smoke test failed" >&2
  exit 1
fi
# Second DS Start opens camera menu ONLY while Burnet introduction is active.
# This keyboard action is verified in the real emulator, unlike synthetic
# touchscreen injection on some SDL/Xvfb runners.
send_ds_key Return
sleep 3
snapshot 04-camera-settings
if cmp -s "$outdir/02-after-start.png" "$outdir/04-camera-settings.png"; then
  echo "Camera quick settings did not open from intro via DS Start" >&2
  exit 1
fi
# DS B must close the menu, restoring the original intro screen exactly.
send_ds_key z
sleep 2
snapshot 05-camera-back
if ! cmp -s "$outdir/02-after-start.png" "$outdir/05-camera-back.png"; then
  echo "Camera quick settings did not return to the original intro" >&2
  exit 1
fi
# DS B now skips intro; DS A enters extensions for a further real shot.
send_ds_key z
sleep 2
send_ds_key x
sleep 5
snapshot 03-after-a
python3 tools/verify_emulator_screenshots.py \
  --output "$outdir/report.json" \
  "$outdir/01-title.png" "$outdir/02-after-start.png" \
  "$outdir/04-camera-settings.png" "$outdir/05-camera-back.png" \
  "$outdir/03-after-a.png"
python3 - "$outdir/report.json" <<'PY'
import json
from pathlib import Path
import sys
p=Path(sys.argv[1])
report=json.loads(p.read_text())
report["camera_settings_input_changed_frame"]=True
report["camera_settings_returned_to_intro"]=True
report["camera_settings_verification"]="actual intro Start transition and B restoration in Linux DeSmuME"
report["limitations"].append(
    "Importing a BMP from emulated writable FAT/SD and live DSi camera "
    "still require separate end-to-end verification")
p.write_text(json.dumps(report,indent=2)+"\n")
PY
echo "PASS: real DeSmuME camera settings menu opened and returned to intro"
