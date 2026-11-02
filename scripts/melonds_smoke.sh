#!/usr/bin/env bash
# Launch the built DS ROM in the official melonDS runtime and capture its
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
  launcher=(flatpak run --env=QT_QPA_PLATFORMTHEME=generic --env=GTK_USE_PORTAL=0 --env=GSETTINGS_BACKEND=memory --env=DCONF_PROFILE=/dev/null --env=QT_QPA_PLATFORM=xcb net.kuribo64.melonDS)
fi
"${launcher[@]}" "$rom" >"$out/melonds.log" 2>&1 &
pid=$!
printf 'Emulator launcher PID: %s\n' "$pid" >>"$out/runtime.log"
cleanup(){
  # SIGTERM allows melonDS to flush FAT/DLDI saves. AppImage runtimes can
  # ignore it; waiting indefinitely previously exhausted the 30-minute job.
  trap - EXIT
  local state attempt
  # Ask Qt to close its window first. SIGTERM alone required SIGKILL in a
  # real AppImage run, which cannot establish that FAT/DLDI writes flushed.
  if [[ -n "${window:-}" ]]; then
    # Qt's File > Quit action (Ctrl+Q) allows the emulator to sync its
    # folder-backed DLDI filesystem before exit. X11 windowclose alone
    # did not stop the AppImage in actual CI and led to forced SIGKILL.
    xdotool windowfocus "$window" 2>/dev/null || true
    xdotool key --clearmodifiers ctrl+q 2>/dev/null || true
    printf 'Emulator GUI Quit shortcut requested for XID %s\n' "$window" >>"$out/runtime.log"
    for attempt in {1..25}; do
      state="$(ps -o stat= -p "$pid" 2>/dev/null || true)"
      [[ -z "$state" || "$state" == Z* ]] && break
      sleep 0.1
    done
    state="$(ps -o stat= -p "$pid" 2>/dev/null || true)"
    if [[ -n "$state" && "$state" != Z* ]]; then
      xdotool windowclose "$window" 2>/dev/null || true
      printf 'Emulator GUI close requested for XID %s\n' "$window" >>"$out/runtime.log"
      for attempt in {1..25}; do
        state="$(ps -o stat= -p "$pid" 2>/dev/null || true)"
        [[ -z "$state" || "$state" == Z* ]] && break
        sleep 0.1
      done
    fi
  fi
  state="$(ps -o stat= -p "$pid" 2>/dev/null || true)"
  if [[ -n "$state" && "$state" != Z* ]]; then
    kill -TERM "$pid" 2>/dev/null || true
    for attempt in {1..40}; do
      state="$(ps -o stat= -p "$pid" 2>/dev/null || true)"
      [[ -z "$state" || "$state" == Z* ]] && break
      sleep 0.1
    done
  fi
  state="$(ps -o stat= -p "$pid" 2>/dev/null || true)"
  if [[ -n "$state" && "$state" != Z* ]]; then
    kill -KILL "$pid" 2>/dev/null || true
    printf 'WARNING: Emulator launcher PID %s force-killed after SIGTERM timeout; save flush unverified\n' "$pid" >>"$out/runtime.log"
  fi
  wait "$pid" 2>/dev/null || true
  if kill -0 "$pid" 2>/dev/null; then
    printf 'Emulator launcher PID %s still running after cleanup\n' "$pid" >>"$out/runtime.log"
  else
    printf 'Emulator launcher PID %s terminated\n' "$pid" >>"$out/runtime.log"
  fi
}
trap cleanup EXIT
window=""
for attempt in $(seq 1 60); do
  window=""
  while IFS= read -r candidate; do
    [[ -n "$candidate" ]] || continue
    geometry="$(xwininfo -id "$candidate" 2>/dev/null || true)"
    width="$(sed -n 's/^  Width: \([0-9][0-9]*\)$/\1/p' <<<"$geometry" | head -n1)"
    height="$(sed -n 's/^  Height: \([0-9][0-9]*\)$/\1/p' <<<"$geometry" | head -n1)"
    if [[ "${width:-0}" -ge 256 && "${height:-0}" -ge 400 ]]; then
      window="$candidate"
      break
    fi
  done < <(xdotool search --onlyvisible --name 'melonDS' 2>/dev/null || true)
  [[ -n "$window" ]] && break
  # Flatpak may return before its sandboxed GUI process has registered a window.
  # Keep the full bounded window-discovery timeout instead of treating the
  # short-lived launcher PID as proof that melonDS itself has exited.
  if ! kill -0 "$pid" 2>/dev/null && [[ "$attempt" == 1 ]]; then
    echo "Launcher PID exited; waiting for sandboxed melonDS window" >>"$out/runtime.log"
  fi
  sleep 1
done
if [[ -z "$window" ]]; then
  xwininfo -root -tree >"$out/window-tree.txt" 2>&1 || true
  # A native build can crash before opening X11. Preserve a bounded stack
  # trace so a failing CI run identifies the fault instead of guessing.
  if [[ -n "${MELONDS_BIN:-}" ]] && command -v gdb >/dev/null; then
    timeout 25s gdb -batch -ex 'set pagination off' -ex run \
      -ex 'thread apply all bt 8' --args "$MELONDS_BIN" "$rom" \
      >"$out/native-backtrace.txt" 2>&1 || true
    tail -n 100 "$out/native-backtrace.txt" >&2
  fi
  cat "$out/melonds.log" >&2
  echo "melonDS window did not appear; no screenshot claimed" >&2
  exit 1
fi
echo "Window XID: $window" >>"$out/runtime.log"
xwininfo -id "$window" >>"$out/runtime.log" 2>&1 || true
snapshot() {
  local name="$1"
  xwininfo -id "$window" >/dev/null 2>&1 || { echo "melonDS display closed before $name" >&2; exit 1; }
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
# This is a boot screenshot, not necessarily a title screenshot: the game
# restores its last saved scene and can reopen the Development Lab shop.
snapshot 01-title
if [[ "${REQUIRE_PREEXISTING_ORB:-0}" == 1 ]]; then
  # A previous search can save the shop as the resume scene. On a genuinely
  # fresh second emulator launch, inspect its pixels BEFORE sending stylus
  # or Start: those inputs would otherwise act on the resumed shop instead
  # of the title screen and falsely fail restart acceptance.
  if python3 tools/verify_melonds_navigation.py "$out" \
      --observe-shop-orbs-screenshot "$out/01-title.png" \
      >"$out/orb-balance-before.json" 2>"$out/restart-boot-shop.err"; then
    cp "$out/01-title.png" "$out/03-shop-orbs-before.png"
    if [[ -z "${EXPECTED_RESTORED_ORBS:-}" ]]; then
      echo "Clean-restart acceptance failed: missing first-session Orb balance" >&2
      exit 1
    fi
    python3 tools/check_restored_orbs.py "$out/orb-balance-before.json" \
      --expected-balance "$EXPECTED_RESTORED_ORBS"
    echo "PASS: fresh emulator resumed into saved Development Lab shop; exact Orb balance restored" | tee -a "$out/runtime.log"
    # The EXIT trap records launcher termination for the provenance verifier.
    exit 0
  fi
  rm -f "$out/orb-balance-before.json"
  echo "INFO: restart boot is not the saved shop; testing title navigation" | tee -a "$out/runtime.log"
fi
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
  # Keep both the original tap frame and a second frame after a longer
  # settling period to distinguish a delayed transition from a missed tap.
  sleep 2
  snapshot 02-title-touch-delayed
  # A slow transition can complete after the first screenshot. Accept only
  # independently verified intro pixels; do not mask a successful stylus tap
  # by sending a second Start input that could advance the scene again.
  if cp "$out/02-title-touch-delayed.png" "$out/02-intro.png" &&
     python3 tools/verify_melonds_navigation.py "$out" --stage 02-intro >>"$out/runtime.log" 2>&1; then
    touch_verified=1
    echo "PASS: delayed title stylus input entered the intro" | tee -a "$out/runtime.log"
  else
    rm -f "$out/02-intro.png"
    press_ds_key Return
    snapshot 02-intro
    python3 tools/verify_melonds_navigation.py "$out" --stage 02-intro
  fi
fi
# Explicit workflow mappings: DS B=X, DS A=Z. Each action is checked against
# the real screen heading so animation alone cannot satisfy the smoke test.
press_ds_key x
snapshot 03-lab
# Sample the saved Dream Orb balance BEFORE search. This is a different
# counter from live Orb entities, which also disappear on timeout.
press_ds_key Down 0.2
press_ds_key z 0.3
snapshot 03-shop-orbs-before
if ! python3 tools/verify_melonds_navigation.py "$out" \
    --observe-shop-orbs-screenshot "$out/03-shop-orbs-before.png" \
    >"$out/orb-balance-before.json"; then
  rm -f "$out/orb-balance-before.json"
  echo "WARNING: could not read pre-search saved Orb balance" | tee -a "$out/runtime.log"
fi
# On the second, independently launched emulator process, refuse to proceed
# unless the first process' saved Orb gain was actually restored. Merely
# setting REQUIRE_PREEXISTING_ORB in the workflow is not an assertion.
if [[ "${REQUIRE_PREEXISTING_ORB:-0}" == 1 ]]; then
  if [[ ! -s "$out/orb-balance-before.json" ]]; then
    echo "Clean-restart acceptance failed: no readable pre-search Orb balance" >&2
    exit 1
  fi
  if [[ -z "${EXPECTED_RESTORED_ORBS:-}" ]]; then
    echo "Clean-restart acceptance failed: missing independently observed first-session balance" >&2
    exit 1
  fi
  python3 tools/check_restored_orbs.py "$out/orb-balance-before.json" \
    --expected-balance "$EXPECTED_RESTORED_ORBS"
  # The second process exists only to verify restored save state. Do not
  # start a second randomized search or risk obscuring the acceptance result.
  # The EXIT trap records emulator termination for provenance verification.
  echo "PASS: independently decoded restored Orb balance; ending restart session" | tee -a "$out/runtime.log"
  exit 0
fi
press_ds_key x 0.3
# Returning to the lab resets selection to START SEARCH.
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
# Move both independent DS fallback camera axes together during sphere
# pursuit. Sequential key pulses add latency while the target keeps moving.
# This helper never presses A; the fresh post-movement screenshot remains
# the only authority for a subsequent bounded shot.
aim_ds_pair() {
  local hkey="$1" hsec="$2" vkey="$3" vsec="$4" settle="${5:-0.06}"
  [[ "$hkey" =~ ^(Left|Right|none)$ && "$vkey" =~ ^(Up|Down|none)$ ]] || return 2
  [[ "$hsec" =~ ^(0|0\.[0-9]{1,3})$ && "$vsec" =~ ^(0|0\.[0-9]{1,3})$ ]] || return 2
  if [[ "$hkey" == none || "$hsec" =~ ^0(\.0+)?$ ]]; then
    aim_ds_key "$vkey" "$vsec" "$settle"
    return
  fi
  if [[ "$vkey" == none || "$vsec" =~ ^0(\.0+)?$ ]]; then
    aim_ds_key "$hkey" "$hsec" "$settle"
    return
  fi
  local first second first_seconds remaining
  read -r first second first_seconds remaining < <(
    awk -v h="$hsec" -v v="$vsec" 'BEGIN {
      if (h <= v) printf "horizontal vertical %.3f %.3f\n", h, v-h;
      else printf "vertical horizontal %.3f %.3f\n", v, h-v;
    }'
  )
  local first_key="$hkey" second_key="$vkey"
  if [[ "$first" == vertical ]]; then
    first_key="$vkey"
    second_key="$hkey"
  fi
  xdotool windowfocus "$window"
  xdotool keydown --clearmodifiers "$hkey" "$vkey"
  sleep "$first_seconds"
  xdotool keyup "$first_key"
  sleep "$remaining"
  xdotool keyup "$second_key"
  sleep "$settle"
}
# Capture a paired before/after record for each Orb-aim input pulse. These
# measurements expose whether a key moves the reticle, camera, or target;
# they do not authorize firing. The normal observed-alignment gate remains
# the sole authority for an A-button shot.
orb_aim_pulse() {
  local label="$1" key="$2" seconds="$3" settle="${4:-0.06}"
  [[ "$key" == none || "$seconds" == 0 ]] && return 0
  snapshot "orb-calibration-$label-before"
  python3 tools/plan_melonds_aim.py "$out/orb-calibration-$label-before.png" --target orb \
    >"$out/orb-calibration-$label-before.json" 2>"$out/orb-calibration-$label-before.err" || true
  printf 'pulse=%s key=%s hold_seconds=%s\\n' "$label" "$key" "$seconds" | tee -a "$out/orb-calibration.csv"
  aim_ds_key "$key" "$seconds" "$settle"
  snapshot "orb-calibration-$label-after"
  python3 tools/plan_melonds_aim.py "$out/orb-calibration-$label-after.png" --target orb \
    >"$out/orb-calibration-$label-after.json" 2>"$out/orb-calibration-$label-after.err" || true
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
  orb_aim_pulse initial-horizontal "$horizontal" "$horizontal_seconds" 0.06
  orb_aim_pulse initial-vertical "$vertical" "$vertical_seconds" 0.06
  snapshot 05-radar-orb-aimed
  # Observe the moving Orb twice WITHOUT moving the D-pad between samples.
  # Reticle movement would contaminate the apparent Orb velocity.
  for correction in 1 2 3; do
    previous_orb_frame="$out/05-radar-orb-aimed.png"
    sleep 0.06
    snapshot "05-radar-orb-motion-$correction"
    if ! python3 tools/plan_melonds_aim.py "$out/05-radar-orb-motion-$correction.png" --target orb \
        --previous-screenshot "$previous_orb_frame" >"$out/orb-aim-correction-$correction.json"; then
      break
    fi
    read -r horizontal horizontal_seconds vertical vertical_seconds < <(
      python3 -c 'import json,sys; p=json.load(open(sys.argv[1])); x=p["offset"]["x"]; y=p["offset"]["y"]; done=abs(x)<=4 and abs(y)<=4; print("none" if done else p["horizontal_key"], 0 if done else round(min(0.4,p["horizontal_seconds"]*1.5),3), "none" if done else p["vertical_key"], 0 if done else round(min(0.4,p["vertical_seconds"]*1.5),3))' "$out/orb-aim-correction-$correction.json"
    )
    [[ "$horizontal" == none && "$vertical" == none ]] && break
    orb_aim_pulse "correction-$correction-horizontal" "$horizontal" "$horizontal_seconds" 0.06
    orb_aim_pulse "correction-$correction-vertical" "$vertical" "$vertical_seconds" 0.06
    snapshot 05-radar-orb-aimed
  done
  # A moving Orb can leave the reticle during correction. Do not fire at a
  # cloud just because an Orb was visible in an earlier screenshot.
  # Actual live evidence has shown a moving Orb 25px from the reticle
  # after three correction passes. Give it a short stationary opportunity
  # to cross the reticle rather than firing blindly or trusting stale aim.
  # Every attempted shot still requires an independently observed, fresh
  # within_safe_fire_radius result; the bounded window does not prove a hit.
  orb_fire_ready=0
  for sample in 0 1 2 3 4; do
    if (( sample > 0 )); then
      sleep 0.05
    fi
    snapshot "05-radar-orb-prefire-$sample"
    latest_radar="$out/05-radar-orb-prefire-$sample.png"
    if python3 tools/plan_melonds_aim.py "$latest_radar" --target orb \
        >"$out/orb-fire-check-$sample.json" 2>"$out/orb-fire-error-$sample.txt" &&
       python3 -c 'import json,sys; sys.exit(not json.load(open(sys.argv[1]))["within_safe_fire_radius"])' \
        "$out/orb-fire-check-$sample.json"; then
      cp "$out/orb-fire-check-$sample.json" "$out/orb-fire-check.json"
      orb_fire_ready=1
      echo "INFO: observed moving Orb aligned on prefire sample $sample" | tee -a "$out/runtime.log"
      break
    fi
  done
  if [[ "$orb_fire_ready" == 1 ]]; then
    press_ds_key z 0.12
    snapshot 05-radar-orb-postfire
    latest_radar="$out/05-radar-orb-postfire.png"
  else
    echo "WARNING: moving Orb not aligned in five fresh frames; skipped unsafe shot" | tee -a "$out/runtime.log"
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
    # A remaining cloud can be outside the current camera viewport without
    # exposing a detectable gold edge cue. Reacquire by bounded D-pad camera
    # movement only; NEVER shoot unless a fresh cloud frame is subsequently
    # recognized and independently passes the existing safe-fire gate.
    echo "INFO: cloud not visible on retry $attempt; bounded camera reacquisition" | tee -a "$out/runtime.log"
    reacquired=0
    scan_step=0
    for scan_direction in Right Down Left Up; do
      scan_step=$((scan_step + 1))
      aim_ds_key "$scan_direction" 0.32 0.04
      snapshot "05-radar-retry-$attempt-scan-$scan_step"
      latest_radar="$out/05-radar-retry-$attempt-scan-$scan_step.png"
      if ! python3 tools/verify_melonds_navigation.py "$out" \
          --observe-search-screenshot "$latest_radar" \
          >"$out/search-retry-$attempt-scan-$scan_step.json"; then
        if python3 tools/verify_melonds_navigation.py "$out" \
            --observe-results-screenshot "$latest_radar" >/dev/null 2>&1; then
          cp "$latest_radar" "$out/06-results.png"
          echo "INFO: Results appeared during camera reacquisition" | tee -a "$out/runtime.log"
        fi
        break
      fi
      read -r scan_state scan_clouds < <(
        python3 -c 'import json,sys; s=json.load(open(sys.argv[1])); print(s["state"], s.get("radar_counters",{}).get("clouds",0))' \
          "$out/search-retry-$attempt-scan-$scan_step.json"
      )
      if [[ "$scan_state" == sphere ]]; then
        cp "$latest_radar" "$out/05-sphere-encounter.png"
        echo "PASS: delayed sphere encounter recognized during camera reacquisition" | tee -a "$out/runtime.log"
        break
      fi
      [[ "$scan_state" == radar && "$scan_clouds" -gt 0 ]] || break
      if python3 tools/plan_melonds_aim.py "$latest_radar" \
          >"$out/aim-retry-$attempt.json" 2>"$out/aim-retry-$attempt-scan-error.txt"; then
        reacquired=1
        echo "INFO: cloud or edge marker reacquired on scan $scan_step" | tee -a "$out/runtime.log"
        break
      fi
    done
    [[ -f "$out/05-sphere-encounter.png" ]] && break
    if [[ "$reacquired" != 1 ]]; then
      echo "WARNING: no recognizable cloud after bounded camera scan; no blind shot" | tee -a "$out/runtime.log"
      break
    fi
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
  # A stale encounter screenshot never authorizes firing. Keep A released
  # until a fresh capture frame identifies the actual sphere target.
  xdotool keyup z
  capture_last="$out/05-sphere-encounter.png"
  # Capture needs up to 240 HP, not merely one successful beam hit. Stop
  # immediately on a verified reward; otherwise cap this live pursuit at
  # 220 screenshot-backed attempts (override downward for quick smoke runs).
  # The prior 160-step live ITEM encounter reached 170/177 meter pixels
  # without a reward; extend the bounded attempt rather than claim capture.
  guided_sphere_steps=0
  reacquire_attempts=0
  reacquire_successes=0
  edge_recovery_attempts=0
  edge_recovery_successes=0
  sphere_fire_authorized=0
  sphere_fire_skipped=0
  sphere_diagonal_pulses=0
  sphere_single_axis_pulses=0
  last_sphere_plan=""
  capture_steps="${CAPTURE_SWEEP_STEPS:-220}"
  if ! [[ "$capture_steps" =~ ^[0-9]+$ ]] || (( capture_steps < 1 || capture_steps > 220 )); then
    echo "CAPTURE_SWEEP_STEPS must be an integer from 1 to 220" >&2
    exit 2
  fi
  for step in $(seq 1 "$capture_steps"); do
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
    # Never fire while taking an unverified frame or reading Results.
    xdotool keyup z
    snapshot "05-sphere-before-$step"
    current_sphere="$out/05-sphere-before-$step.png"
    # A reward can appear between the previous screenshot and this fresh
    # pre-aim frame. Check it BEFORE moving or firing again; otherwise the
    # sweep may dismiss Results and lose genuine capture evidence.
    if python3 tools/verify_melonds_navigation.py "$out" \
        --observe-reward-screenshot "$current_sphere" \
        >"$out/sphere-reward-attempt.json" 2>/dev/null; then
      mv "$out/sphere-reward-attempt.json" "$out/sphere-reward.json"
      cp "$current_sphere" "$out/05-capture-reward.png"
      capture_last="$current_sphere"
      echo "PASS: real emulator capture reward observed before sweep movement $step" | tee -a "$out/runtime.log"
      break
    fi
    rm -f "$out/sphere-reward-attempt.json"
    if python3 tools/verify_melonds_navigation.py "$out" \
        --observe-results-screenshot "$current_sphere" >/dev/null 2>&1; then
      capture_last="$current_sphere"
      echo "INFO: encounter ended before sweep movement $step without verified reward" | tee -a "$out/runtime.log"
      break
    fi
    # Preserve the current live frame as diagnostic evidence when the
    # target classifier fails; never interpret an unrecognized frame as a
    # successful capture. Capture pursuit must remain bounded.
    if ! python3 tools/verify_melonds_navigation.py "$out" \
        --observe-capture-progress "$current_sphere" \
        >"$out/sphere-before-progress-$step.json" 2>/dev/null; then
      echo "WARNING: pre-aim sphere frame $step is not recognized as capture progress" | tee -a "$out/runtime.log"
      break
    fi
    # Unknown artwork/backgrounds fail closed to the bounded manual sweep.
    # A single ambiguous frame is not proof that the encounter is lost.
    # Release the shoot key, take ONE fresh stationary sample and recheck
    # Results before aiming again. Never fall back to blind directional fire.
    if ! python3 tools/plan_melonds_aim.py "$current_sphere" --target sphere \
        --previous-screenshot "$previous_sphere" \
        >"$out/sphere-aim-$step.json" 2>"$out/sphere-aim-error-$step.txt"; then
      reacquire_attempts=$((reacquire_attempts + 1))
      # Keep the beam OFF while the target is obscured. The sphere may cross
      # the HUD or overlap a projectile for several consecutive frames.
      # Three bounded, stationary screenshots are safer than blind firing or
      # abandoning the entire encounter after one ambiguous sample.
      xdotool keyup z
      reacquire_state=ambiguous
      for reacquire_sample in 1 2 3; do
        sleep 0.12
        snapshot "05-sphere-reacquire-$step-$reacquire_sample"
        reacquired="$out/05-sphere-reacquire-$step-$reacquire_sample.png"
        if python3 tools/verify_melonds_navigation.py "$out" \
            --observe-reward-screenshot "$reacquired" \
            >"$out/sphere-reward-attempt.json" 2>/dev/null; then
          mv "$out/sphere-reward-attempt.json" "$out/sphere-reward.json"
          cp "$reacquired" "$out/05-capture-reward.png"
          capture_last="$reacquired"
          reacquire_state=ended
          echo "PASS: capture reward observed during sphere reacquisition $step/$reacquire_sample" | tee -a "$out/runtime.log"
          break
        fi
        rm -f "$out/sphere-reward-attempt.json"
        if ! python3 tools/verify_melonds_navigation.py "$out" \
            --observe-capture-progress "$reacquired" \
            >"$out/sphere-reacquire-progress-$step-$reacquire_sample.json" 2>/dev/null; then
          echo "WARNING: reacquisition frame $step/$reacquire_sample is not a live sphere encounter" | tee -a "$out/runtime.log"
          reacquire_state=ended
          break
        fi
        if python3 tools/plan_melonds_aim.py "$reacquired" --target sphere \
            --previous-screenshot "$previous_sphere" \
            >"$out/sphere-aim-$step.json" \
            2>"$out/sphere-reacquire-error-$step-$reacquire_sample.txt"; then
          reacquire_state=found
          echo "INFO: recovered sphere target on stationary sample $reacquire_sample at step $step" | tee -a "$out/runtime.log"
          break
        fi
      done
      if [[ "$reacquire_state" == ended ]]; then
        break
      fi
      if [[ "$reacquire_state" != found && -n "$last_sphere_plan" ]] &&
         python3 tools/plan_sphere_recovery.py "$last_sphere_plan" \
           >"$out/sphere-edge-plan-$step.json" 2>"$out/sphere-edge-error-$step.txt"; then
        # One camera nudge is allowed only when the LAST directly observed
        # sphere was at a viewport boundary. Beam remains released. Camera
        # movement invalidates two-frame motion extrapolation, so reacquire
        # with a fresh single-frame unique-target check before rearming.
        edge_recovery_attempts=$((edge_recovery_attempts + 1))
        read -r recovery_key recovery_seconds < <(
          python3 -c 'import json,sys; p=json.load(open(sys.argv[1])); assert p["fire_authorized"] is False; print(p["key"],p["seconds"])' \
            "$out/sphere-edge-plan-$step.json"
        )
        aim_ds_key "$recovery_key" "$recovery_seconds" 0.08
        snapshot "05-sphere-edge-recovery-$step"
        edge_frame="$out/05-sphere-edge-recovery-$step.png"
        if python3 tools/verify_melonds_navigation.py "$out" \
            --observe-reward-screenshot "$edge_frame" \
            >"$out/sphere-reward-attempt.json" 2>/dev/null; then
          mv "$out/sphere-reward-attempt.json" "$out/sphere-reward.json"
          cp "$edge_frame" "$out/05-capture-reward.png"
          capture_last="$edge_frame"
          reacquire_state=ended
          echo "PASS: capture reward appeared during safe edge recovery" | tee -a "$out/runtime.log"
        else
          rm -f "$out/sphere-reward-attempt.json"
          if python3 tools/verify_melonds_navigation.py "$out" \
              --observe-capture-progress "$edge_frame" \
              >"$out/sphere-edge-progress-$step.json" 2>/dev/null &&
             python3 tools/plan_melonds_aim.py "$edge_frame" --target sphere \
              >"$out/sphere-aim-$step.json" 2>"$out/sphere-edge-aim-error-$step.txt"; then
            reacquire_state=found
            edge_recovery_successes=$((edge_recovery_successes + 1))
            echo "INFO: unique sphere reacquired after no-fire boundary nudge at step $step" | tee -a "$out/runtime.log"
          fi
        fi
      fi
      if [[ "$reacquire_state" == ended ]]; then
        break
      fi
      if [[ "$reacquire_state" != found ]]; then
        echo "WARNING: sphere target still ambiguous after stationary and bounded edge recovery at step $step" | tee -a "$out/runtime.log"
        break
      fi
      reacquire_successes=$((reacquire_successes + 1))
    fi
    guided_sphere_steps=$((guided_sphere_steps + 1))
    last_sphere_plan="$out/sphere-aim-$step.json"
    read -r horizontal horizontal_seconds vertical vertical_seconds < <(
      python3 -c 'import json,sys; p=json.load(open(sys.argv[1])); print(p["horizontal_key"],p["horizontal_seconds"],p["vertical_key"],p["vertical_seconds"])' \
        "$out/sphere-aim-$step.json"
    )
    # Camera motion invalidates the old target coordinates. Move with A
    # RELEASED, then independently observe the sphere near the reticle.
    # Never fire merely because an earlier moving-target prediction existed.
    aim_ds_pair "$horizontal" "$horizontal_seconds" "$vertical" "$vertical_seconds" 0.06
    if [[ "$horizontal" != none && "$vertical" != none &&
          "$horizontal_seconds" != 0 && "$vertical_seconds" != 0 ]]; then
      sphere_diagonal_pulses=$((sphere_diagonal_pulses + 1))
    else
      sphere_single_axis_pulses=$((sphere_single_axis_pulses + 1))
    fi
    snapshot "05-sphere-prefire-$step"
    prefire_frame="$out/05-sphere-prefire-$step.png"
    # One fresh PNG decode now checks reward, capture scene, unique target
    # and observed-only 13px gate. Separate ImageMagick/JSON subprocesses
    # previously let fast spheres drift between observation and A-button.
    prefire_code=0
    python3 tools/verify_sphere_prefire_frame.py "$prefire_frame" --fire-aligned \
      --reward "$out/sphere-reward-attempt.json" \
      --progress "$out/sphere-prefire-progress-$step.json" \
      --aim "$out/sphere-prefire-aim-$step.json" \
      --gate "$out/sphere-prefire-gate-$step.json" \
      >"$out/sphere-prefire-inspection-$step.json" \
      2>"$out/sphere-prefire-error-$step.txt" || prefire_code=$?
    case "$prefire_code" in
      20)
        mv "$out/sphere-reward-attempt.json" "$out/sphere-reward.json"
        cp "$prefire_frame" "$out/05-capture-reward.png"
        capture_last="$prefire_frame"
        echo "PASS: capture reward observed before prefire $step" | tee -a "$out/runtime.log"
        break ;;
      12)
        echo "WARNING: prefire frame $step is no longer a recognized sphere encounter" | tee -a "$out/runtime.log"
        break ;;
      11)
        sphere_fire_skipped=$((sphere_fire_skipped + 1))
        capture_last="$prefire_frame"
        echo "INFO: prefire $step has no unique fresh target; no shot" >>"$out/runtime.log"
        continue ;;
      10) ;; # Unaligned; one no-fire correction is allowed.
      0) ;;  # Directly observed and aligned.
      *) echo "ERROR: prefire inspection failed ($prefire_code)" >&2; exit 1 ;;
    esac
    if [[ "$prefire_code" == 10 ]]; then
      # The first observation is not aligned. A stays released; correct
      # once and require an independent SECOND screenshot before any shot.
      read -r fix_h fix_h_seconds fix_v fix_v_seconds < <(
        python3 -c 'import json,sys; p=json.load(open(sys.argv[1])); print(p["horizontal_key"],round(min(0.12,p["horizontal_seconds"]),3),p["vertical_key"],round(min(0.12,p["vertical_seconds"]),3))' \
          "$out/sphere-prefire-aim-$step.json"
      )
      aim_ds_pair "$fix_h" "$fix_h_seconds" "$fix_v" "$fix_v_seconds" 0.04
      if [[ "$fix_h" != none && "$fix_v" != none &&
            "$fix_h_seconds" != 0 && "$fix_v_seconds" != 0 ]]; then
        sphere_diagonal_pulses=$((sphere_diagonal_pulses + 1))
      else
        sphere_single_axis_pulses=$((sphere_single_axis_pulses + 1))
      fi
      snapshot "05-sphere-prefire-corrected-$step"
      prefire_frame="$out/05-sphere-prefire-corrected-$step.png"
      corrected_code=0
      python3 tools/verify_sphere_prefire_frame.py "$prefire_frame" --fire-aligned \
        --reward "$out/sphere-reward-attempt.json" \
        --progress "$out/sphere-prefire-corrected-progress-$step.json" \
        --aim "$out/sphere-prefire-aim-$step.json" \
        --gate "$out/sphere-prefire-gate-$step.json" \
        >"$out/sphere-prefire-corrected-inspection-$step.json" \
        2>"$out/sphere-prefire-error-$step.txt" || corrected_code=$?
      case "$corrected_code" in
        20)
          mv "$out/sphere-reward-attempt.json" "$out/sphere-reward.json"
          cp "$prefire_frame" "$out/05-capture-reward.png"
          capture_last="$prefire_frame"
          echo "PASS: capture reward observed during no-fire correction $step" | tee -a "$out/runtime.log"
          break ;;
        12)
          echo "WARNING: corrected prefire frame $step is no longer a sphere encounter" | tee -a "$out/runtime.log"
          break ;;
        11|10)
          sphere_fire_skipped=$((sphere_fire_skipped + 1))
          capture_last="$prefire_frame"
          echo "INFO: corrected prefire $step remained ambiguous or unaligned; no shot" >>"$out/runtime.log"
          continue ;;
        0) ;;
        *) echo "ERROR: corrected prefire inspection failed ($corrected_code)" >&2; exit 1 ;;
      esac
    fi
    # The aligned inspector has ALREADY pulsed and released A immediately
    # after its fresh screenshot gate; no second shell-side shot is allowed.
    # A pulse is not proof of a hit, capture or reward.
    sphere_fire_authorized=$((sphere_fire_authorized + 1))
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
  echo "INFO: guided sphere aim used $guided_sphere_steps of $capture_steps allowed attempts" | tee -a "$out/runtime.log"
  echo "INFO: fresh aligned prefire shots $sphere_fire_authorized; unaligned/ambiguous skipped $sphere_fire_skipped" | tee -a "$out/runtime.log"
  echo "INFO: sphere camera pulses diagonal=$sphere_diagonal_pulses single_axis_or_none=$sphere_single_axis_pulses (not proof of hits)" | tee -a "$out/runtime.log"
  echo "INFO: sphere reacquisition succeeded $reacquire_successes of $reacquire_attempts attempts" | tee -a "$out/runtime.log"
  echo "INFO: no-fire edge camera recovery succeeded $edge_recovery_successes of $edge_recovery_attempts attempts" | tee -a "$out/runtime.log"
fi
# Persist an explicit meter ceiling and reward-evidence boundary for CI.
# An encounter and a partially filled bar are NOT a completed capture.
python3 tools/summarize_capture_attempt.py "$out" \
  --output "$out/sphere-attempt-report.json" | tee -a "$out/runtime.log"
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
# Reject missing, duplicated, or out-of-order live navigation evidence.
python3 tools/validate_navigation_evidence.py "$out/navigation-report.json" --screenshots "$out"
# Read the persistent Orb balance after the search. A decreased active-Orb
# counter cannot prove collection because live Orbs expire after 210 frames.
# A positive shop balance delta can; neither proves restart persistence.
if [[ -s "$out/orb-balance-before.json" ]]; then
  press_ds_key Down 0.2
  press_ds_key z 0.3
  snapshot 08-shop-orbs-after
  if python3 tools/verify_melonds_navigation.py "$out" \
      --observe-shop-orbs-screenshot "$out/08-shop-orbs-after.png" \
      >"$out/orb-balance-after.json"; then
    python3 - "$out/orb-balance-before.json" "$out/orb-balance-after.json" \
        "$out/orb-balance-change.json" <<'PY'
import json
import sys
from pathlib import Path
sys.path.insert(0, "tools")
from verify_melonds_navigation import compare_shop_orb_balances
before = json.loads(Path(sys.argv[1]).read_text())
after = json.loads(Path(sys.argv[2]).read_text())
result = compare_shop_orb_balances(before, after)
Path(sys.argv[3]).write_text(json.dumps(result, indent=2) + "\n")
print("PASS: session Orb balance increased; restart persistence unverified"
      if result["balance_increased"]
      else "INFO: no session Orb balance gain observed")
PY
  else
    rm -f "$out/orb-balance-after.json"
    echo "WARNING: could not read post-search saved Orb balance" | tee -a "$out/runtime.log"
  fi
fi
if [[ "${REQUIRE_ORB_COLLECTION:-0}" == 1 ]] &&
   ! python3 -c 'import json,sys; sys.exit(not json.load(open(sys.argv[1]))["orb_collection_observed"])' \
      "$out/orb-balance-change.json" 2>/dev/null; then
  echo "Strict Orb collection acceptance failed: no independently verified saved balance increase" >&2
  exit 1
fi
if [[ "${REQUIRE_CAPTURE:-0}" == 1 && ! -f "$out/05-capture-reward.png" ]]; then
  echo "Strict capture acceptance failed: no verified reward screenshot" >&2
  exit 1
fi
if [[ "${REQUIRE_TOUCH:-0}" == 1 && "$touch_verified" != 1 ]]; then
  echo "Strict stylus check failed; keyboard navigation passed independently" >&2
  exit 1
fi
