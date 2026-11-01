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
# Hold synthetic keys across several emulated VBlanks to avoid lost taps.
send_ds_key() {
  local name="$1"
  xdotool windowfocus "$window" 2>/dev/null || true
  xdotool keydown --window "$window" "$name"
  sleep 0.35
  xdotool keyup --window "$window" "$name"
}
# DS Start -> intro (on a fresh save). A real screen transition is required.
send_ds_key Return
sleep 6
snapshot 02-after-start
if cmp -s "$outdir/01-title.png" "$outdir/02-after-start.png"; then
  echo "DS Start did not advance the real emulator; smoke test failed" >&2
  exit 1
fi
# On intro, DS X ('s') is another camera shortcut. A headless Xvfb
# environment may not deliver SDL synthetic events: retain evidence but
# never treat a non-changing image as proof that the camera menu opened.
send_ds_key s
sleep 2
snapshot 04-camera-settings
if cmp -s "$outdir/02-after-start.png" "$outdir/04-camera-settings.png"; then
  # Lower panel begins at y=192 in this 256x384 DeSmuME SDL window.
  xdotool mousemove --window "$window" 20 372
  xdotool mousedown 1
  sleep 0.35
  xdotool mouseup 1
  sleep 2
  snapshot 04-camera-settings
fi
if cmp -s "$outdir/02-after-start.png" "$outdir/04-camera-settings.png"; then
  send_ds_key Shift_R
  sleep 2
  snapshot 04-camera-settings
fi
camera_input_changed=0
if ! cmp -s "$outdir/02-after-start.png" "$outdir/04-camera-settings.png"; then
  camera_input_changed=1
else
  echo "WARNING: camera menu input not confirmed under headless DeSmuME" | tee -a "$outdir/runtime.log"
fi
# B returns from the optional menu (or skips intro if no menu opened);
# retain a final gameplay screenshot, regardless of input responsiveness.
send_ds_key z
sleep 2
send_ds_key x
sleep 5
snapshot 03-after-a
python3 tools/verify_emulator_screenshots.py \
  --output "$outdir/report.json" \
  "$outdir/01-title.png" "$outdir/02-after-start.png" \
  "$outdir/03-after-a.png" "$outdir/04-camera-settings.png"
# The report distinguishes tested startup from an unverified menu transition.
python3 - "$outdir/report.json" "$camera_input_changed" <<'PY'
import json
from pathlib import Path
import sys
p=Path(sys.argv[1])
report=json.loads(p.read_text())
report["camera_settings_input_changed_frame"]=bool(int(sys.argv[2]))
if not report["camera_settings_input_changed_frame"]:
    report["limitations"].append(
        "Camera settings control was NOT verified by injected SDL input; "
        "Xvfb screenshot after camera shortcut matched the intro")
p.write_text(json.dumps(report,indent=2)+"\n")
PY
echo "Real DeSmuME boot and screenshot validation completed"
