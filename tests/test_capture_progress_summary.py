#!/usr/bin/env python3
"""Synthetic regressions for capture-meter reporting and reward evidence."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from summarize_capture_attempt import summarize
from sphere_prefire_gate import evaluate as evaluate_prefire

with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    assert summarize(root)["samples"] == 0
    assert summarize(root)["paired_positive_pulse_fraction"] is None
    assert summarize(root)["postfire_meter_effectiveness_by_class"] == {}
    assert summarize(root)["max_meter_observation"] is None
    assert summarize(root)["prefire_gate_evaluations"] == 0
    def observation(name, value, klass="swift"):
        (root / name).write_text(json.dumps({"encounter": {"capture_class": klass},
                                              "filled_pixels": value, "bar_width": 177}))
    observation("sphere-progress-2.json", 20)
    observation("sphere-before-progress-1.json", 0)
    observation("sphere-reacquire-progress-3-1.json", 14)
    observation("sphere-edge-progress-4.json", 33)
    observation("sphere-prefire-progress-5.json", 12)
    observation("sphere-prefire-corrected-progress-5.json", 17)
    observation("sphere-prefire-stationary-progress-5.json", 19)
    aligned = evaluate_prefire({"candidate_spheres": 1,
                                "target_screen": {"x": 128, "y": 96},
                                "offset": {"x": 0, "y": 0}})
    unaligned = evaluate_prefire({"candidate_spheres": 1,
                                  "target_screen": {"x": 150, "y": 96},
                                  "offset": {"x": 22, "y": 0}})
    (root / "sphere-prefire-gate-5.json").write_text(json.dumps(aligned))
    (root / "sphere-prefire-gate-6.json").write_text(json.dumps(unaligned))
    result = summarize(root)
    assert result["samples"] == 7
    assert result["prefire_gate_evaluations"] == 2
    assert result["prefire_aligned_observations"] == 1
    assert result["prefire_unaligned_observations"] == 1
    assert result["max_meter_pixels"] == 33
    # Corrupted alignment sidecars must not become evidence of an aligned shot.
    forged = dict(aligned)
    forged["fire_authorized"] = False
    (root / "sphere-prefire-gate-5.json").write_text(json.dumps(forged))
    try:
        summarize(root)
    except ValueError:
        pass
    else:
        raise AssertionError("Forged prefire authorization was accepted")
    (root / "sphere-prefire-gate-5.json").write_text(json.dumps(aligned))
    result = summarize(root)
    assert result["samples"] == 7 and result["max_meter_pixels"] == 33
    assert result["max_meter_observation"] == "sphere-edge-progress-4.json"
    assert not result["reward_screen_observed"] and not result["reward_persisted_after_restart"]
    (root / "sphere-reward.json").write_text(json.dumps({"reward_kind": "item", "reward_name": "Test Item"}))
    try:
        summarize(root)
    except ValueError:
        pass
    else:
        raise AssertionError("Accepted reward JSON without screenshot")
    (root / "05-capture-reward.png").write_bytes(b"\x89PNG\r\n\x1a\nsynthetic")
    # A valid signature and a catalog-looking JSON file do not establish
    # actual emulator reward pixels. Reject the forged screenshot.
    try:
        summarize(root)
    except ValueError:
        pass
    else:
        raise AssertionError("PNG signature and JSON alone claimed a capture")

    from unittest.mock import patch
    with (patch("summarize_capture_attempt.decode_native_capture",
                return_value=(b"synthetic-pixels", 256, 403)),
          patch("summarize_capture_attempt.font_rows", return_value=[]),
          patch("summarize_capture_attempt.read_capture_reward",
                return_value={"reward_kind": "item", "reward_name": "Test Item"}) as read_reward):
        assert summarize(root)["reward_screen_observed"]
        assert not summarize(root)["reward_persisted_after_restart"]
        assert read_reward.call_count == 2  # Two independent summaries read pixels
        # The displayed reward must match the sidecar exactly; no swapping
        # Pokémon for items or substituting a different catalog entry.
        read_reward.return_value = {"reward_kind": "pokemon", "reward_name": "Test Item"}
        try:
            summarize(root)
        except ValueError:
            pass
        else:
            raise AssertionError("Mismatched screenshot reward kind accepted")
        read_reward.return_value = {"reward_kind": "item", "reward_name": "Other Item"}
        try:
            summarize(root)
        except ValueError:
            pass
        else:
            raise AssertionError("Mismatched screenshot reward name accepted")
        read_reward.return_value = {"reward_kind": "item", "reward_name": "Test Item"}
        for bad in (True, 178, -1, 12.5):
            observation("sphere-progress-2.json", bad)
            try:
                summarize(root)
            except ValueError:
                pass
            else:
                raise AssertionError(f"Accepted invalid meter fill {bad!r}")
        observation("sphere-progress-2.json", 20)
        (root / "sphere-reward.json").write_text(json.dumps({"reward_kind": "pokemon", "reward_name": ""}))
        try:
            summarize(root)
        except ValueError:
            pass
        else:
            raise AssertionError("Accepted empty reward name")


# Report observed meter response to actual inspector-reported A pulses.
# This is diagnostic correlation, never a substitute for Results/restart proof.
with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    def meter(name, value):
        (root / name).write_text(json.dumps({
            "encounter": {"capture_class": "erratic"},
            "filled_pixels": value, "bar_width": 177}))
    aligned = evaluate_prefire({"candidate_spheres": 1,
                                "target_screen": {"x": 128, "y": 96},
                                "offset": {"x": 0, "y": 0}})
    for step in (1, 2, 3):
        (root / f"sphere-prefire-gate-{step}.json").write_text(json.dumps(aligned))
    def fired(name):
        (root / name).write_text(json.dumps({
            "status": "aligned", "fire_authorized": True, "fire_executed": True}))
    meter("sphere-prefire-progress-1.json", 8)
    meter("sphere-progress-1.json", 14)
    fired("sphere-prefire-inspection-1.json")
    meter("sphere-prefire-corrected-progress-2.json", 12)
    fired("sphere-prefire-corrected-inspection-2.json")
    # No postfire frame: not a zero-damage shot and not a proven gain.
    meter("sphere-prefire-stationary-progress-3.json", 16)
    meter("sphere-progress-3.json", 13)
    fired("sphere-prefire-stationary-inspection-3.json")
    result = summarize(root)
    assert result["inspector_reported_fire_pulses"] == 3
    assert result["paired_postfire_meter_observations"] == 2
    assert result["unpaired_fire_pulses"] == 1
    assert result["positive_postfire_meter_deltas"] == 1
    assert result["max_postfire_meter_gain_pixels"] == 6
    assert result["negative_postfire_meter_deltas"] == 1
    assert result["zero_postfire_meter_deltas"] == 0
    assert result["paired_positive_pulse_fraction"] == 0.5
    assert result["postfire_meter_effectiveness_by_class"] == {
        "erratic": {"reported_pulses": 3, "paired_meter_observations": 2,
                    "positive_meter_deltas": 1, "negative_meter_deltas": 1,
                    "unpaired_pulses": 1}}
    # A different encounter class in the postfire screenshot cannot be
    # correlated with the prefire pulse, even if its meter is larger.
    (root / "sphere-progress-1.json").write_text(json.dumps({
        "encounter": {"capture_class": "swift"},
        "filled_pixels": 14, "bar_width": 177}))
    try:
        summarize(root)
    except ValueError as exc:
        assert "Cross-encounter" in str(exc)
    else:
        raise AssertionError("Cross-encounter pulse gain was accepted")
    meter("sphere-progress-1.json", 14)
    assert result["postfire_meter_delta_samples"] == [
        {"step": 1, "prefire_meter": 8, "postfire_meter": 14, "meter_delta": 6},
        {"step": 2, "prefire_meter": 12, "postfire_meter": None, "meter_delta": None},
        {"step": 3, "prefire_meter": 16, "postfire_meter": 13, "meter_delta": -3},
    ]
    # A gate alone never establishes an executed pulse.
    (root / "sphere-prefire-inspection-1.json").write_text(json.dumps({
        "status": "aligned", "fire_authorized": True, "fire_executed": False}))
    assert summarize(root)["inspector_reported_fire_pulses"] == 2
    fired("sphere-prefire-inspection-1.json")
    # A second claimed pulse on the same step cannot inflate evidence.
    fired("sphere-prefire-corrected-inspection-1.json")
    try:
        summarize(root)
    except ValueError:
        pass
    else:
        raise AssertionError("Duplicate pulse accepted")
    (root / "sphere-prefire-corrected-inspection-1.json").unlink()
    # A mismatched gate or an unaligned firing claim is rejected.
    (root / "sphere-prefire-gate-1.json").write_text(json.dumps({
        **aligned, "fire_authorized": False}))
    try:
        summarize(root)
    except ValueError:
        pass
    else:
        raise AssertionError("Forged gate accepted")
    (root / "sphere-prefire-gate-1.json").write_text(json.dumps(aligned))
    (root / "sphere-prefire-inspection-1.json").write_text(json.dumps({
        "status": "unaligned", "fire_authorized": False, "fire_executed": True}))
    try:
        summarize(root)
    except ValueError:
        pass
    else:
        raise AssertionError("Unaligned firing claim accepted")
    fired("sphere-prefire-inspection-1.json")
    # A missing prefire meter cannot silently become a measured shot.
    (root / "sphere-prefire-progress-1.json").unlink()
    try:
        summarize(root)
    except ValueError:
        pass
    else:
        raise AssertionError("Fired pulse without baseline meter accepted")

with tempfile.TemporaryDirectory() as tmp:
    assert subprocess.run([sys.executable, str(ROOT / "tools/summarize_capture_attempt.py"), tmp],
                          capture_output=True).returncode == 0

smoke = (ROOT / "scripts/melonds_smoke.sh").read_text()
assert 'tools/summarize_capture_attempt.py "$out"' in smoke
print("PASS: capture meter summary never promotes progress into persisted reward claims")
