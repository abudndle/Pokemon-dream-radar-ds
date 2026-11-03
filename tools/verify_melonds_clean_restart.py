#!/usr/bin/env python3
"""Fail closed unless two real emulator sessions show saved Dream Orb restoration.

The JSON balance observations are produced by the existing screenshot reader.
This checker also requires separate launcher PIDs, first-process termination,
nonempty DLDI save media and all three corresponding screenshot files.
It proves only Dream Orb balance persistence, never capture reward parity.
"""
import argparse
import json
from pathlib import Path
import re
from verify_melonds_navigation import (compare_restart_shop_orb_balances,
                                       decode_native_capture, font_rows,
                                       read_shop_orb_balance)


def _read_json(path):
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ValueError(f"Invalid JSON observation: {path}")
    return value


def _pid(runtime):
    match = re.search(r"^Emulator launcher PID: ([1-9][0-9]*)$", runtime, re.M)
    if not match:
        raise ValueError("Missing emulator launcher PID evidence")
    return int(match.group(1))


def verify_restart(first_dir, second_dir, save_file, *, verify_pixels=False):
    first_dir, second_dir, save_file = map(Path, (first_dir, second_dir, save_file))
    if first_dir.resolve() == second_dir.resolve():
        raise ValueError("Restart evidence must come from different output directories")
    for path in (first_dir / "03-shop-orbs-before.png",
                 first_dir / "08-shop-orbs-after.png",
                 second_dir / "03-shop-orbs-before.png"):
        if not path.is_file() or path.stat().st_size < 8:
            raise ValueError(f"Missing emulator screenshot: {path}")
        if path.open("rb").read(8) != b"\x89PNG\r\n\x1a\n":
            raise ValueError(f"Invalid PNG screenshot signature: {path}")
    if not save_file.is_file() or save_file.stat().st_size == 0:
        raise ValueError("No nonempty writable DLDI save file")
    first_log = (first_dir / "runtime.log").read_text()
    second_log = (second_dir / "runtime.log").read_text()
    # Reject concatenated session logs and require exactly one clean-exit
    # record for each distinct emulator launcher.
    for label, runtime in (("first", first_log), ("second", second_log)):
        launchers = re.findall(r"^Emulator launcher PID: ([1-9][0-9]*)$", runtime, re.M)
        if len(launchers) != 1:
            raise ValueError(f"{label} log must identify exactly one emulator launcher")
    first_pid, second_pid = _pid(first_log), _pid(second_log)
    if first_pid == second_pid:
        raise ValueError("Same emulator process cannot prove restart")
    for label, runtime, launcher_pid in (
        ("first", first_log, first_pid), ("second", second_log, second_pid)
    ):
        if (re.search(
                rf"^Emulator launcher PID {launcher_pid} (?:force-killed|still running)(?:$|\\s)",
                runtime, re.M)
                or len(re.findall(
                    rf"^Emulator launcher PID {launcher_pid} terminated$",
                    runtime, re.M)) != 1):
            raise ValueError(f"{label} emulator did not terminate cleanly")
    first_exited = True
    first = _read_json(first_dir / "orb-balance-change.json")
    restarted = _read_json(second_dir / "orb-balance-before.json")
    if verify_pixels:
        # Re-read the visible gold ORBS digits from all three PNGs rather
        # than trusting the sidecar JSON. CI must never accept invented or
        # stale counter files as independent emulator observations.
        font = font_rows()
        observations = (
            (first_dir / "03-shop-orbs-before.png", first["before"]),
            (first_dir / "08-shop-orbs-after.png", first["after"]),
            (second_dir / "03-shop-orbs-before.png", restarted),
        )
        for path, expected in observations:
            pixels, width, height = decode_native_capture(path)
            decoded = read_shop_orb_balance(pixels, width, height, font)
            if decoded != expected:
                raise ValueError(f"Screenshot Orb balance differs from JSON: {path}")
    result = compare_restart_shop_orb_balances(
        first["before"], first["after"], restarted,
        first_pid=first_pid, restart_pid=second_pid,
        first_process_exited=first_exited,
        save_media_present=True)
    if not result["persistence_verified"]:
        raise ValueError(f"Clean restart did not restore gained Orbs: {result['status']}")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("first_dir", type=Path)
    parser.add_argument("restart_dir", type=Path)
    parser.add_argument("save_file", type=Path)
    parser.add_argument("--verify-pixels", action="store_true",
                        help="Decode each actual emulator PNG and cross-check the ORBS digits")
    args = parser.parse_args()
    try:
        result = verify_restart(args.first_dir, args.restart_dir, args.save_file,
                                verify_pixels=args.verify_pixels)
    except (ValueError, OSError, KeyError, json.JSONDecodeError) as exc:
        parser.exit(1, f"Clean-restart Orb acceptance failed: {exc}\n")
    print(json.dumps(result, indent=2))
    print("PASS: independent melonDS process restored exact saved Dream Orb balance")


if __name__ == "__main__":
    main()
