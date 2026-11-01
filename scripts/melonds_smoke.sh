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
for app in flatpak xdotool import identify compare; do
  command -v "$app" >/dev/null || { echo "Missing $app" >&2; exit 1; }
done
export LIBGL_ALWAYS_SOFTWARE=1
export SDL_AUDIODRIVER=dummy
printf 'Emulator: melonDS Flatpak\nROM: %s\nDISPLAY: %s\n' "$rom" "${DISPLAY:-unset}" >"$out/runtime.log"
flatpak run net.kuribo64.melonDS "$rom" >"$out/melonds.log" 2>&1 &
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
  xdotool windowactivate --sync "$window" 2>/dev/null || true
  xdotool key --clearmodifiers "$key"
  sleep 2
}
touch_ds() {
  local x="$1" y="$2"
  xdotool windowactivate --sync "$window" 2>/dev/null || true
  xdotool mousemove --sync --window "$window" "$x" "$y"
  # Hold the stylus contact across several DS frames; a short X11 click can
  # fall entirely between melonDS touch-sampling VBlanks.
  xdotool mousedown 1
  sleep 0.35
  xdotool mouseup 1
  sleep 2
}
assert_changed() {
  local before="$1" after="$2"
  local diff
  diff="$(compare -metric AE "$out/$before.png" "$out/$after.png" null: 2>&1 || true)"
  # A state transition should change a substantial portion of the 256x403
  # dual-screen frame; reject identical or near-identical captures.
  if ! awk -v n="$diff" 'BEGIN { exit !(n+0 > 500) }'; then
    echo "Expected visible screen transition $before -> $after; changed pixels=$diff" >&2
    exit 1
  fi
  echo "Verified visible transition: $before -> $after ($diff pixels)" >>"$out/runtime.log"
}
sleep 10
snapshot 01-title
# The captured client window is 256x403: its menu bar occupies y=0..19,
# top DS screen y=20..211, and touchscreen y=211..402. Tap the center of
# the highlighted Start button (x=128, y≈269), not the cloud-count label.
touch_ds 128 269
snapshot 02-after-start-touch
assert_changed 01-title 02-after-start-touch
echo "PASS: melonDS touchscreen activated the highlighted Start menu item" |
  tee -a "$out/runtime.log"
