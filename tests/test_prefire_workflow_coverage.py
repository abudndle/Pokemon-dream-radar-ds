#!/usr/bin/env python3
"""Prevent helper-only changes from silently skipping real melonDS CI."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
workflow = (ROOT / ".github/workflows/melonds-smoke.yml").read_text()
script = (ROOT / "scripts/melonds_smoke.sh").read_text()
makefile = (ROOT / "Makefile").read_text()

for path in (
    "tools/sphere_prefire_gate.py",
    "tools/verify_sphere_prefire_frame.py",
    "tests/test_prefire_frame.py",
    "tests/test_sphere_prefire_gate.py",
    "tests/test_sphere_fire_gating.py",
    "tools/summarize_capture_attempt.py",
    "tests/test_capture_progress_summary.py",
):
    assert f"      - '{path}'" in workflow, f"Missing pull-request path trigger: {path}"

assert "python3 -m py_compile" in workflow
assert re.search(r"python3 -m py_compile[^\n]*tools/sphere_prefire_gate.py", workflow)
for test in ("test_sphere_prefire_gate.py", "test_sphere_fire_gating.py", "test_prefire_frame.py"):
    assert f"python3 tests/{test}" in workflow
    assert f"python3 tests/{test}" in makefile
assert script.count('python3 tools/verify_sphere_prefire_frame.py "$prefire_frame"') == 2
assert 'tools/sphere_prefire_gate.py' not in script.split('    snapshot "05-sphere-prefire-$step"', 1)[1].split('    # The last observed target is uniquely aligned.', 1)[0]
assert 'snapshot "05-sphere-prefire-$step"' in script
assert 'snapshot "05-sphere-prefire-corrected-$step"' in script

print("PASS: changes to the sphere prefire gate trigger melonDS CI and execute its regressions")
