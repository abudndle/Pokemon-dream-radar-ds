#!/usr/bin/env bash
# Launch the built DS ROM in the official melonDS Flatpak and capture its
# real application window. This is a boot/screenshot smoke test, not gameplay
# parity or DSi camera verification.
set -euo pipefail
if [[ $# -ne 2 ]]; then
  echo "Usage: $0 /path/to/game.nds output-directory" >&2
  exit 2
fi
rom="$(realpath "$1")"
out="$(realpath -m "$2")"
mkdir -p "$out"
test -s "$rom"
for app in xdotool import identify python3; do
  command -v "$app" >/dev/null || { echo "Missing $app" >&2; exit 1; }
done
export LIBGL_ALWAYS_SOFTWARE=1
export SDL_AUDIODRIVER=dummy
printf 'Emulator: melonDS\nLauncher: %s\nROM: %s\nDISPLAY: %s\n' \
  "${MELONDS_BIN:-net.kuribo64.melonDS Flatpak}" "$rom" "${DISPLAY:-unset}" >"$out/runtime.log"
if [[ -n "${MELONDS_BIN:-}" ]]; then
  launcher=("$MELONDS_BIN")
else
  command -v flatpak >/dev/null || { echo "Missing flatpak or MELONDS_BIN" >&2; exit 1; }
  launcher=(flatpak run net.kuribo64.melonDS)
fi
"${launcher[@]}" "$rom" >"$out/melonds.log" 2>&1 &
pid=$!
cleanup(){ kill "$pid" 2>/dev/null || true; wait "$pid" 2>/dev/null || true; }
trap cleanup EXIT
window=""
for attempt in $(seq 1 60); do
  window="$(xdotool search --onlyvisible --name 'melonDS' 2>/dev/null | head -n 1 || true)"
  [[ -n "$window" ]] && break
  kill -0 "$pid" 2>/dev/null || { cat "$out/melonds.log" >&2; exit 1; }
  sleep 1
done
if [[ -z "$window" ]]; then
  xwininfo -root -tree >"$out/window-tree.txt" 2>&1 || true
  cat "$out/melonds.log" >&2
  echo "melonDS window did not appear; no screenshot claimed" >&2
  exit 1
fi
echo "Window XID: $window" >>"$out/runtime.log"
xwininfo -id "$window" >>"$out/runtime.log" 2>&1 || true
snapshot() {
  local name="$1"
  kill -0 "$pid" 2>/dev/null || { echo "melonDS exited before $name" >&2; exit 1; }
  import -silent -window "$window" "$out/$name.png"
  identify "$out/$name.png" | tee -a "$out/runtime.log"
  test -s "$out/$name.png"
}
press_ds_key() {
  local key="$1"
  xdotool windowfocus "$window"
  xdotool keydown --clearmodifiers "$key"
  sleep 0.2
  xdotool keyup "$key"
  sleep 2
}
touch_ds() {
  local x="$1" y="$2"
  xdotool windowfocus "$window"
  xdotool mousemove --sync --window "$window" "$x" "$y"
  # Hold the stylus contact across several DS frames; a short X11 click can
  # fall entirely between melonDS touch-sampling VBlanks.
  xdotool mousedown 1
  sleep 0.35
  xdotool mouseup 1
  sleep 2
}
sleep 10
snapshot 01-title
# The captured client window is 256x403: its menu bar occupies y=0..19,
# top DS screen y=20..211, and touchscreen y=211..402. Tap the center of
# the highlighted Start button (x=128, y≈269), not the cloud-count label.
touch_ds 128 269
snapshot 02-intro
touch_verified=0
if python3 tools/verify_melonds_navigation.py "$out" --stage 02-intro >>"$out/runtime.log" 2>&1; then
  touch_verified=1
  echo "PASS: title stylus input entered the intro" | tee -a "$out/runtime.log"
else
  mv "$out/02-intro.png" "$out/02-title-touch-unverified.png"
  echo "WARNING: title stylus input unverified; testing independent DS Start input" | tee -a "$out/runtime.log"
  press_ds_key Return
  snapshot 02-intro
  python3 tools/verify_melonds_navigation.py "$out" --stage 02-intro
fi
# Explicit workflow mappings: DS B=X, DS A=Z. Each action is checked against
# the real screen heading so animation alone cannot satisfy the smoke test.
press_ds_key x
snapshot 03-lab
press_ds_key z
snapshot 04-extensions
press_ds_key z
snapshot 05-radar
# Use actual fallback-sprite pixels to aim toward the nearest visible cloud.
# The planner is intentionally non-fatal: a missing/unrecognized cloud is
# evidence of a limitation, not permission to fabricate a successful shot.
aim_ds_key() {
  local key="$1" seconds="$2"
  [[ "$key" == none ]] && return 0
  xdotool windowfocus "$window"
  xdotool keydown --clearmodifiers "$key"
  sleep "$seconds"
  xdotool keyup "$key"
  sleep 0.4
}
if python3 tools/plan_melonds_aim.py "$out/05-radar.png" >"$out/aim-plan.json"; then
  read -r horizontal horizontal_seconds vertical vertical_seconds < <(
    python3 -c 'import json,sys; p=json.load(open(sys.argv[1])); print(p["horizontal_key"], p["horizontal_seconds"], p["vertical_key"], p["vertical_seconds"])' "$out/aim-plan.json"
  )
  aim_ds_key "$horizontal" "$horizontal_seconds"
  aim_ds_key "$vertical" "$vertical_seconds"
  snapshot 05-radar-aimed
else
  echo "WARNING: screenshot-guided aim unavailable; trying center reticle" | tee -a "$out/runtime.log"
fi
# The original A button fires the beam in radar. Compare the actual counter
# frame after firing; an input attempt alone is not a successful cloud hit.
press_ds_key z
snapshot 05-radar-postfire
# Dream Orbs appear only after a cloud is hit. Attempt a separate Orb shot
# from the actual post-fire screenshot; never infer collection from the input.
if python3 tools/plan_melonds_aim.py "$out/05-radar-postfire.png" --target orb >"$out/orb-aim-plan.json"; then
  read -r horizontal horizontal_seconds vertical vertical_seconds < <(
    python3 -c 'import json,sys; p=json.load(open(sys.argv[1])); print(p["horizontal_key"], p["horizontal_seconds"], p["vertical_key"], p["vertical_seconds"])' "$out/orb-aim-plan.json"
  )
  aim_ds_key "$horizontal" "$horizontal_seconds"
  aim_ds_key "$vertical" "$vertical_seconds"
  snapshot 05-radar-orb-aimed
  press_ds_key z
  snapshot 05-radar-orb-postfire
else
  echo "WARNING: no visible pink Dream Orb target; collection not verified" | tee -a "$out/runtime.log"
fi
press_ds_key x
snapshot 06-results
press_ds_key x
snapshot 07-lab-return
python3 tools/verify_melonds_navigation.py "$out" --touch-verified "$touch_verified"
if [[ "${REQUIRE_TOUCH:-0}" == 1 && "$touch_verified" != 1 ]]; then
  echo "Strict stylus check failed; keyboard navigation passed independently" >&2
  exit 1
fi
