#!/usr/bin/env python3
"""Guard fresh-frame A pulses; source checks are not live gameplay evidence."""
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
script = (ROOT / "scripts/melonds_smoke.sh").read_text()
inspector = (ROOT / "tools/verify_sphere_prefire_frame.py").read_text()
start = script.index('capture_last=""\nif [[ -f "$out/05-sphere-encounter.png" ]]; then')
end = script.index("# Persist an explicit meter ceiling", start)
loop = script[start:end]

# There must be exactly three screenshot-conditioned firing sites: initial, corrected,
# and one optional stationary near-miss retry. Never fire from the
# predicted/old aim plan or from a stationary/edge reacquisition.
call = 'python3 tools/verify_sphere_prefire_frame.py "$prefire_frame" --fire-aligned'
assert loop.count(call) == 3, "Only fresh inspector calls may pulse A"
assert 'xdotool keydown --clearmodifiers z' not in loop
assert loop.count('python3 tools/verify_sphere_preaim_frame.py "$current_sphere"') == 1
assert loop.index('python3 tools/verify_sphere_preaim_frame.py "$current_sphere"') < loop.index('aim_ds_pair "$horizontal"')
assert 'if [[ "$preaim_code" == 11 ]]; then' in loop
assert '20)' in loop and '12)' in loop
assert '--fire-aligned' not in loop.split('python3 tools/verify_sphere_preaim_frame.py "$current_sphere"', 1)[1].split('    if [[ "$preaim_code" == 11 ]]; then', 1)[0]
# Fast prefire capture retains a real X11 screenshot and nonempty-file check.
fast = script.split('snapshot_fast() {', 1)[1].split('\n}', 1)[0]
assert 'import -silent -window "$window" "$out/$name.png"' in fast
assert 'test -s "$out/$name.png"' in fast
assert 'identify ' not in fast and 'xwininfo ' not in fast
first, second, third = [i for i in range(len(loop)) if loop.startswith(call, i)]
assert loop.index('snapshot_fast "05-sphere-prefire-$step"') < first
assert first < loop.index('case "$prefire_code" in')
assert loop.index('snapshot_fast "05-sphere-prefire-corrected-$step"') < second
assert second < loop.index('case "$corrected_code" in')
assert loop.index('snapshot_fast "05-sphere-prefire-stationary-$step"') < third
assert third < loop.index('case "$stationary_code" in')
assert loop.index('tools/check_stationary_retry.py') < third
assert 'sphere_stationary_retries=$((sphere_stationary_retries + 1))' in loop
assert loop.index('aim_ds_pair "$horizontal"') < first
assert 'aim_ds_pair "$fix_h"' not in loop
assert loop.index('--correct-unaligned') < loop.index('snapshot_fast "05-sphere-prefire-corrected-$step"')
assert loop.count('--correct-unaligned') == 1
assert 'camera_correction_executed' in loop
assert 'sphere_inline_corrections=$((sphere_inline_corrections + 1))' in loop
assert loop.index('sphere_fire_authorized=$((sphere_fire_authorized + 1))') > third
assert loop.index('snapshot "05-sphere-sweep-$step"') > third

# An aligned result is the only status that may advance to post-fire capture.
# A reward, ambiguous target, or lost encounter must not authorize another shot.
for status in ('20)', '12)', '11)', '10)', '0)'):
    assert status in loop
assert '11|10)' in loop
assert 'sphere_fire_skipped=$((sphere_fire_skipped + 1))' in loop
reacquire = loop[loop.index('      reacquire_attempts='):loop.index('    guided_sphere_steps=')]
assert 'xdotool keydown --clearmodifiers z' not in reacquire
assert 'snapshot "05-sphere-edge-recovery-$step"' in reacquire
assert '  xdotool keyup z' in loop  # defensive release on entry and exit

# The inspector pulses immediately after fresh classification, BEFORE
# slow JSON serialization. Failed pulses/writes cannot claim a shot or hit.
# A is released in finally even if keydown/sleep fails.
assert 'if status != "aligned":' in inspector
assert 'fired = pulse_if_aligned(status) if args.fire_aligned else False' in inspector
assert inspector.index('result = inspect_frame(pixels, width, height, font_rows())') < inspector.index(
    'fired = pulse_if_aligned(status)')
assert inspector.index('fired = pulse_if_aligned(status)') < inspector.index(
    '        write_evidence(paths, result)')
assert 'finally:\n        subprocess.run(["xdotool", "keyup", "z"]' in inspector
assert 'paths["gate"].unlink(missing_ok=True)' in inspector
assert inspector.index('corrected = correct_if_unaligned(status, result[3])') < inspector.index('        write_evidence(paths, result)')
assert 'if status != "unaligned":' in inspector
assert 'gate = evaluate(aim)' in inspector

subprocess.run(["bash", "-n", str(ROOT / "scripts/melonds_smoke.sh")], check=True)
print("PASS: fresh-frame inspector pulses once, releases A and fails closed")
