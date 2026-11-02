#!/usr/bin/env python3
"""Synthetic near-miss retry regressions; no emulator capture is implied."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from check_stationary_retry import should_retry
from sphere_prefire_gate import evaluate


def decision(x, y=96):
    return evaluate({"candidate_spheres": 1,
                     "target_screen": {"x": x, "y": y},
                     "offset": {"x": x - 128, "y": y - 96}})


assert not should_retry(decision(128))
assert not should_retry(decision(141))
assert not should_retry(decision(142))
assert should_retry(decision(144))
assert should_retry(decision(154))
assert not should_retry(decision(155))
assert not should_retry(decision(200))
assert should_retry(decision(128, 122))
assert not should_retry(decision(128, 123))
for bad in (None, {}, {"observed_target_screen": {"x": True, "y": 96}},
            {**decision(150), "fire_authorized": True},
            {**decision(150), "observed_reticle_distance_squared": 0},
            {**decision(150), "motion_prediction": "bounded"},
            {**decision(150), "observed_target_screen": {"x": 256, "y": 96}}):
    try:
        should_retry(bad)
    except ValueError:
        pass
    else:
        raise AssertionError(f"Invalid retry evidence accepted: {bad}")

with tempfile.TemporaryDirectory() as tmp:
    path = Path(tmp) / "gate.json"
    cmd = [sys.executable, str(ROOT / "tools/check_stationary_retry.py"), str(path)]
    for evidence, status in ((decision(144), 0), (decision(155), 3),
                             (decision(128), 3), ({}, 2)):
        path.write_text(json.dumps(evidence))
        run = subprocess.run(cmd, capture_output=True, text=True)
        assert run.returncode == status, (status, run.stderr)
        if status in (0, 3):
            result = json.loads(run.stdout)
            assert result["fire_authorized"] is False
            assert result["take_fresh_screenshot"] is (status == 0)
    path.write_text("{invalid json")
    assert subprocess.run(cmd, capture_output=True).returncode == 2
print("PASS: near-miss retry permits only a fresh observation, never stale-frame firing")
