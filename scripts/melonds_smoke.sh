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
  xdotool mousemove --window "$window" "$x" "$y"
  xdotool click 1
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
# Use real touchscreen taps for deterministic menu navigation. The screenshot
# window is 256x403: a 192px top screen followed by the 192px touch screen,
# with the melonDS menu strip above it. Touch centers match runtime hitboxes.
touch_ds 128 269
snapshot 02-intro
assert_changed 01-title 02-intro
# melonDS default B mapping is X. B skips the intro directly to the lab.
press_ds_key x
snapshot 03-lab
if compare -metric AE "$out/02-intro.png" "$out/03-lab.png" null: 2>&1 | awk 'BEGIN{n=0} {n=$1} END{exit !(n+0>500)}'; then
  :
else
  # Touch advances any remaining Burnet intro pages; retry up to four times.
  for _ in 1 2 3 4; do touch_ds 128 350; done
  snapshot 03-lab
  assert_changed 02-intro 03-lab
fi
# Lab row 0 is START SEARCH; extension row 0 is the Basic Extension.
touch_ds 128 224
snapshot 04-extensions
assert_changed 03-lab 04-extensions
touch_ds 128 244
snapshot 05-cloud-search
assert_changed 04-extensions 05-cloud-search
echo "PASS: real melonDS boot, title -> intro -> lab -> extensions -> radar navigation" |
  tee -a "$out/runtime.log"
