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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("screenshot", type=Path)
    for name in ("reward", "progress", "aim", "gate"):
        parser.add_argument("--" + name, required=True, type=Path)
    args = parser.parse_args()
    paths = {name: getattr(args, name) for name in ("reward", "progress", "aim", "gate")}
    # A failed decode must not leave stale gate JSON that looks authorized.
    for path in paths.values():
        path.unlink(missing_ok=True)
    try:
        pixels, width, height = decode_native_capture(args.screenshot)
        result = inspect_frame(pixels, width, height, font_rows())
        status = write_evidence(paths, result)
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        parser.exit(13, f"Prefire frame inspection failed: {exc}\n")
    print(json.dumps({"status": status, "fire_authorized": status == "aligned",
                      "limitations": "Fresh fallback screenshot only; not proof of hit, capture, save or restart."}))
    return EXIT_CODES[status]


if __name__ == "__main__":
    raise SystemExit(main())
