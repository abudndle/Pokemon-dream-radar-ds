#!/usr/bin/env python3
"""Synthetic regressions for the no-fire, edge-only sphere camera nudge."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from plan_sphere_recovery import plan_edge_recovery


def plan(x, y):
    return {"candidate_spheres": 1, "observed_target_screen": {"x": x, "y": y},
            "target_screen": {"x": x + 12, "y": y + 12}}


for x, y, expected in ((128, 35, "Up"), (128, 180, "Down"),
                       (20, 96, "Left"), (239, 96, "Right"),
                       (20, 20, "Up")):
    result = plan_edge_recovery(plan(x, y))
    assert result["key"] == expected and result["seconds"] <= 0.12
    assert result["fire_authorized"] is False
    assert result["observed_target_screen"] == {"x": x, "y": y}

for invalid in (None, [], {}, plan(128, 96),
                {"candidate_spheres": 1, "target_screen": {"x": 15, "y": 15}},
                {"candidate_spheres": 2, "observed_target_screen": {"x": 20, "y": 20}},
                {"candidate_spheres": True, "observed_target_screen": {"x": 20, "y": 20}},
                plan(-1, 50), plan(128, 192), plan(True, 35), plan(12.0, 35)):
    try:
        plan_edge_recovery(invalid)
    except ValueError:
        pass
    else:
        raise AssertionError(f"Unsafe edge recovery accepted: {invalid!r}")

with tempfile.TemporaryDirectory() as tmp:
    path = Path(tmp) / "last-plan.json"
    path.write_text(json.dumps(plan(128, 38)))
    result = subprocess.run([sys.executable, str(ROOT / "tools/plan_sphere_recovery.py"),
                             str(path)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["key"] == "Up"
    path.write_text(json.dumps(plan(128, 100)))
    assert subprocess.run([sys.executable, str(ROOT / "tools/plan_sphere_recovery.py"),
                           str(path)], capture_output=True).returncode != 0

smoke = (ROOT / "scripts/melonds_smoke.sh").read_text()
assert "tools/plan_sphere_recovery.py" in smoke
assert "xdotool keyup z" in smoke
assert 'snapshot "05-sphere-edge-recovery-$step"' in smoke
assert 'last_sphere_plan="$out/sphere-aim-$step.json"' in smoke
print("PASS: sphere edge recovery requires observed edge, no fire and fresh screenshot")
