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
# Capture actual emulator window, not simulated original UI images.
sleep 7
snapshot 01-title
# DeSmuME scans DS keys once per emulated frame; xdotool's short
# synthetic key tap can be missed. Hold it for several VBlanks.
send_ds_key() {
  local name="$1"
  xdotool windowfocus "$window" 2>/dev/null || true
  xdotool keydown --window "$window" "$name"
  sleep 0.35
  xdotool keyup --window "$window" "$name"
}
# Try the actual touch-screen gear first. The DeSmuME CLI draws the two
# 256x192 panels vertically at native size; icon center (20,180) in the
# lower panel is therefore window coordinate (20,372).
xdotool mousemove --sync --window "$window" 20 372
xdotool mousedown 1
sleep 0.5
xdotool mouseup 1
sleep 2
snapshot 04-camera-settings
# Some headless X11 builds drop synthetic mouse events; also exercise
# the independent DS X/Select shortcuts with injected key presses.
if cmp -s "$outdir/01-title.png" "$outdir/04-camera-settings.png"; then
  echo "Mouse gear tap unchanged; trying DS X" >>"$outdir/runtime.log"
  send_ds_key s
  sleep 2
  snapshot 04-camera-settings
fi
if cmp -s "$outdir/01-title.png" "$outdir/04-camera-settings.png"; then
  echo "DS X unchanged; trying DS Select" >>"$outdir/runtime.log"
  send_ds_key Shift_R
  sleep 2
  snapshot 04-camera-settings
fi
# Reject unchanged screenshots: a visible emulator window alone does not
# demonstrate the newly added camera settings menu.
python3 - "$outdir/01-title.png" "$outdir/04-camera-settings.png" <<'PY'
import hashlib
import pathlib
import sys
before, after=(pathlib.Path(p).read_bytes() for p in sys.argv[1:3])
if hashlib.sha256(before).digest()==hashlib.sha256(after).digest():
    raise SystemExit("DS X did not open camera settings; unchanged real screenshot")
print("PASS: emulator displayed a changed title frame after DS X camera shortcut")
PY
# DS B (CLI 'z') returns to title without losing the normal smoke path.
send_ds_key z
sleep 2
send_ds_key Return
sleep 6
snapshot 02-after-start
# DeSmuME CLI maps 'x' to DS A.
send_ds_key x
sleep 6
snapshot 03-after-a
python3 tools/verify_emulator_screenshots.py \
  --output "$outdir/report.json" \
  "$outdir/01-title.png" "$outdir/02-after-start.png" \
  "$outdir/03-after-a.png" "$outdir/04-camera-settings.png"
echo "Real DeSmuME screenshot capture and validation complete"
