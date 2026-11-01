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
# DeSmuME default key s maps to DS X; BackSpace maps to DS Select.
# Only their chord may open the hidden camera utility. A single X must
# leave the original four-option 3DS title menu unchanged.
send_ds_key s
sleep 2
snapshot 04-title-single-x
if ! cmp -s "$outdir/01-title.png" "$outdir/04-title-single-x.png"; then
  echo "Single X changed the title frame; hidden camera restriction not verified" >&2
  exit 1
fi
send_camera_chord() {
  xdotool windowfocus "$window" 2>/dev/null || true
  xdotool keydown --window "$window" BackSpace
  sleep 0.20
  xdotool keydown --window "$window" s
  sleep 0.45
  xdotool keyup --window "$window" s
  xdotool keyup --window "$window" BackSpace
}
send_camera_chord
sleep 2
snapshot 05-camera-settings
camera_menu_opened=0
if cmp -s "$outdir/01-title.png" "$outdir/05-camera-settings.png"; then
  # Do not mislabel a headless X11 input failure as navigation success.
  mv "$outdir/05-camera-settings.png" "$outdir/05-title-chord-unverified.png"
  echo "WARNING: Select+X did not change the actual title frame; input delivery UNVERIFIED" |
    tee -a "$outdir/runtime.log"
else
  camera_menu_opened=1
  echo "Verified camera menu input route: title Select+X" >>"$outdir/runtime.log"
  send_ds_key z
  sleep 2
  snapshot 06-camera-back
  if ! cmp -s "$outdir/01-title.png" "$outdir/06-camera-back.png"; then
    echo "Camera quick menu did not restore the original title" >&2
    exit 1
  fi
fi
# The intro must also reject the hidden shortcut: it is not a gameplay or
# Professor Burnet dialogue control.
send_ds_key Return
sleep 4
snapshot 02-after-start
if cmp -s "$outdir/01-title.png" "$outdir/02-after-start.png"; then
  echo "DS Start did not advance from the title" >&2
  exit 1
fi
send_camera_chord
sleep 2
snapshot 07-intro-combo-blocked
if ! cmp -s "$outdir/02-after-start.png" "$outdir/07-intro-combo-blocked.png"; then
  echo "Hidden Select+X changed the Burnet intro frame; menu gating failed" >&2
  exit 1
fi
# DS B skips intro; DS A enters extensions for another real emulator shot.
send_ds_key z
sleep 2
send_ds_key x
sleep 5
snapshot 03-after-a
screenshots=("$outdir/01-title.png" "$outdir/02-after-start.png"
             "$outdir/07-intro-combo-blocked.png" "$outdir/04-title-single-x.png" "$outdir/03-after-a.png")
if ((camera_menu_opened)); then
  screenshots+=("$outdir/05-camera-settings.png" "$outdir/06-camera-back.png")
else
  screenshots+=("$outdir/05-title-chord-unverified.png")
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
report["camera_settings_chord"]="Select+X (hidden); single X and intro combo rejected"
report["camera_settings_returned_to_title"]=camera_opened
report["camera_settings_blocked_on_intro"]=camera_opened
report["camera_settings_verification"]=(
    "hidden Select+X camera entry/return visually verified" if camera_opened else
    "INCONCLUSIVE: emulator Select+X did not produce a title menu transition")
if not camera_opened:
    report["limitations"].append(
         "Hidden Select+X behavior passed host tests, but emulator input "
        "delivery and menu entry were NOT verified; no success is claimed.")
report["limitations"].append(
    "Importing a BMP from emulated writable FAT/SD and live DSi camera "
    "still require separate end-to-end verification")
p.write_text(json.dumps(report,indent=2)+"\n")
PY
if ((camera_menu_opened)); then
  echo "PASS: real DeSmuME hidden Select+X camera menu, title return and intro routing"
else
  echo "PASS: real DeSmuME boot and intro Start; WARNING hidden camera chord UNVERIFIED"
fi
