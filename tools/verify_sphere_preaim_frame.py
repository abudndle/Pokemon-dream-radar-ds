#!/usr/bin/env python3
"""Classify a live pre-aim sphere frame with one PNG decode per screenshot.

Unlike the prefire inspector, this may use two-frame motion to plan CAMERA
movement. It never authorizes or sends a shot: only a later independent
observed-only prefire screenshot can do that. Reward recognition takes priority
over pursuit so the Results screen is not accidentally dismissed.
"""
import argparse
import json
from pathlib import Path

from plan_melonds_aim import plan_sphere_motion
from verify_melonds_navigation import (decode_native_capture, font_rows,
                                       read_capture_progress, read_capture_reward)

EXIT_CODES = {"target": 0, "ambiguous": 11, "not_encounter": 12,
              "reward": 20}


def inspect_frame(pixels, previous_pixels, width, height, font):
    try:
        reward = read_capture_reward(pixels, width, height, font)
    except ValueError:
        pass
    else:
        return "reward", reward, None, None
    try:
        progress = read_capture_progress(pixels, width, height, font)
    except ValueError:
        return "not_encounter", None, None, None
    try:
        aim = plan_sphere_motion(previous_pixels, pixels, width, height)
    except ValueError:
        return "ambiguous", None, progress, None
    return "target", None, progress, aim


def write_evidence(paths, result):
    status, reward, progress, aim = result
    for path in paths.values():
        path.unlink(missing_ok=True)
    for key, value in (("reward", reward), ("progress", progress), ("aim", aim)):
        if value is not None:
            paths[key].write_text(json.dumps(value, indent=2) + "\n")
    return status


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("screenshot", type=Path)
    parser.add_argument("--previous-screenshot", required=True, type=Path)
    for name in ("reward", "progress", "aim"):
        parser.add_argument("--" + name, required=True, type=Path)
    args = parser.parse_args()
    paths = {name: getattr(args, name) for name in ("reward", "progress", "aim")}
    for path in paths.values():
        path.unlink(missing_ok=True)
    try:
        pixels, width, height = decode_native_capture(args.screenshot)
        # Do not require a previous valid image for an independently visible
        # reward or ended encounter. Only camera motion needs that history.
        try:
            reward = read_capture_reward(pixels, width, height, font_rows())
        except ValueError:
            reward = None
        if reward is not None:
            result = ("reward", reward, None, None)
        else:
            try:
                progress = read_capture_progress(pixels, width, height, font_rows())
            except ValueError:
                result = ("not_encounter", None, None, None)
            else:
                try:
                    old, old_w, old_h = decode_native_capture(args.previous_screenshot)
                    if (old_w, old_h) != (width, height):
                        raise ValueError("Previous sphere frame dimensions changed")
                    aim = plan_sphere_motion(old, pixels, width, height)
                except (OSError, ValueError):
                    result = ("ambiguous", None, progress, None)
                else:
                    result = ("target", None, progress, aim)
        status = write_evidence(paths, result)
    except (OSError, ValueError) as exc:
        parser.exit(13, f"Pre-aim frame inspection failed: {exc}\n")
    print(json.dumps({"status": status, "fire_authorized": False,
                      "limitations": "Pre-aim evidence permits camera movement only; fresh observed-only prefire required."}))
    return EXIT_CODES[status]


if __name__ == "__main__":
    raise SystemExit(main())
