#!/usr/bin/env python3
"""Guard the live melonDS sphere capture loop against blind A-button firing.

This is a shell control-flow regression, NOT proof of successful gameplay.
"""
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
script = (ROOT / "scripts/melonds_smoke.sh").read_text()
start = script.index('capture_last=""\nif [[ -f "$out/05-sphere-encounter.png" ]]; then')
end = script.index("# Persist an explicit meter ceiling", start)
loop = script[start:end]

# The only fire authorization must occur after the successful screenshot
# planner path (including any bounded, no-fire reacquisition).
fire = '    xdotool keydown --clearmodifiers z\n'
assert loop.count(fire) == 1, "Capture loop has a blind or duplicate fire site"
aim = loop.index('    guided_sphere_steps=$((guided_sphere_steps + 1))')
fire_at = loop.index(fire)
assert aim < fire_at
assert loop.index('    last_sphere_plan="$out/sphere-aim-$step.json"') < fire_at
assert loop.index('    read -r horizontal horizontal_seconds vertical vertical_seconds') < fire_at

# A fresh observation and all stationary/edge recovery must be no-fire.
assert loop.index('  xdotool keyup z') < loop.index('  capture_last="$out/05-sphere-encounter.png"')
assert loop.index('    xdotool keyup z\n    snapshot "05-sphere-before-$step"') < fire_at
reacquire = loop[loop.index('      reacquire_attempts='):aim]
assert 'xdotool keydown' not in reacquire
assert 'xdotool keyup z' in reacquire
assert 'snapshot "05-sphere-edge-recovery-$step"' in reacquire

# A-button is released BEFORE the post-fire screenshot; the Results scene
# can otherwise be dismissed by repeated A presses while evidence is read.
post = loop[fire_at:]
assert post.index('    xdotool keyup z\n    capture_last="$out/05-sphere-sweep-$step.png"') < post.index('    snapshot "05-sphere-sweep-$step"')
assert post.index('    snapshot "05-sphere-sweep-$step"') < post.index('--observe-reward-screenshot "$capture_last"')
assert loop.index('  xdotool keyup z\n  echo "INFO: guided sphere aim') > fire_at

subprocess.run(["bash", "-n", str(ROOT / "scripts/melonds_smoke.sh")], check=True)
print("PASS: sphere beam gated on screenshot plan, released during recovery and Results")
