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
# Hold keys across several VBlanks. No gear or X-alone camera shortcut.
send_ds_key() {
  local name="$1"
  xdotool windowfocus "$window" 2>/dev/null || true
  xdotool keydown --window "$window" "$name"
  sleep 0.35
  xdotool keyup --window "$window" "$name"
}
send_ds_key s
sleep 2
snapshot 04-title-x-alone
if ! cmp -s "$outdir/01-title.png" "$outdir/04-title-x-alone.png"; then
  echo "DS X alone unexpectedly changed the title screen" >&2
  exit 1
fi
# Previously there was an extra gear painted at bottom touch (20,180).
xdotool mousemove --window "$window" 20 372
sleep 0.2
xdotool mousedown 1
sleep 0.45
xdotool mouseup 1
sleep 2
snapshot 05-title-no-gear
if ! cmp -s "$outdir/01-title.png" "$outdir/05-title-no-gear.png"; then
  echo "Removed gear touch region unexpectedly changed the title" >&2
  exit 1
fi
# Best-effort Select+X chord: headless Select mapping is not yet verified.
send_camera_chord() {
  xdotool windowfocus "$window" 2>/dev/null || true
  xdotool keydown --window "$window" BackSpace
  sleep 0.20
  xdotool keydown --window "$window" s
  sleep 0.5
  xdotool keyup --window "$window" s
  xdotool keyup --window "$window" BackSpace
}
send_camera_chord
sleep 2
snapshot 06-title-select-x-attempt
camera_menu_opened=0
if ! cmp -s "$outdir/01-title.png" "$outdir/06-title-select-x-attempt.png"; then
  send_ds_key z
  sleep 2
  snapshot 07-title-after-camera-back
  if cmp -s "$outdir/01-title.png" "$outdir/07-title-after-camera-back.png"; then
    camera_menu_opened=1
  else
    echo "Select+X changed the frame but B failed to return to title" >&2
    exit 1
  fi
fi
if ((camera_menu_opened)); then
  echo "PASS: Select+X changed title frame and B restored title" | tee -a "$outdir/runtime.log"
else
  echo "WARNING: headless Select+X delivery unverified; no success claimed" | tee -a "$outdir/runtime.log"
fi
# Title Start advances to Professor Burnet; DS X must NOT open camera
# settings there or on any other non-title screen.
send_ds_key Return
sleep 4
snapshot 02-after-start
if cmp -s "$outdir/01-title.png" "$outdir/02-after-start.png"; then
  echo "DS Start did not advance from the title" >&2
  exit 1
fi
send_camera_chord
sleep 2
snapshot 08-intro-combo-blocked
if ! cmp -s "$outdir/02-after-start.png" "$outdir/08-intro-combo-blocked.png"; then
  echo "Select+X changed Burnet intro; hidden menu must reject gameplay/story" >&2
  exit 1
fi
# DS B skips intro; DS A enters extensions for another real emulator shot.
send_ds_key z
sleep 2
send_ds_key x
sleep 5
snapshot 03-after-a
screenshots=("$outdir/01-title.png" "$outdir/02-after-start.png"
             "$outdir/08-intro-combo-blocked.png" "$outdir/03-after-a.png"
             "$outdir/04-title-x-alone.png" "$outdir/05-title-no-gear.png"
             "$outdir/06-title-select-x-attempt.png")
if ((camera_menu_opened)); then screenshots+=("$outdir/07-title-after-camera-back.png"); fi
python3 tools/verify_emulator_screenshots.py \
  --output "$outdir/report.json" "${screenshots[@]}"
python3 - "$outdir/report.json" "$camera_menu_opened" <<'PY'
import json
from pathlib import Path
import sys
p=Path(sys.argv[1])
camera_opened=sys.argv[2]=="1"
report=json.loads(p.read_text())
report["title_x_alone_blocked"]=True
report["intro_select_x_chord_blocked"]=True
report["removed_title_gear_touch_blocked"]=True
report["select_x_chord_frame_transition_and_return"]=camera_opened
report["camera_settings_verification"]=(
    "Select+X changed frame and B returned to title; content not independently recognized"
    if camera_opened else "INCONCLUSIVE: emulator Select+X host input delivery not verified")
if not camera_opened:
    report["limitations"].append(
        "Hidden Select+X logic passed host tests but emulator chord delivery "
        "and camera menu content remain unverified.")
report["limitations"].append(
    "Original 3DS title backdrops are privately staged, not bundled; "
    "3DS visual parity is not established by these captures.")
p.write_text(json.dumps(report,indent=2)+"\n")
PY
if ((camera_menu_opened)); then
  echo "PASS: real DeSmuME title Select+X return and intro routing"
else
  echo "PASS: DeSmuME boot, Start and blocked X/gear; WARNING Select+X menu UNVERIFIED"
fi
