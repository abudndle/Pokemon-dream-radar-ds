#!/usr/bin/env python3
"""Regress screenshot-derived postfire motion without claiming live capture."""
import json
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from analyze_sphere_motion import analyze
from sphere_prefire_gate import evaluate


def write(path, value):
    path.write_text(json.dumps(value))


with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    report = {"kind": "melonDS-sphere-capture-progress",
              "postfire_meter_delta_samples": []}
    write(root / "sphere-attempt-report.json", report)
    empty = analyze(root)
    assert empty["inspector_reported_pulses"] == 0
    assert empty["median_postfire_reticle_distance_pixels"] is None
    assert empty["postfire_targets_recognized"] == 0

    def fired(step, variant, x=128, y=96, delta=0):
        gate = evaluate({"candidate_spheres": 1,
                         "target_screen": {"x": x, "y": y},
                         "offset": {"x": x - 128, "y": y - 96}})
        assert gate["fire_authorized"]
        write(root / f"sphere-prefire-gate-{step}.json", gate)
        write(root / f"sphere-prefire-{variant}inspection-{step}.json",
              {"status": "aligned", "fire_authorized": True,
               "fire_executed": True})
        before = 2 if delta is not None and delta < 0 else 0
        report["postfire_meter_delta_samples"].append(
            {"step": step, "prefire_meter": before,
             "postfire_meter": before + delta if delta is not None else None,
             "meter_delta": delta})

    fired(1, "", delta=3)
    fired(2, "corrected-", delta=0)
    fired(3, "stationary-", delta=None)
    fired(4, "", delta=-1)
    write(root / "sphere-attempt-report.json", report)
    for step in (1, 2, 4):
        (root / f"05-sphere-sweep-{step}.png").write_bytes(b"test-png")
    for step, variant in ((1, ""), (2, "corrected-"), (4, "")):
        (root / f"05-sphere-prefire-{variant}{step}.png").write_bytes(b"test-png")
    with patch("analyze_sphere_motion.describe_projectiles",
               side_effect=[
                   {"projectile_centers": [{"x": 128, "y": 96}],
                    "projectile_near_reticle": True,
                    "nearest_projectile_distance_pixels": 0.0},
                   {"projectile_centers": [{"x": 109, "y": 139}],
                    "projectile_near_reticle": False,
                    "nearest_projectile_distance_pixels": 47.0},
                   {"projectile_centers": [],
                    "projectile_near_reticle": False,
                    "nearest_projectile_distance_pixels": None},
               ]) as projectiles, \
         patch("analyze_sphere_motion.decode_native_capture",
               return_value=(b"fake-rgb", 256, 403)) as decode, \
         patch("analyze_sphere_motion.plan_sphere",
               side_effect=[
                   {"target_screen": {"x": 132, "y": 96}},
                   {"target_screen": {"x": 160, "y": 96}},
                   ValueError("ambiguous")]) as track:
        result = analyze(root)
    assert decode.call_count == 6 and track.call_count == 3
    assert projectiles.call_count == 3
    assert result["prefire_projectile_frames_inspected"] == 3
    assert result["prefire_projectile_frames_missing"] == 1
    assert result["prefire_frames_with_projectiles"] == 2
    assert result["prefire_projectiles_near_reticle"] == 1
    assert result["shots"][0]["prefire_projectile_near_reticle"] is True
    assert result["shots"][2]["prefire_projectile_near_reticle"] is None
    assert result["inspector_reported_pulses"] == 4
    assert result["postfire_targets_recognized"] == 2
    assert result["postfire_targets_unrecognized"] == 1
    assert result["postfire_frames_missing"] == 1
    assert result["median_postfire_reticle_distance_pixels"] == 18
    assert result["postfire_near_reticle_observations"] == 1
    assert result["shots"][0]["postfire_target_displacement_pixels"] == 4
    assert result["shots"][1]["prefire_variant"] == "corrected-"
    assert result["shots"][2]["postfire_status"] == "missing_frame"
    assert result["shots"][3]["postfire_status"] == "target_not_uniquely_recognized"
    strata = result["meter_response_by_projectile_proximity"]
    assert strata["near_reticle"]["reported_pulses"] == 1
    assert strata["near_reticle"]["positive_meter_changes"] == 1
    assert strata["near_reticle"]["median_postfire_displacement_pixels"] == 4
    assert strata["not_near_reticle"]["reported_pulses"] == 2
    assert strata["not_near_reticle"]["zero_meter_changes"] == 1
    assert strata["not_near_reticle"]["negative_meter_changes"] == 1
    assert strata["unknown"]["reported_pulses"] == 1
    assert strata["unknown"]["unpaired_pulses"] == 1
    assert "not proof" in result["limitations"]

    # Keep adversarial JSON tests independent of image decoder mocks. The
    # previous valid frames were deliberately synthetic, not native PNGs.
    for step in (1, 2, 4):
        (root / f"05-sphere-sweep-{step}.png").unlink()
    for step, variant in ((1, ""), (2, "corrected-"), (4, "")):
        (root / f"05-sphere-prefire-{variant}{step}.png").unlink()
    # Duplicate pulse rows, forged gates and conflicting inspectors must
    # fail closed rather than inflating measured aiming effectiveness.
    report["postfire_meter_delta_samples"].append(dict(report["postfire_meter_delta_samples"][0]))
    write(root / "sphere-attempt-report.json", report)
    try:
        analyze(root)
    except ValueError as exc:
        assert "Duplicate" in str(exc)
    else:
        raise AssertionError("Duplicate pulse row accepted")
    report["postfire_meter_delta_samples"].pop()
    write(root / "sphere-attempt-report.json", report)
    gate_path = root / "sphere-prefire-gate-1.json"
    original = json.loads(gate_path.read_text())
    write(gate_path, {**original, "fire_authorized": False})
    try:
        analyze(root)
    except ValueError as exc:
        assert "authorization" in str(exc)
    else:
        raise AssertionError("Forged firing gate accepted")
    write(gate_path, original)
    write(root / "sphere-prefire-corrected-inspection-1.json",
          {"status": "aligned", "fire_authorized": True, "fire_executed": True})
    try:
        analyze(root)
    except ValueError as exc:
        assert "unique inspector" in str(exc)
    else:
        raise AssertionError("Multiple firing inspectors accepted")
    (root / "sphere-prefire-corrected-inspection-1.json").unlink()

    # The motion audit must not launder altered summary numbers or
    # contradictory firing inspector evidence into measured effectiveness.
    report["postfire_meter_delta_samples"][0]["meter_delta"] = 99
    write(root / "sphere-attempt-report.json", report)
    try:
        analyze(root)
    except ValueError as exc:
        assert "meter row" in str(exc)
    else:
        raise AssertionError("Forged postfire meter delta accepted")
    report["postfire_meter_delta_samples"][0]["meter_delta"] = 3
    report["postfire_meter_delta_samples"][0]["postfire_meter"] = True
    write(root / "sphere-attempt-report.json", report)
    try:
        analyze(root)
    except ValueError as exc:
        assert "meter row" in str(exc)
    else:
        raise AssertionError("Boolean meter observation accepted")
    report["postfire_meter_delta_samples"][0]["postfire_meter"] = 3
    report["inspector_reported_fire_pulses"] = 5
    write(root / "sphere-attempt-report.json", report)
    try:
        analyze(root)
    except ValueError as exc:
        assert "pulse count" in str(exc)
    else:
        raise AssertionError("Mismatched summary pulse count accepted")
    report["inspector_reported_fire_pulses"] = 4
    write(root / "sphere-attempt-report.json", report)
    inspector_path = root / "sphere-prefire-inspection-1.json"
    inspector = json.loads(inspector_path.read_text())
    write(inspector_path, {**inspector, "status": "unaligned"})
    try:
        analyze(root)
    except ValueError as exc:
        assert "Contradictory firing inspector" in str(exc)
    else:
        raise AssertionError("Unaligned inspector firing accepted")
    write(inspector_path, inspector)
    assert analyze(root)["meter_response_by_projectile_proximity"]["unknown"]["reported_pulses"] == 4

print("PASS: postfire motion diagnostics separate target movement from actual hit evidence")
