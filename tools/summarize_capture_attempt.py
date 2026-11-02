#!/usr/bin/env python3
"""Summarize screenshot-derived sphere meter observations without inferring capture.

A CI job passing does not imply capture. Results screenshots, not meter changes,
are required to mark a visible reward; a separate restart is needed for persistence.
"""
import argparse
import json
from pathlib import Path
import subprocess

from verify_melonds_navigation import (decode_native_capture, font_rows,
                                       read_capture_reward)

PATTERNS = ("sphere-before-progress-*.json", "sphere-progress-*.json",
            "sphere-reacquire-progress-*.json", "sphere-edge-progress-*.json")
CLASSES = {"drifting", "swift", "erratic", "legendary", "item"}


def summarize(directory):
    directory = Path(directory)
    observations = []
    for pattern in PATTERNS:
        for path in directory.glob(pattern):
            data = json.loads(path.read_text())
            if not isinstance(data, dict):
                raise ValueError(f"Malformed capture observation: {path}")
            value = data.get("filled_pixels")
            width = data.get("bar_width")
            encounter = data.get("encounter")
            if (type(value) is not int or type(width) is not int or width != 177
                    or not 0 <= value <= width or not isinstance(encounter, dict)
                    or encounter.get("capture_class") not in CLASSES):
                raise ValueError(f"Invalid capture meter evidence: {path}")
            observations.append({"file": path.name, "filled_pixels": value,
                                 "capture_class": encounter["capture_class"]})
    reward_path = directory / "sphere-reward.json"
    image_path = directory / "05-capture-reward.png"
    reward_observed = False
    reward = None
    if reward_path.exists() or image_path.exists():
        if not reward_path.is_file() or not image_path.is_file():
            raise ValueError("Capture reward sidecar and screenshot must both exist")
        reward = json.loads(reward_path.read_text())
        if (not isinstance(reward, dict) or reward.get("reward_kind") not in ("pokemon", "item")
                or not isinstance(reward.get("reward_name"), str)
                or not reward["reward_name"].strip()):
            raise ValueError("Invalid capture reward sidecar")
        if image_path.open("rb").read(8) != b"\x89PNG\r\n\x1a\n":
            raise ValueError("Capture reward screenshot has no PNG signature")
        # The sidecar alone is not evidence. Decode the actual emulator PNG
        # and independently recognize a unique catalog-backed Results reward.
        # A PNG signature or a fabricated JSON file must never mark capture.
        try:
            pixels, width, height = decode_native_capture(image_path)
            visible = read_capture_reward(pixels, width, height, font_rows())
        except (OSError, subprocess.SubprocessError) as exc:
            raise ValueError("Capture reward screenshot could not be decoded") from exc
        if visible != {"reward_kind": reward["reward_kind"],
                        "reward_name": reward["reward_name"]}:
            raise ValueError("Capture reward sidecar disagrees with visible Results")
        reward_observed = True
    return {"kind": "melonDS-sphere-capture-progress",
            "samples": len(observations),
            "max_meter_pixels": max((o["filled_pixels"] for o in observations), default=0),
            "meter_width_pixels": 177,
            "capture_classes_observed": sorted({o["capture_class"] for o in observations}),
            "reward_screen_observed": reward_observed,
            "reward": reward,
            "reward_persisted_after_restart": False,
            "limitations": "Meter fill is not a capture; a Results reward screenshot is not restart persistence. Independent two-process reward restoration remains required."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        report = summarize(args.directory)
    except (OSError, ValueError, subprocess.SubprocessError, json.JSONDecodeError) as exc:
        parser.exit(1, f"Capture progress summary failed: {exc}\n")
    content = json.dumps(report, indent=2) + "\n"
    if args.output:
        args.output.write_text(content)
    print(content, end="")


if __name__ == "__main__":
    main()
