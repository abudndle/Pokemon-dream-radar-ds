#!/usr/bin/env python3
"""Regression tests for prefire inspector evidence."""
import json
import subprocess
import sys
import tempfile
from pathlib import Path
script = Path(__file__).resolve().parents[1] / "tools/check_prefire_correction.py"
with tempfile.TemporaryDirectory() as tmp:
    path = Path(tmp) / "inspection.json"
    def run(data, strict=False):
        path.write_text(json.dumps(data))
        return subprocess.run([sys.executable, str(script), str(path)] + (["--require-corrected"] if strict else []), capture_output=True, text=True)
    valid = {"status": "unaligned", "camera_correction_executed": True, "fire_executed": False}
    assert run(valid, True).stdout.strip() == "yes"
    assert run({**valid, "camera_correction_executed": False}).stdout.strip() == "no"
    assert run({**valid, "camera_correction_executed": False}, True).returncode == 1
    # A fresh unaligned observation inside the configured no-chase radius is
    # valid only when it explicitly proves that no correction was necessary.
    aim = Path(tmp) / "aim.json"
    aim.write_text(json.dumps({"offset": {"x": -15, "y": 10}}))
    near = subprocess.run([sys.executable, str(script), str(path),
                           "--allow-near-miss", "--aim", str(aim),
                           "--max-distance", "26"], capture_output=True, text=True)
    path.write_text(json.dumps({**valid, "camera_correction_executed": False}))
    near = subprocess.run([sys.executable, str(script), str(path),
                           "--allow-near-miss", "--aim", str(aim),
                           "--max-distance", "26"], capture_output=True, text=True)
    assert near.returncode == 0 and near.stdout.strip() == "no"
    aim.write_text(json.dumps({"offset": {"x": 27, "y": 10}}))
    far = subprocess.run([sys.executable, str(script), str(path),
                           "--allow-near-miss", "--aim", str(aim),
                           "--max-distance", "26"], capture_output=True, text=True)
    assert far.returncode == 1 and "exceeds no-chase radius" in far.stderr
    for bad in ({"status": "aligned"}, {"fire_executed": True}, {"fire_executed": None}, {"camera_correction_executed": 1}, {"camera_correction_executed": None}):
        result = run({**valid, **bad})
        assert result.returncode == 1 and "unsafe prefire correction" in result.stderr
print("PASS: correction contract rejects unsafe and contradictory evidence")
