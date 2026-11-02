#!/usr/bin/env python3
"""Keep the CI sphere-pursuit budget and runtime safety cap synchronized."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
script = (ROOT / "scripts/melonds_smoke.sh").read_text()
workflow = (ROOT / ".github/workflows/melonds-smoke.yml").read_text()

assert 'capture_steps="${CAPTURE_SWEEP_STEPS:-220}"' in script
assert '(( capture_steps < 1 || capture_steps > 220 ))' in script
assert 'CAPTURE_SWEEP_STEPS must be an integer from 1 to 220' in script
assert "options: ['40', '80', '160', '220']" in workflow
assert "default: '220'" in workflow
assert "inputs.capture_sweep_steps || '220'" in workflow
assert re.search(r"timeout-minutes:\s*30", workflow)
assert 'if [[ "${REQUIRE_CAPTURE:-0}" == 1 && ! -f "$out/05-capture-reward.png" ]]' in script
assert 'tools/summarize_capture_attempt.py "$out"' in script
print("PASS: bounded 220-step pursuit and strict reward gate match melonDS CI")
