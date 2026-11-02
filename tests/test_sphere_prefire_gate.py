#!/usr/bin/env python3
"""Regression: no stale, predicted or ambiguous target can authorize firing."""
from pathlib import Path
import copy
import json
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from sphere_prefire_gate import evaluate

def plan(x, y):
    return {"candidate_spheres": 1, "target_screen": {"x": x, "y": y},
            "offset": {"x": x - 128, "y": y - 96}}

assert evaluate(plan(128, 96))["fire_authorized"] is True
assert evaluate(plan(141, 96))["fire_authorized"] is True
assert evaluate(plan(141, 97))["fire_authorized"] is False
assert evaluate(plan(142, 96))["fire_authorized"] is False
assert evaluate(plan(0, 0))["fire_authorized"] is False

for changed in (
    {"candidate_spheres": 0}, {"candidate_spheres": 2},
    {"candidate_spheres": True}, {"target_screen": {"x": 128.0, "y": 96}},
    {"target_screen": {"x": -1, "y": 96}}, {"target_screen": {"x": 256, "y": 96}},
    {"offset": {"x": 1, "y": 0}}, {"offset": {"x": False, "y": 0}},
    {"motion_prediction": "bounded"}, {"observed_displacement": {"x": 1, "y": 0}},
):
    invalid = plan(128, 96)
    invalid.update(changed)
    try:
        evaluate(invalid)
    except ValueError:
        pass
    else:
        raise AssertionError(f"Invalid prefire plan accepted: {changed}")

with tempfile.TemporaryDirectory() as tmp:
    path = Path(tmp) / "fresh-plan.json"
    path.write_text(json.dumps(plan(128, 96)))
    good = subprocess.run([sys.executable, str(ROOT / "tools/sphere_prefire_gate.py"),
                           str(path)], capture_output=True, text=True)
    assert good.returncode == 0
    assert json.loads(good.stdout)["fire_authorized"] is True
    path.write_text(json.dumps({**plan(128, 96), "motion_prediction": "bounded"}))
    bad = subprocess.run([sys.executable, str(ROOT / "tools/sphere_prefire_gate.py"),
                          str(path)], capture_output=True, text=True)
    assert bad.returncode != 0 and "refused" in bad.stderr

print("PASS: fresh observed sphere alignment gates firing; stale motion and invalid targets fail closed")
