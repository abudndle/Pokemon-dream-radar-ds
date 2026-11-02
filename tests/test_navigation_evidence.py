#!/usr/bin/env python3
"""Synthetic report tests; never claim to be live emulator evidence."""
from pathlib import Path
import copy
import sys
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from validate_navigation_evidence import check_report
from verify_melonds_navigation import STAGES

base = {"kind": "melonds-native-ds-navigation",
        "title_touch_verified": False,
        "stages": [{"file": name + ".png", "recognized_heading": value[2]}
                   for name, value in STAGES.items()]}
assert check_report(base)["stage_count"] == 6
assert check_report(base)["title_touch_verified"] is False
for mutation in ("missing", "reorder", "heading", "touch", "kind", "duplicate"):
    bad = copy.deepcopy(base)
    if mutation == "missing":
        bad["stages"].pop()
    elif mutation == "reorder":
        bad["stages"][0], bad["stages"][1] = bad["stages"][1], bad["stages"][0]
    elif mutation == "heading":
        bad["stages"][3]["recognized_heading"] = "RESEARCH LAB"
    elif mutation == "touch":
        bad["title_touch_verified"] = "false"
    elif mutation == "kind":
        bad["kind"] = "synthetic"
    else:
        bad["stages"][1]["file"] = bad["stages"][0]["file"]
    try:
        check_report(bad)
    except ValueError:
        pass
    else:
        raise AssertionError("Invalid evidence accepted: " + mutation)
# The live screenshot path must inspect all six frames, not merely trust JSON.
# Mocks avoid claiming synthetic test images are actual melonDS screenshots.
with patch("validate_navigation_evidence.font_rows", return_value=[0] * 768), \
     patch("validate_navigation_evidence.decode_native_capture",
           return_value=(bytes(256 * 384 * 3), 256, 384)) as decode, \
     patch("validate_navigation_evidence.check_heading") as heading:
    assert check_report(base, "/synthetic")["navigation_verified"]
    assert decode.call_count == len(STAGES)
    assert heading.call_count == len(STAGES)

with patch("validate_navigation_evidence.font_rows", return_value=[0] * 768), \
     patch("validate_navigation_evidence.decode_native_capture",
           side_effect=ValueError("bad image dimensions")):
    try:
        check_report(base, "/synthetic")
    except ValueError:
        pass
    else:
        raise AssertionError("Corrupt screenshot accepted")

with patch("validate_navigation_evidence.font_rows", return_value=[0] * 768), \
     patch("validate_navigation_evidence.decode_native_capture",
           return_value=(bytes(256 * 384 * 3), 256, 384)), \
     patch("validate_navigation_evidence.check_heading",
           side_effect=ValueError("heading mismatch")):
    try:
        check_report(base, "/synthetic")
    except ValueError:
        pass
    else:
        raise AssertionError("Unrecognized screenshot accepted")
print("PASS: ordered navigation evidence, PNG validation and negative controls")
