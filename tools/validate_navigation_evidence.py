#!/usr/bin/env python3
"""Require complete, distinct, correctly ordered emulator navigation evidence."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from verify_melonds_navigation import STAGES, font_rows, decode_native_capture, check_heading


def check_report(report, screenshot_dir=None):
    if not isinstance(report, dict) or report.get("kind") != "melonds-native-ds-navigation":
        raise ValueError("Not a native melonDS navigation report")
    stages = report.get("stages")
    expected = list(STAGES)
    if not isinstance(stages, list) or len(stages) != len(expected):
        raise ValueError("Incomplete navigation stage sequence")
    filenames = []
    for actual, name in zip(stages, expected):
        if not isinstance(actual, dict) or actual.get("file") != name + ".png":
            raise ValueError("Missing or out-of-order navigation capture")
        if actual.get("recognized_heading") != STAGES[name][2]:
            raise ValueError("Heading recognition does not match stage")
        filenames.append(actual["file"])
    if len(set(filenames)) != len(filenames):
        raise ValueError("Duplicate capture filename")
    if type(report.get("title_touch_verified")) is not bool:
        raise ValueError("Touch verification status must be explicit")
    if screenshot_dir is not None:
        directory = Path(screenshot_dir)
        font = font_rows()
        for name in expected:
            path = directory / (name + ".png")
            pixels, width, height = decode_native_capture(path)
            x, y, heading = STAGES[name]
            check_heading(pixels, width, height, x, y, heading, font)
    return {"stage_count": len(stages),
            "title_touch_verified": report["title_touch_verified"],
            "navigation_verified": True}


if __name__ == "__main__":
    import argparse
    import json
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("report", type=Path)
    p.add_argument("--screenshots", type=Path,
                   help="Require and recognize actual PNG pixels for every reported stage")
    args = p.parse_args()
    result = check_report(json.loads(args.report.read_text()), args.screenshots)
    print("PASS: %d ordered navigation captures; touch=%s" %
          (result["stage_count"], result["title_touch_verified"]))
