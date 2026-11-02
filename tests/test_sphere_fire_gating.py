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

# There must be exactly two screenshot-conditioned firing sites, one before
# and one after the optional no-fire camera correction. Never fire from the
# predicted/old aim plan or from a stationary/edge reacquisition.
call = 'python3 tools/verify_sphere_prefire_frame.py "$prefire_frame" --fire-aligned'
assert loop.count(call) == 2, "Only fresh inspector calls may pulse A"
assert 'xdotool keydown --clearmodifiers z' not in loop
first, second = [i for i in range(len(loop)) if loop.startswith(call, i)]
assert loop.index('snapshot "05-sphere-prefire-$step"') < first
assert first < loop.index('case "$prefire_code" in')
assert loop.index('snapshot "05-sphere-prefire-corrected-$step"') < second
assert second < loop.index('case "$corrected_code" in')
assert loop.index('aim_ds_pair "$horizontal"') < first
assert loop.index('aim_ds_pair "$fix_h"') < second
assert loop.index('sphere_fire_authorized=$((sphere_fire_authorized + 1))') > second
assert loop.index('snapshot "05-sphere-sweep-$step"') > second

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

# The inspector pulses only after classification and evidence publication;
# it guarantees keyup in finally, including failed keydown/sleep paths.
assert 'if status != "aligned":' in inspector
assert 'fired = pulse_if_aligned(status) if args.fire_aligned else False' in inspector
assert inspector.index('status = write_evidence(paths, result)') < inspector.index(
    'fired = pulse_if_aligned(status)')
assert 'finally:\n        subprocess.run(["xdotool", "keyup", "z"]' in inspector
assert 'paths["gate"].unlink(missing_ok=True)' in inspector

subprocess.run(["bash", "-n", str(ROOT / "scripts/melonds_smoke.sh")], check=True)
print("PASS: fresh-frame inspector pulses once, releases A and fails closed")
