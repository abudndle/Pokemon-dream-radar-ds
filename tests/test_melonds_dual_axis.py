#!/usr/bin/env python3
"""Host regression for simultaneous no-fire sphere D-pad pulses."""
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
script = (ROOT / "scripts/melonds_smoke.sh").read_text()
start = script.index("aim_ds_pair() {")
end = script.index("\n}\n", start) + 2
function = script[start:end]


def run(*args):
    shell = """window=42
xdotool() { printf 'xdotool %s\\n' "$*"; }
sleep() { printf 'sleep %s\\n' "$1"; }
aim_ds_key() { printf 'single %s %s %s\\n' "$1" "$2" "$3"; }
""" + function + '\naim_ds_pair "$@"\n'
    result = subprocess.run(["bash", "-c", shell, "dual-axis-test", *args],
                            capture_output=True, text=True)
    return result.returncode, result.stdout.splitlines()


code, events = run("Right", "0.150", "Down", "0.050", "0.060")
assert code == 0, (code, events)
assert events == [
    "xdotool windowfocus 42",
    "xdotool keydown --clearmodifiers Right Down",
    "sleep 0.050",
    "xdotool keyup Down",
    "sleep 0.100",
    "xdotool keyup Right",
    "sleep 0.060",
], events
code, events = run("Left", "0.050", "Up", "0.150", "0.040")
assert code == 0
assert events[1] == "xdotool keydown --clearmodifiers Left Up"
assert events[3] == "xdotool keyup Left" and events[5] == "xdotool keyup Up"
code, events = run("Right", "0.100", "Down", "0.100")
assert code == 0 and events[3] == "xdotool keyup Right" and events[5] == "xdotool keyup Down"
code, events = run("none", "0", "Down", "0.100")
assert code == 0 and events == ["single Down 0.100 0.06"]
code, events = run("Right", "0.100", "none", "0")
assert code == 0 and events == ["single Right 0.100 0.06"]
code, events = run("none", "0", "none", "0")
assert code == 0 and events == ["single none 0 0.06"]
for args in (("z", "0.1", "Down", "0.1"),
             ("Left", "-1", "Up", "0.1"),
             ("Left", "0.1", "Right", "0.1"),
             ("Left", "10", "Up", "0.1"),
             ("Left", "0.1", "Up", "inf")):
    code, events = run(*args)
    assert code != 0 and not events, (args, code, events)

capture = script.split('capture_last=""\nif [[ -f "$out/05-sphere-encounter.png" ]]; then', 1)[1].split('# Persist an explicit meter ceiling', 1)[0]
assert capture.count('aim_ds_pair "$horizontal" "$horizontal_seconds" "$vertical" "$vertical_seconds" 0.06') == 1
assert 'aim_ds_pair "$fix_h"' not in capture
assert capture.count('--correct-unaligned') == 1
assert 'sphere_inline_corrections=$((sphere_inline_corrections + 1))' in capture
assert capture.index('aim_ds_pair "$horizontal"') < capture.index('snapshot_fast "05-sphere-prefire-$step"')
assert capture.index('sphere_inline_corrections=$((sphere_inline_corrections + 1))') < capture.index('snapshot_fast "05-sphere-prefire-corrected-$step"')
assert 'xdotool keydown --clearmodifiers z' not in function
assert capture.count('sphere_diagonal_pulses=$((sphere_diagonal_pulses + 1))') == 1
assert capture.count('sphere_single_axis_pulses=$((sphere_single_axis_pulses + 1))') == 1
assert 'initial sphere camera pulses diagonal=$sphere_diagonal_pulses' in capture

print("PASS: simultaneous bounded D-pad axes release independently; A stays gated by fresh screenshots")
