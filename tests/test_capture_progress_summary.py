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

with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    assert summarize(root)["samples"] == 0
    def observation(name, value, klass="swift"):
        (root / name).write_text(json.dumps({"encounter": {"capture_class": klass},
                                              "filled_pixels": value, "bar_width": 177}))
    observation("sphere-progress-2.json", 20)
    observation("sphere-before-progress-1.json", 0)
    observation("sphere-reacquire-progress-3-1.json", 14)
    observation("sphere-edge-progress-4.json", 33)
    result = summarize(root)
    assert result["samples"] == 4 and result["max_meter_pixels"] == 33
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
        read_reward.assert_called_once()
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
