#!/usr/bin/env python3
"""Synthetic extension-budget checks; not real capture evidence."""
from pathlib import Path
import json
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from check_capture_extension import should_extend

base = {"max_meter_pixels": 110, "samples": 704,
        "meter_width_pixels": 177, "capture_classes_observed": ["drifting"],
        "reward_screen_observed": False}
assert should_extend(base)[0] is True
for peak in (0, 1, 23):
    assert should_extend({**base, "max_meter_pixels": peak})[0] is False
assert should_extend({**base, "max_meter_pixels": 24})[0] is True
assert should_extend({**base, "max_meter_pixels": 177})[0] is True
assert should_extend({**base, "reward_screen_observed": True})[0] is False
for bad in (
    {**base, "max_meter_pixels": True},
    {**base, "max_meter_pixels": -1},
    {**base, "max_meter_pixels": 178},
    {**base, "samples": 0},
    {**base, "meter_width_pixels": 0},
    {**base, "capture_classes_observed": []},
    {**base, "capture_classes_observed": ["unknown"]},
    {**base, "capture_classes_observed": [{"drifting": True}]},
    {**base, "capture_classes_observed": [["drifting"]]},
    {**base, "capture_classes_observed": [None]},
    {**base, "capture_classes_observed": [42]},
    {**base, "reward_screen_observed": "false"},
    {"max_meter_pixels": 110},
):
    try:
        should_extend(bad)
    except ValueError:
        pass
    else:
        raise AssertionError(f"Invalid evidence accepted: {bad}")

with tempfile.TemporaryDirectory() as tmp:
    path = Path(tmp) / "progress.json"
    cmd = [sys.executable, str(ROOT / "tools/check_capture_extension.py"), str(path)]
    for evidence, expected in ((base, 0), ({**base, "max_meter_pixels": 0}, 3),
                               ({**base, "samples": -1}, 2),
                               ({**base, "capture_classes_observed": [{"bad": True}]}, 2)):
        path.write_text(json.dumps(evidence))
        result = subprocess.run(cmd, capture_output=True, text=True)
        assert result.returncode == expected, (result.returncode, result.stderr)
        if expected != 2:
            assert json.loads(result.stdout)["extend"] == (expected == 0)
    path.write_text("{bad json")
    assert subprocess.run(cmd, capture_output=True).returncode == 2
print("PASS: only validated positive meter evidence extends bounded live pursuit")
