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
  local key="$1" settle="${2:-2}"
  xdotool windowfocus "$window"
  xdotool keydown --clearmodifiers "$key"
  sleep 0.2
  xdotool keyup "$key"
  sleep "$settle"
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
  local key="$1" seconds="$2" settle="${3:-0.4}"
  [[ "$key" == none ]] && return 0
  xdotool windowfocus "$window"
  xdotool keydown --clearmodifiers "$key"
  sleep "$seconds"
  xdotool keyup "$key"
  sleep "$settle"
}
if python3 tools/plan_melonds_aim.py "$out/05-radar.png" >"$out/aim-plan.json"; then
  read -r horizontal horizontal_seconds vertical vertical_seconds < <(
    python3 -c 'import json,sys; p=json.load(open(sys.argv[1])); print(p["horizontal_key"], p["horizontal_seconds"], p["vertical_key"], p["vertical_seconds"])' "$out/aim-plan.json"
  )
  aim_ds_key "$horizontal" "$horizontal_seconds"
  aim_ds_key "$vertical" "$vertical_seconds"
  snapshot 05-radar-aimed
  # CI emulation speed varies, so milliseconds are not a fixed DS frame count.
  # Re-read actual pixels after movement and correct the remaining offset
  # before firing; four bounded corrections also permit offscreen reacquisition.
  for correction in 1 2 3 4; do
    if ! python3 tools/plan_melonds_aim.py "$out/05-radar-aimed.png" >"$out/aim-correction-$correction.json"; then
      break
    fi
    read -r horizontal horizontal_seconds vertical vertical_seconds < <(
      python3 -c 'import json,sys; p=json.load(open(sys.argv[1])); x=p["offset"]["x"]; y=p["offset"]["y"]; done=abs(x)<=7 and abs(y)<=7; print("none" if done else p["horizontal_key"], 0 if done else round(min(0.3,p["horizontal_seconds"]*1.5),3), "none" if done else p["vertical_key"], 0 if done else round(min(0.3,p["vertical_seconds"]*1.5),3))' "$out/aim-correction-$correction.json"
    )
    [[ "$horizontal" == none && "$vertical" == none ]] && break
    aim_ds_key "$horizontal" "$horizontal_seconds"
    aim_ds_key "$vertical" "$vertical_seconds"
    snapshot 05-radar-aimed
  done
else
  echo "WARNING: screenshot-guided aim unavailable; no blind cloud shot" | tee -a "$out/runtime.log"
fi
# A gold edge marker is a navigation cue, never a hittable cloud. Recheck
# a FRESH screenshot before firing; moving the reticle can reveal an offscreen
# cloud or leave the last visible target too far away to hit.
snapshot 05-radar-prefire
if python3 tools/plan_melonds_aim.py "$out/05-radar-prefire.png" \
    >"$out/cloud-fire-check.json" &&
   python3 -c 'import json,sys; p=json.load(open(sys.argv[1])); sys.exit(not (p["target_type"]=="cloud" and p["within_safe_fire_radius"]))' \
    "$out/cloud-fire-check.json"; then
  press_ds_key z 0.12
else
  echo "WARNING: cloud not aligned or only an offscreen marker; skipped blind shot" | tee -a "$out/runtime.log"
fi
# A changed counter after a real A input is the only evidence of a cloud hit.
snapshot 05-radar-postfire
# A changed counter can indicate an Orb drop; a GOLD encounter label and
# independent timer are required to assert a sphere transition.
latest_radar="$out/05-radar-postfire.png"
if python3 tools/verify_melonds_navigation.py "$out" \
    --observe-search-screenshot "$latest_radar" >"$out/search-first-state.json"; then
  if python3 -c 'import json,sys; sys.exit(json.load(open(sys.argv[1]))["state"] != "sphere")' \
      "$out/search-first-state.json"; then
    cp "$latest_radar" "$out/05-sphere-encounter.png"
    echo "PASS: real sphere encounter screen recognized after cloud shot" | tee -a "$out/runtime.log"
  fi
else
  echo "WARNING: postfire frame was neither a recognized radar nor encounter" | tee -a "$out/runtime.log"
fi
# Dream Orbs live only 210 DS frames (~3.5 seconds). Avoid the usual
# two-second navigation settle after cloud fire and use short aim settles so
# the screenshot-guided Orb attempt occurs before the target expires. Verify
# collection independently from the counters, never from the input alone.
if [[ ! -f "$out/05-sphere-encounter.png" ]] && \
   python3 tools/plan_melonds_aim.py "$out/05-radar-postfire.png" --target orb >"$out/orb-aim-plan.json"; then
  read -r horizontal horizontal_seconds vertical vertical_seconds < <(
    python3 -c 'import json,sys; p=json.load(open(sys.argv[1])); print(p["horizontal_key"], p["horizontal_seconds"], p["vertical_key"], p["vertical_seconds"])' "$out/orb-aim-plan.json"
  )
  aim_ds_key "$horizontal" "$horizontal_seconds" 0.06
  aim_ds_key "$vertical" "$vertical_seconds" 0.06
  snapshot 05-radar-orb-aimed
  for correction in 1 2 3; do
    if ! python3 tools/plan_melonds_aim.py "$out/05-radar-orb-aimed.png" --target orb >"$out/orb-aim-correction-$correction.json"; then
      break
    fi
    read -r horizontal horizontal_seconds vertical vertical_seconds < <(
      python3 -c 'import json,sys; p=json.load(open(sys.argv[1])); x=p["offset"]["x"]; y=p["offset"]["y"]; done=abs(x)<=4 and abs(y)<=4; print("none" if done else p["horizontal_key"], 0 if done else round(min(0.4,p["horizontal_seconds"]*1.5),3), "none" if done else p["vertical_key"], 0 if done else round(min(0.4,p["vertical_seconds"]*1.5),3))' "$out/orb-aim-correction-$correction.json"
    )
    [[ "$horizontal" == none && "$vertical" == none ]] && break
    aim_ds_key "$horizontal" "$horizontal_seconds" 0.06
    aim_ds_key "$vertical" "$vertical_seconds" 0.06
    snapshot 05-radar-orb-aimed
  done
  # A moving Orb can leave the reticle during correction. Do not fire at a
  # cloud just because an Orb was visible in an earlier screenshot.
  latest_radar="$out/05-radar-orb-aimed.png"
  if python3 tools/plan_melonds_aim.py "$latest_radar" --target orb \
      >"$out/orb-fire-check.json" &&
     python3 -c 'import json,sys; sys.exit(not json.load(open(sys.argv[1]))["within_safe_fire_radius"])' \
      "$out/orb-fire-check.json"; then
    press_ds_key z 0.12
    snapshot 05-radar-orb-postfire
    latest_radar="$out/05-radar-orb-postfire.png"
  else
    echo "WARNING: moving Orb not aligned with reticle; skipped unsafe shot" | tee -a "$out/runtime.log"
  fi
else
  if [[ -f "$out/05-sphere-encounter.png" ]]; then
    echo "INFO: sphere encounter replaced Orb-collection stage" | tee -a "$out/runtime.log"
  else
    echo "WARNING: no visible pink Dream Orb target; collection not verified" | tee -a "$out/runtime.log"
  fi
fi
# The initial pink cloud can produce Orbs instead of an encounter. Try
# at most eight bounded acquisition attempts (including offscreen cues),
# always using fresh actual emulator screenshots.
# The last cloud can finish the outing; recognize a genuine Results heading
# instead of assuming a B-button press is still in radar. Never assert a
# sphere without its class label and active timer.
for attempt in 1 2 3 4 5 6 7 8; do
  [[ -f "$out/05-sphere-encounter.png" ]] && break
  if ! python3 tools/verify_melonds_navigation.py "$out" \
      --observe-search-screenshot "$latest_radar" >"$out/search-retry-$attempt-before.json"; then
    echo "WARNING: cannot identify search state before retry $attempt" | tee -a "$out/runtime.log"
    break
  fi
  read -r search_state clouds < <(
    python3 -c 'import json,sys; s=json.load(open(sys.argv[1])); print(s["state"], s.get("radar_counters",{}).get("clouds",0))' \
      "$out/search-retry-$attempt-before.json"
  )
  [[ "$search_state" == radar && "$clouds" -gt 0 ]] || break
  if ! python3 tools/plan_melonds_aim.py "$latest_radar" >"$out/aim-retry-$attempt.json"; then
    echo "WARNING: no recognizable cloud for retry $attempt" | tee -a "$out/runtime.log"
    break
  fi
  read -r horizontal horizontal_seconds vertical vertical_seconds < <(
    python3 -c 'import json,sys; p=json.load(open(sys.argv[1])); print(p["horizontal_key"],p["horizontal_seconds"],p["vertical_key"],p["vertical_seconds"])' \
      "$out/aim-retry-$attempt.json"
  )
  aim_ds_key "$horizontal" "$horizontal_seconds"
  aim_ds_key "$vertical" "$vertical_seconds"
  snapshot "05-radar-retry-$attempt-aimed"
  for correction in 1 2 3 4; do
    if ! python3 tools/plan_melonds_aim.py "$out/05-radar-retry-$attempt-aimed.png" \
        >"$out/aim-retry-$attempt-correction-$correction.json"; then
      break
    fi
    read -r horizontal horizontal_seconds vertical vertical_seconds < <(
      python3 -c 'import json,sys; p=json.load(open(sys.argv[1])); x=p["offset"]["x"];y=p["offset"]["y"];done=abs(x)<=7 and abs(y)<=7; print("none" if done else p["horizontal_key"],0 if done else round(min(0.3,p["horizontal_seconds"]*1.5),3),"none" if done else p["vertical_key"],0 if done else round(min(0.3,p["vertical_seconds"]*1.5),3))' \
        "$out/aim-retry-$attempt-correction-$correction.json"
    )
    [[ "$horizontal" == none && "$vertical" == none ]] && break
    aim_ds_key "$horizontal" "$horizontal_seconds"
    aim_ds_key "$vertical" "$vertical_seconds"
    snapshot "05-radar-retry-$attempt-aimed"
  done
  snapshot "05-radar-retry-$attempt-prefire"
  latest_radar="$out/05-radar-retry-$attempt-prefire.png"
  if ! python3 tools/plan_melonds_aim.py "$latest_radar" \
      >"$out/cloud-retry-$attempt-fire-check.json" ||
     ! python3 -c 'import json,sys; p=json.load(open(sys.argv[1])); sys.exit(not (p["target_type"]=="cloud" and p["within_safe_fire_radius"]))' \
      "$out/cloud-retry-$attempt-fire-check.json"; then
    echo "WARNING: retry $attempt cloud still offscreen or unaligned; moving to next acquisition" | tee -a "$out/runtime.log"
    continue
  fi
  press_ds_key z 0.12
  snapshot "05-radar-retry-$attempt-postfire"
  latest_radar="$out/05-radar-retry-$attempt-postfire.png"
  if ! python3 tools/verify_melonds_navigation.py "$out" \
      --observe-search-screenshot "$latest_radar" >"$out/search-retry-$attempt-after.json"; then
    if python3 tools/verify_melonds_navigation.py "$out" \
        --observe-results-screenshot "$latest_radar" >/dev/null 2>&1; then
      cp "$latest_radar" "$out/06-results.png"
      echo "INFO: final cloud led directly to verified Results heading" | tee -a "$out/runtime.log"
    else
      echo "WARNING: unrecognized frame after retry $attempt" | tee -a "$out/runtime.log"
    fi
    break
  fi
  if python3 -c 'import json,sys; sys.exit(json.load(open(sys.argv[1]))["state"] != "sphere")' \
      "$out/search-retry-$attempt-after.json"; then
    cp "$latest_radar" "$out/05-sphere-encounter.png"
    echo "PASS: real sphere encounter screen recognized on retry $attempt" | tee -a "$out/runtime.log"
    break
  fi
done
# A sphere screenshot proves only an encounter. Exercise real A-button firing
# during a bounded directional sweep, then inspect each actual frame for the
# capture meter and for a catalog-backed Results reward. The sweep is a
# fallback, not an assertion of a capture; the target may move or evade it.
capture_last=""
if [[ -f "$out/05-sphere-encounter.png" ]]; then
  echo "INFO: exercising bounded live sphere shooting; reward not yet verified" | tee -a "$out/runtime.log"
  xdotool windowfocus "$window"
  xdotool keydown --clearmodifiers z
  capture_last="$out/05-sphere-encounter.png"
  for step in $(seq 1 24); do
    sweep=$(( (step - 1) % 12 + 1 ))
    case "$sweep" in
      1)  direction=Right; seconds=0.40 ;;
      2)  direction=Up;    seconds=0.17 ;;
      3)  direction=Left;  seconds=0.70 ;;
      4)  direction=Down;  seconds=0.14 ;;
      5)  direction=Right; seconds=0.70 ;;
      6)  direction=Down;  seconds=0.14 ;;
      7)  direction=Left;  seconds=0.70 ;;
      8)  direction=Down;  seconds=0.14 ;;
      9)  direction=Right; seconds=0.70 ;;
      10) direction=Up;    seconds=0.20 ;;
      11) direction=Left;  seconds=0.70 ;;
      12) direction=Down;  seconds=0.18 ;;
    esac
    # Sample a fresh frame after the previous movement. The encounter art
    # moves during screenshots; a stale one-frame position can chase the
    # target indefinitely. Extrapolate only a bounded two-frame displacement.
    previous_sphere="$capture_last"
    snapshot "05-sphere-before-$step"
    current_sphere="$out/05-sphere-before-$step.png"
    # Unknown artwork/backgrounds fail closed to the bounded manual sweep.
    if python3 tools/plan_melonds_aim.py "$current_sphere" --target sphere \
        --previous-screenshot "$previous_sphere" \
        >"$out/sphere-aim-$step.json" 2>/dev/null; then
      read -r horizontal horizontal_seconds vertical vertical_seconds < <(
        python3 -c 'import json,sys; p=json.load(open(sys.argv[1])); print(p["horizontal_key"],p["horizontal_seconds"],p["vertical_key"],p["vertical_seconds"])' \
          "$out/sphere-aim-$step.json"
      )
      aim_ds_key "$horizontal" "$horizontal_seconds"
      aim_ds_key "$vertical" "$vertical_seconds"
      sleep 0.35
    else
      aim_ds_key "$direction" "$seconds"
    fi
    capture_last="$out/05-sphere-sweep-$step.png"
    snapshot "05-sphere-sweep-$step"
    if python3 tools/verify_melonds_navigation.py "$out" \
        --observe-reward-screenshot "$capture_last" \
        >"$out/sphere-reward-attempt.json" 2>/dev/null; then
      mv "$out/sphere-reward-attempt.json" "$out/sphere-reward.json"
      cp "$capture_last" "$out/05-capture-reward.png"
      echo "PASS: real emulator Results screen contains a catalog-backed capture reward" | tee -a "$out/runtime.log"
      break
    fi
    rm -f "$out/sphere-reward-attempt.json"
    if python3 tools/verify_melonds_navigation.py "$out" \
        --observe-capture-progress "$capture_last" \
        >"$out/sphere-progress-$step.json" 2>/dev/null; then
      echo "INFO: sphere sweep $step meter observed" >>"$out/runtime.log"
    elif python3 tools/verify_melonds_navigation.py "$out" --observe-results-screenshot "$capture_last" \
        >/dev/null 2>&1; then
      echo "INFO: encounter ended without a verified capture reward" | tee -a "$out/runtime.log"
      break
    else
      echo "WARNING: unrecognized sphere/reward frame at step $step" | tee -a "$out/runtime.log"
      break
    fi
  done
  xdotool keyup z
fi
if [[ -f "$out/05-capture-reward.png" ]]; then
  cp "$out/05-capture-reward.png" "$out/06-results.png"
elif [[ -f "$out/06-results.png" ]]; then
  echo "INFO: Results already observed after the final cloud" >>"$out/runtime.log"
elif [[ -n "$capture_last" ]] &&
     python3 tools/verify_melonds_navigation.py "$out" \
       --observe-reward-screenshot "$capture_last" >/dev/null 2>&1; then
  cp "$capture_last" "$out/06-results.png"
elif [[ -n "$capture_last" ]] &&
     python3 tools/verify_melonds_navigation.py "$out" --observe-results-screenshot "$capture_last" >/dev/null 2>&1; then
  cp "$capture_last" "$out/06-results.png"
else
  press_ds_key x
  snapshot 06-results
fi
press_ds_key x
snapshot 07-lab-return
python3 tools/verify_melonds_navigation.py "$out" --touch-verified "$touch_verified"
if [[ "${REQUIRE_CAPTURE:-0}" == 1 && ! -f "$out/05-capture-reward.png" ]]; then
  echo "Strict capture acceptance failed: no verified reward screenshot" >&2
  exit 1
fi
if [[ "${REQUIRE_TOUCH:-0}" == 1 && "$touch_verified" != 1 ]]; then
  echo "Strict stylus check failed; keyboard navigation passed independently" >&2
  exit 1
fi
