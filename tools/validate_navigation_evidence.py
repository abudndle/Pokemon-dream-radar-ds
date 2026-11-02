#!/usr/bin/env python3
"""Require complete, distinct, correctly ordered emulator navigation evidence."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from verify_melonds_navigation import STAGES


def check_report(report):
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
    return {"stage_count": len(stages),
            "title_touch_verified": report["title_touch_verified"],
            "navigation_verified": True}


if __name__ == "__main__":
    import argparse
    import json
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("report", type=Path)
    args = p.parse_args()
    result = check_report(json.loads(args.report.read_text()))
    print("PASS: %d ordered navigation captures; touch=%s" %
          (result["stage_count"], result["title_touch_verified"]))
