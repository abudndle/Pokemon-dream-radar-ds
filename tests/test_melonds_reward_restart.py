#!/usr/bin/env python3
"""Synthetic reward-restart provenance regressions; not live capture proof."""
import json
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from verify_melonds_reward_restart import verify_reward_restart

PNG = bytes((137, 80, 78, 71, 13, 10, 26, 10)) + b"synthetic-only"
REWARD = {"reward_kind": "item", "reward_name": "Sun Stone"}


def check(first, second, save, visible=(REWARD, REWARD, REWARD)):
    with patch("verify_melonds_reward_restart.decode_native_capture",
               return_value=(b"", 256, 403)), \
         patch("verify_melonds_reward_restart.font_rows", return_value=[]), \
         patch("verify_melonds_reward_restart.read_capture_reward",
               side_effect=list(visible)):
        return verify_reward_restart(first, second, save)


def rejected(first, second, save, visible=(REWARD, REWARD, REWARD)):
    try:
        check(first, second, save, visible)
    except (ValueError, OSError, KeyError):
        return
    raise AssertionError("Unverified reward restoration accepted")


with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    first, second = root / "first", root / "second"
    first.mkdir()
    second.mkdir()
    (first / "05-capture-reward.png").write_bytes(PNG)
    (first / "06-results-preserved.png").write_bytes(PNG)
    (second / "03-restored-capture-reward.png").write_bytes(PNG)
    (first / "sphere-reward.json").write_text(json.dumps(REWARD))
    (first / "reward-preserved-before-exit.json").write_text(json.dumps(REWARD))
    (second / "restored-reward.json").write_text(json.dumps(REWARD))
    (first / "runtime.log").write_text(
        "Emulator launcher PID: 101\nEmulator launcher PID 101 terminated\n")
    (second / "runtime.log").write_text(
        "Emulator launcher PID: 102\nEmulator launcher PID 102 terminated\n")
    save = root / "dream_radar.dreamradar.sav"
    save.write_bytes(b"synthetic-save")
    report = check(first, second, save)
    assert report["visible_reward_restored"] is True
    assert report["visible_reward_preserved_before_shutdown"] is True
    assert len(report["save_file_sha256"]) == 64
    assert report["reward"] == REWARD
    assert report["first_pid"] == 101 and report["restart_pid"] == 102
    rejected(first, first, save)
    rejected(first, second, save, (REWARD, REWARD, {"reward_kind": "pokemon", "reward_name": "Tornadus"}))
    rejected(first, second, save, (REWARD, {"reward_kind": "pokemon", "reward_name": "Tornadus"}, REWARD))
    preserved = first / "reward-preserved-before-exit.json"
    original_preserved = preserved.read_text()
    preserved.write_text(json.dumps({"reward_kind": "item", "reward_name": "Moon Stone"}))
    rejected(first, second, save)
    preserved.write_text(original_preserved)
    preserved_png = first / "06-results-preserved.png"
    preserved_png.unlink()
    rejected(first, second, save)
    preserved_png.write_bytes(b"invalid PNG")
    rejected(first, second, save)
    preserved_png.write_bytes(PNG)
    old = (second / "restored-reward.json").read_text()
    (second / "restored-reward.json").write_text(json.dumps({
        "reward_kind": "pokemon", "reward_name": "Tornadus"}))
    rejected(first, second, save)
    (second / "restored-reward.json").write_text(old)
    log = (second / "runtime.log").read_text()
    (second / "runtime.log").write_text(
        "Emulator launcher PID: 101\nEmulator launcher PID 101 terminated\n")
    rejected(first, second, save)
    (second / "runtime.log").write_text(
        "Emulator launcher PID: 102\nEmulator launcher PID 102 force-killed\n"
        "Emulator launcher PID 102 terminated\n")
    rejected(first, second, save)
    (second / "runtime.log").write_text("Emulator launcher PID: 102\n")
    rejected(first, second, save)
    (second / "runtime.log").write_text(
        "Emulator launcher PID: 102\nEmulator launcher PID 102 terminated unexpectedly\n")
    rejected(first, second, save)
    (second / "runtime.log").write_text(
        "Emulator launcher PID: 102\nEmulator launcher PID 102 terminated\n"
        "Emulator launcher PID 102 terminated\n")
    rejected(first, second, save)
    (second / "runtime.log").write_text(log)
    (second / "runtime.log").write_text(log + "Emulator launcher PID: 103\nEmulator launcher PID 103 terminated\n")
    rejected(first, second, save)
    (second / "runtime.log").write_text(log)
    first_log = (first / "runtime.log").read_text()
    (first / "runtime.log").write_text(first_log + "Emulator launcher PID: 104\n")
    rejected(first, second, save)
    (first / "runtime.log").write_text(first_log)
    image = second / "03-restored-capture-reward.png"
    image.write_bytes(b"invalid PNG")
    rejected(first, second, save)
    image.write_bytes(PNG)
    save.unlink()
    rejected(first, second, save)
    save.write_bytes(b"synthetic-save")
    assert check(first, second, save)["visible_reward_restored"]

print("PASS: reward restart requires two screenshot-decoded matching rewards and distinct clean emulator processes")
