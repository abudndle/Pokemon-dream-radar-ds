#!/usr/bin/env python3
"""Classify one fresh melonDS prefire PNG with one pixel decode.

This combines reward, encounter, unique-target and observed-only gate checks.
No result authorizes firing from a previous screenshot or a motion prediction.
Exit statuses: 0 aligned, 10 unaligned, 11 ambiguous target,
12 not an encounter, 20 catalog-backed reward, 13 invalid input.
"""
import argparse
import json
from pathlib import Path
import subprocess
import time

from plan_melonds_aim import plan_sphere
from sphere_prefire_gate import evaluate
from verify_melonds_navigation import (decode_native_capture, font_rows,
                                       read_capture_progress, read_capture_reward)

EXIT_CODES = {"aligned": 0, "unaligned": 10, "ambiguous": 11,
              "not_encounter": 12, "reward": 20}


def inspect_frame(pixels, width, height, font):
    """Classify one screenshot, never trusting sidecar JSON or old aim plans."""
    try:
        reward = read_capture_reward(pixels, width, height, font)
    except ValueError:
        pass
    else:
        return "reward", reward, None, None, None
    try:
        progress = read_capture_progress(pixels, width, height, font)
    except ValueError:
        return "not_encounter", None, None, None, None
    try:
        aim = plan_sphere(pixels, width, height)
    except ValueError:
        return "ambiguous", None, progress, None, None
    gate = evaluate(aim)
    return ("aligned" if gate["fire_authorized"] else "unaligned",
            None, progress, aim, gate)


def write_evidence(paths, result):
    """Delete stale output first; only write observations from this frame."""
    status, reward, progress, aim, gate = result
    for path in paths.values():
        path.unlink(missing_ok=True)
    for key, value in (("reward", reward), ("progress", progress),
                       ("aim", aim), ("gate", gate)):
        if value is not None:
            paths[key].write_text(json.dumps(value, indent=2) + "\n")
    return status


def pulse_if_aligned(status):
    """Fire inside the fresh-frame inspector, minimizing post-gate delay.

    The only permitted pulse follows the same-frame unique-target gate.
    Always release A even if keydown, sleeping, or the emulator fails.
    The return value records an input pulse, NOT a verified hit.
    """
    if status != "aligned":
        return False
    try:
        subprocess.run(["xdotool", "keydown", "--clearmodifiers", "z"],
                       check=True, timeout=3)
        time.sleep(0.16)
    finally:
        subprocess.run(["xdotool", "keyup", "z"], check=True, timeout=3)
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("screenshot", type=Path)
    for name in ("reward", "progress", "aim", "gate"):
        parser.add_argument("--" + name, required=True, type=Path)
    parser.add_argument("--fire-aligned", action="store_true",
                        help="Pulse DS A immediately after a fresh aligned observation; never on other statuses")
    args = parser.parse_args()
    paths = {name: getattr(args, name) for name in ("reward", "progress", "aim", "gate")}
    # A failed decode must not leave stale gate JSON that looks authorized.
    for path in paths.values():
        path.unlink(missing_ok=True)
    try:
        pixels, width, height = decode_native_capture(args.screenshot)
        result = inspect_frame(pixels, width, height, font_rows())
        status = write_evidence(paths, result)
        fired = pulse_if_aligned(status) if args.fire_aligned else False
    except (OSError, ValueError, subprocess.CalledProcessError,
            subprocess.TimeoutExpired) as exc:
        # A failed key pulse must never leave an authorized gate sidecar.
        paths["gate"].unlink(missing_ok=True)
        parser.exit(13, f"Prefire frame inspection failed: {exc}\n")
    print(json.dumps({"status": status, "fire_authorized": status == "aligned",
                      "fire_executed": fired,
                      "limitations": "Fresh fallback screenshot only; not proof of hit, capture, save or restart."}))
    return EXIT_CODES[status]


if __name__ == "__main__":
    raise SystemExit(main())
