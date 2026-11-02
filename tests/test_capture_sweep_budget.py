#!/usr/bin/env python3
"""Keep the CI sphere-pursuit budget and runtime safety cap synchronized."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
script = (ROOT / "scripts/melonds_smoke.sh").read_text()
workflow = (ROOT / ".github/workflows/melonds-smoke.yml").read_text()

assert 'capture_steps="${CAPTURE_SWEEP_STEPS:-440}"' in script
assert '(( capture_steps < 1 || capture_steps > 440 ))' in script
assert 'CAPTURE_SWEEP_STEPS must be an integer from 1 to 440' in script
assert "options: ['40', '80', '160', '220', '440']" in workflow
assert "default: '440'" in workflow
assert "inputs.capture_sweep_steps || '440'" in workflow
assert re.search(r"timeout-minutes:\s*30", workflow)
assert 'if [[ "${REQUIRE_CAPTURE:-0}" == 1 && ! -f "$out/05-capture-reward.png" ]]' in script
assert 'tools/summarize_capture_attempt.py "$out"' in script
assert 'if (( step == 220 && capture_steps > 220 ))' not in script
assert 'if (( step == 221 )); then' in script
# No-fire `continue` branches must never skip the 220-step extension gate.
# Enforce the gate at the very start of step 221, before screenshot/movement.
loop_start = script.index('  for step in $(seq 1 "$capture_steps"); do')
loop_end = script.index('  xdotool keyup z\n  echo "INFO: guided sphere aim used', loop_start)
loop = script[loop_start:loop_end]
checkpoint = loop.index('    if (( step == 221 )); then')
assert loop.count('if (( step == 221 )); then') == 1
assert checkpoint < loop.index('    sweep=$(( (step - 1) % 12 + 1 ))')
assert checkpoint < loop.index('    snapshot "05-sphere-before-$step"')
assert checkpoint < loop.index('        continue ;;')
assert checkpoint < loop.index('          continue ;;')
assert '    if (( step == 220 && capture_steps > 220 )); then' not in loop
assert 'tools/check_capture_extension.py "$out/sphere-midpoint-report.json"' in script
assert 'tools/summarize_capture_attempt.py "$out"' in script
assert '3) echo "INFO: no sufficient meter progress' in script
assert '*) echo "ERROR: invalid capture extension evidence' in script
assert "      - 'tools/check_capture_extension.py'" in workflow
assert "      - 'tests/test_capture_extension.py'" in workflow
assert "python3 tests/test_capture_extension.py" in workflow
print("PASS: bounded 440-step pursuit enforces unskippable evidence gate before step 221")
