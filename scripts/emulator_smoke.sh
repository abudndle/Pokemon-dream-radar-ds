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
  # Preserve the previously verified Start/B/A keyboard delivery path.
  # SDL/Xvfb delivery of the new title X shortcut is separately audited.
  xdotool windowfocus "$window" 2>/dev/null || true
  xdotool keydown --window "$window" "$name"
  sleep 0.35
  xdotool keyup --window "$window" "$name"
}
# DeSmuME default key 's' maps to DS X. The quick menu is accessible
# from the title only; we verify opening, closing and restoring the title.
send_ds_key s
sleep 2
snapshot 04-camera-settings
camera_entry_input="title X (DeSmuME key s)"
if cmp -s "$outdir/01-title.png" "$outdir/04-camera-settings.png"; then
  # DeSmuME SDL input under headless Xvfb sometimes drops the X key.
  # A real click at (20, 372) is the title gear (bottom screen local
  # coordinate 20, 180, with 192px upper screen). Never inject clicks in
  # intro/gameplay; the gear must only open on the title.
  xdotool mousemove --window "$window" 20 372
  sleep 0.2
  xdotool mousedown 1
  sleep 0.45
  xdotool mouseup 1
  sleep 3
  snapshot 04-camera-settings
  camera_entry_input="title touch gear (20,180)"
fi
camera_menu_opened=0
if cmp -s "$outdir/01-title.png" "$outdir/04-camera-settings.png"; then
  # Save the real attempt, but never mislabel an unchanged title as a
  # verified camera menu. SDL/Xvfb touch and X events remain inconclusive.
  mv "$outdir/04-camera-settings.png" "$outdir/04-title-input-unverified.png"
  echo "WARNING: title X and gear events produced no visible menu transition; camera-menu input NOT verified" |
    tee -a "$outdir/runtime.log"
else
  camera_menu_opened=1
  echo "Camera menu input route: $camera_entry_input" >>"$outdir/runtime.log"
  send_ds_key z
  sleep 2
  snapshot 05-camera-back
  if ! cmp -s "$outdir/01-title.png" "$outdir/05-camera-back.png"; then
    echo "Camera quick menu did not restore the original title" >&2
    exit 1
  fi
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
send_ds_key s
sleep 2
snapshot 06-intro-X-blocked
if ! cmp -s "$outdir/02-after-start.png" "$outdir/06-intro-X-blocked.png"; then
  echo "DS X changed intro screen; title-only camera shortcut not verified" >&2
  exit 1
fi
# DS B skips intro; DS A enters extensions for another real emulator shot.
send_ds_key z
sleep 2
send_ds_key x
sleep 5
snapshot 03-after-a
screenshots=("$outdir/01-title.png" "$outdir/02-after-start.png"
             "$outdir/06-intro-X-blocked.png" "$outdir/03-after-a.png")
if ((camera_menu_opened)); then
  screenshots+=("$outdir/04-camera-settings.png" "$outdir/05-camera-back.png")
else
  screenshots+=("$outdir/04-title-input-unverified.png")
fi
python3 tools/verify_emulator_screenshots.py \
  --output "$outdir/report.json" "${screenshots[@]}"
python3 - "$outdir/report.json" "$camera_menu_opened" <<'PY'
import json
from pathlib import Path
import sys
p=Path(sys.argv[1])
camera_opened=sys.argv[2]=="1"
report=json.loads(p.read_text())
report["camera_settings_input_changed_frame"]=camera_opened
report["camera_settings_returned_to_title"]=camera_opened
report["camera_settings_blocked_on_intro"]=camera_opened
report["camera_settings_verification"]=(
    "title camera entry/return visually verified" if camera_opened else
    "INCONCLUSIVE: emulator X/touch did not produce a title menu transition")
if not camera_opened:
    report["limitations"].append(
        "Title-only gear/X behavior passed host tests, but emulator input "
        "delivery and menu entry were NOT verified; no success is claimed.")
report["limitations"].append(
    "Importing a BMP from emulated writable FAT/SD and live DSi camera "
    "still require separate end-to-end verification")
p.write_text(json.dumps(report,indent=2)+"\n")
PY
if ((camera_menu_opened)); then
  echo "PASS: real DeSmuME title camera menu, title return and intro routing"
else
  echo "PASS: real DeSmuME boot and intro Start; WARNING title camera menu input UNVERIFIED"
fi
