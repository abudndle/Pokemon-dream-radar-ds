#!/usr/bin/env python3
"""Verify a visible Pokémon/item reward after two separate melonDS launches.

This checks screenshot-decoded Results text, separate terminated emulator
processes and nonempty DLDI save media. It is not proof of Nintendo transfer,
original-game parity, or an independent inventory inspection.
"""
import argparse
import json
from pathlib import Path

from verify_melonds_clean_restart import _pid
from verify_melonds_navigation import (
    decode_native_capture, font_rows, read_capture_reward,
)


def _json(path):
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ValueError(f"Invalid reward sidecar: {path}")
    if (value.get("reward_kind") not in ("pokemon", "item")
            or not isinstance(value.get("reward_name"), str)
            or not value["reward_name"].strip()):
        raise ValueError(f"Missing catalog-backed reward fields: {path}")
    return {"reward_kind": value["reward_kind"],
            "reward_name": value["reward_name"]}


def _image(path, font):
    if not path.is_file() or path.stat().st_size < 8:
        raise ValueError(f"Missing reward screenshot: {path}")
    if path.open("rb").read(8) != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"Invalid PNG signature: {path}")
    pixels, width, height = decode_native_capture(path)
    return read_capture_reward(pixels, width, height, font)


def verify_reward_restart(first_dir, restart_dir, save_file):
    first_dir, restart_dir, save_file = map(Path, (first_dir, restart_dir, save_file))
    if first_dir.resolve() == restart_dir.resolve():
        raise ValueError("Restart requires separate evidence directories")
    if not save_file.is_file() or save_file.stat().st_size == 0:
        raise ValueError("No nonempty writable DLDI save media")
    first_log = (first_dir / "runtime.log").read_text()
    second_log = (restart_dir / "runtime.log").read_text()
    first_pid, second_pid = _pid(first_log), _pid(second_log)
    if first_pid == second_pid:
        raise ValueError("Same emulator process cannot prove restart")
    for label, log, pid in (("first", first_log, first_pid),
                            ("restart", second_log, second_pid)):
        if (f"Emulator launcher PID {pid} force-killed" in log
                or f"Emulator launcher PID {pid} still running" in log
                or f"Emulator launcher PID {pid} terminated" not in log):
            raise ValueError(f"{label} emulator did not terminate cleanly")
    first_sidecar = _json(first_dir / "sphere-reward.json")
    second_sidecar = _json(restart_dir / "restored-reward.json")
    font = font_rows()
    first_visible = _image(first_dir / "05-capture-reward.png", font)
    second_visible = _image(restart_dir / "03-restored-capture-reward.png", font)
    if first_visible != first_sidecar or second_visible != second_sidecar:
        raise ValueError("Reward sidecar disagrees with independently decoded screenshot")
    if first_visible != second_visible:
        raise ValueError("Fresh emulator did not restore the exact visible reward")
    return {
        "kind": "melonDS-two-process-visible-reward-restart",
        "first_pid": first_pid, "restart_pid": second_pid,
        "reward": first_visible, "visible_reward_restored": True,
        "limitations": ("Two independent Results screenshots and nonempty save media "
                        "do not establish official Pokémon transfer or original-game parity."),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("first_dir", type=Path)
    parser.add_argument("restart_dir", type=Path)
    parser.add_argument("save_file", type=Path)
    args = parser.parse_args()
    try:
        report = verify_reward_restart(args.first_dir, args.restart_dir, args.save_file)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        parser.exit(1, f"Reward restart acceptance failed: {exc}\n")
    print(json.dumps(report, indent=2))
    print("PASS: exact visible reward independently restored after melonDS restart")


if __name__ == "__main__":
    main()
