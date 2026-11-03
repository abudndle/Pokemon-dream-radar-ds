#!/usr/bin/env python3
"""Pre-aim single-pass regressions; synthetic evidence is not live capture."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from verify_sphere_preaim_frame import inspect_frame, write_evidence, EXIT_CODES

pixels = b"current"
previous = b"previous"
reward = {"reward_kind": "item", "reward_name": "Dawn Stone"}
progress = {"filled_pixels": 20, "bar_width": 177}
aim = {"candidate_spheres": 1, "target_screen": {"x": 125, "y": 93},
       "offset": {"x": -3, "y": -3}, "motion_prediction": "bounded"}
with patch("verify_sphere_preaim_frame.read_capture_reward", return_value=reward), \
     patch("verify_sphere_preaim_frame.read_capture_progress") as meter, \
     patch("verify_sphere_preaim_frame.plan_sphere_motion") as tracker:
    assert inspect_frame(pixels, previous, 256, 403, [])[0:2] == ("reward", reward)
    meter.assert_not_called()
    tracker.assert_not_called()
with patch("verify_sphere_preaim_frame.read_capture_reward", side_effect=ValueError), \
     patch("verify_sphere_preaim_frame.read_capture_progress", side_effect=ValueError), \
     patch("verify_sphere_preaim_frame.plan_sphere_motion") as tracker:
    assert inspect_frame(pixels, previous, 256, 403, [])[0] == "not_encounter"
    tracker.assert_not_called()
with patch("verify_sphere_preaim_frame.read_capture_reward", side_effect=ValueError), \
     patch("verify_sphere_preaim_frame.read_capture_progress", return_value=progress), \
     patch("verify_sphere_preaim_frame.plan_sphere_motion", return_value=aim) as tracker:
    result = inspect_frame(pixels, previous, 256, 403, [])
    assert result == ("target", None, progress, aim)
    tracker.assert_called_once_with(previous, pixels, 256, 403)
with patch("verify_sphere_preaim_frame.read_capture_reward", side_effect=ValueError), \
     patch("verify_sphere_preaim_frame.read_capture_progress", return_value=progress), \
     patch("verify_sphere_preaim_frame.plan_sphere_motion", side_effect=ValueError):
    assert inspect_frame(pixels, previous, 256, 403, [])[0] == "ambiguous"

# Missing prior frames can guide the camera from a unique CURRENT target,
# but never infer motion or authorize a shot.
with patch("verify_sphere_preaim_frame.read_capture_reward", side_effect=ValueError), \
     patch("verify_sphere_preaim_frame.read_capture_progress", return_value=progress), \
     patch("verify_sphere_preaim_frame.plan_sphere", return_value=aim) as single, \
     patch("verify_sphere_preaim_frame.plan_sphere_motion") as tracker:
    assert inspect_frame(pixels, None, 256, 403, []) == ("target", None, progress, aim)
    single.assert_called_once_with(pixels, 256, 403)
    tracker.assert_not_called()
with patch("verify_sphere_preaim_frame.read_capture_reward", side_effect=ValueError), \
     patch("verify_sphere_preaim_frame.read_capture_progress", return_value=progress), \
     patch("verify_sphere_preaim_frame.plan_sphere", side_effect=ValueError), \
     patch("verify_sphere_preaim_frame.plan_sphere_motion") as tracker:
    assert inspect_frame(pixels, None, 256, 403, [])[0] == "ambiguous"
    tracker.assert_not_called()

with tempfile.TemporaryDirectory() as tmp:
    paths = {key: Path(tmp) / (key + ".json") for key in ("reward", "progress", "aim")}
    for path in paths.values():
        path.write_text('{"stale": true}')
    write_evidence(paths, ("ambiguous", None, progress, None))
    assert not paths["reward"].exists() and not paths["aim"].exists()
    assert json.loads(paths["progress"].read_text()) == progress
    write_evidence(paths, ("target", None, progress, aim))
    assert json.loads(paths["aim"].read_text()) == aim
    write_evidence(paths, ("reward", reward, None, None))
    assert not paths["aim"].exists() and not paths["progress"].exists()
    assert json.loads(paths["reward"].read_text()) == reward
    image = Path(tmp) / "corrupt.png"
    image.write_bytes(b"not-a-png")
    command = [sys.executable, str(ROOT / "tools/verify_sphere_preaim_frame.py"),
               str(image), "--previous-screenshot", str(image)]
    for key, path in paths.items():
        command.extend(["--" + key, str(path)])
    run = subprocess.run(command, capture_output=True, text=True)
    assert run.returncode == 13
    assert all(not path.exists() for path in paths.values())

assert EXIT_CODES == {"target": 0, "ambiguous": 11, "not_encounter": 12, "reward": 20}
source = (ROOT / "tools/verify_sphere_preaim_frame.py").read_text()
assert "xdotool" not in source and "subprocess" not in source
assert '"fire_authorized": False' in source
print("PASS: pre-aim single-pass reward/encounter/target evidence never authorizes firing")
