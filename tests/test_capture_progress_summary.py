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
    aligned = evaluate_prefire({"candidate_spheres": 1,
                                "target_screen": {"x": 128, "y": 96},
                                "offset": {"x": 0, "y": 0}})
    unaligned = evaluate_prefire({"candidate_spheres": 1,
                                  "target_screen": {"x": 150, "y": 96},
                                  "offset": {"x": 22, "y": 0}})
    (root / "sphere-prefire-gate-5.json").write_text(json.dumps(aligned))
    (root / "sphere-prefire-gate-6.json").write_text(json.dumps(unaligned))
    result = summarize(root)
    assert result["samples"] == 6
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
    assert result["samples"] == 6 and result["max_meter_pixels"] == 33
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

with tempfile.TemporaryDirectory() as tmp:
    assert subprocess.run([sys.executable, str(ROOT / "tools/summarize_capture_attempt.py"), tmp],
                          capture_output=True).returncode == 0

smoke = (ROOT / "scripts/melonds_smoke.sh").read_text()
assert 'tools/summarize_capture_attempt.py "$out"' in smoke
print("PASS: capture meter summary never promotes progress into persisted reward claims")
