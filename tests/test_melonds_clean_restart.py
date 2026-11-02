#!/usr/bin/env python3
"""Synthetic regressions for strict restart provenance (not live emulator proof)."""
import json
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from verify_melonds_clean_restart import verify_restart

PNG = bytes((137, 80, 78, 71, 13, 10, 26, 10)) + b"synthetic-test-only"


def fixture(root):
    first, second = root / "first", root / "second"
    first.mkdir()
    second.mkdir()
    for path in (first / "03-shop-orbs-before.png",
                 first / "08-shop-orbs-after.png",
                 second / "03-shop-orbs-before.png"):
        path.write_bytes(PNG)
    (first / "runtime.log").write_text(
        "Emulator launcher PID: 1001\nEmulator launcher PID 1001 terminated\n")
    (second / "runtime.log").write_text(
        "Emulator launcher PID: 1002\nEmulator launcher PID 1002 terminated\n")
    (first / "orb-balance-change.json").write_text(json.dumps({
        "before": {"saved_orbs": 0},
        "after": {"saved_orbs": 2},
        "balance_increased": True}))
    (second / "orb-balance-before.json").write_text(
        json.dumps({"saved_orbs": 2}))
    save = root / "dream_radar.dreamradar.sav"
    save.write_bytes(b"synthetic-save-media")
    return first, second, save


with tempfile.TemporaryDirectory() as temporary:
    root = Path(temporary)
    first, second, save = fixture(root)
    assert verify_restart(first, second, save)["persistence_verified"]
    def rejected(change):
        change()
        try:
            verify_restart(first, second, save)
        except (ValueError, OSError, KeyError):
            return
        raise AssertionError("Unverified restart evidence accepted")

    original = (second / "orb-balance-before.json").read_text()
    rejected(lambda: (second / "orb-balance-before.json").write_text(
        json.dumps({"saved_orbs": 1})))
    (second / "orb-balance-before.json").write_text(original)
    original = (second / "runtime.log").read_text()
    rejected(lambda: (second / "runtime.log").write_text(
        "Emulator launcher PID: 1001\nEmulator launcher PID 1001 terminated\n"))
    (second / "runtime.log").write_text(original)
    rejected(lambda: (second / "runtime.log").write_text(
        "Emulator launcher PID: 1002\n"))
    (second / "runtime.log").write_text(original)
    original = (first / "runtime.log").read_text()
    rejected(lambda: (first / "runtime.log").write_text(
        "Emulator launcher PID: 1001\n"))
    (first / "runtime.log").write_text(original)
    save.unlink()
    try:
        verify_restart(first, second, save)
    except (ValueError, OSError):
        pass
    else:
        raise AssertionError("Missing save media accepted")
    save.write_bytes(b"synthetic-save-media")
    assert verify_restart(first, second, save)["persistence_verified"]
    # Strict CI mode must independently decode all three PNG balances.
    from unittest.mock import patch
    with patch("verify_melonds_clean_restart.decode_native_capture",
               return_value=(b"", 256, 403)), \
         patch("verify_melonds_clean_restart.font_rows", return_value=[]), \
         patch("verify_melonds_clean_restart.read_shop_orb_balance",
               side_effect=[{"saved_orbs": 0}, {"saved_orbs": 2}, {"saved_orbs": 2}]):
        assert verify_restart(first, second, save, verify_pixels=True)["persistence_verified"]
    with patch("verify_melonds_clean_restart.decode_native_capture",
               return_value=(b"", 256, 403)), \
         patch("verify_melonds_clean_restart.font_rows", return_value=[]), \
         patch("verify_melonds_clean_restart.read_shop_orb_balance",
               side_effect=[{"saved_orbs": 0}, {"saved_orbs": 2}, {"saved_orbs": 1}]):
        try:
            verify_restart(first, second, save, verify_pixels=True)
        except ValueError:
            pass
        else:
            raise AssertionError("Sidecar JSON accepted despite mismatched screenshot digits")
    try:
        verify_restart(first, first, save)
    except ValueError:
        pass
    else:
        raise AssertionError("Same-session evidence accepted")
    (second / "03-shop-orbs-before.png").write_bytes(b"not-a-png")
    try:
        verify_restart(first, second, save)
    except ValueError:
        pass
    else:
        raise AssertionError("Invalid screenshot accepted")

# melonDS config's DLDI.ImageSize is a combobox index (0=auto, 1=256MB,
# 2=512MB, 3=1GB, 4=2GB, 5=4GB), NOT a byte count.
import re
workflow = (Path(__file__).resolve().parents[1] /
            ".github/workflows/melonds-smoke.yml").read_text()
sizes = re.findall(r"^\s*ImageSize = ([0-9]+)$", workflow, re.M)
assert len(sizes) == 1 and 0 <= int(sizes[0]) <= 5, sizes
assert "FolderSync = true" in workflow and "ReadOnly = false" in workflow
print("PASS: clean-restart gate rejects same PID, missing save, false balance and invalid screenshots")
