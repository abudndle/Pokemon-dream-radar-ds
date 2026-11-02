#!/usr/bin/env python3
"""Gate a longer live sphere pursuit on independently observed meter progress.

This is a CI time-budget decision, not proof of a hit, capture or reward.
Malformed/absent evidence is an error, never permission to continue blindly.
"""
import argparse
import json
from pathlib import Path


def should_extend(report, threshold=24):
    if not isinstance(report, dict) or type(threshold) is not int or not 1 <= threshold <= 177:
        raise ValueError("Invalid capture extension request")
    peak = report.get("max_meter_pixels")
    samples = report.get("samples")
    width = report.get("meter_width_pixels")
    classes = report.get("capture_classes_observed")
    reward = report.get("reward_screen_observed")
    if (type(peak) is not int or type(samples) is not int or samples < 1
            or type(width) is not int or width != 177 or not 0 <= peak <= width
            or not isinstance(classes, list) or not classes
            or not all(x in {"drifting", "swift", "erratic", "legendary", "item"} for x in classes)
            or type(reward) is not bool):
        raise ValueError("Invalid screenshot-derived meter evidence")
    if reward:
        return False, "reward already observed; do not extend"
    if peak < threshold:
        return False, "insufficient observed meter progress for longer pursuit"
    return True, "observed progress warrants a bounded extension; no capture implied"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    args = parser.parse_args()
    try:
        report = json.loads(args.report.read_text())
        allowed, reason = should_extend(report)
    except (OSError, ValueError) as exc:
        parser.exit(2, f"Capture extension refused: {exc}\n")
    print(json.dumps({"extend": allowed, "reason": reason,
                      "limitations": "Meter progress does not prove a hit, capture, reward or restart persistence."}))
    return 0 if allowed else 3


if __name__ == "__main__":
    raise SystemExit(main())
