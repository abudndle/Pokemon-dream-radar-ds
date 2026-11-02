#!/usr/bin/env python3
"""Fail-closed prefire alignment check for a *fresh* melonDS sphere screenshot.

The caller must run plan_melonds_aim.py --target sphere on a screenshot taken
AFTER D-pad movement. A predicted target or stale earlier aim plan cannot
authorize firing. Alignment is not proof of a hit or captured reward.
"""
import argparse
import json
from pathlib import Path

RETICLE_X, RETICLE_Y = 128, 96
# The smallest runtime CaptureProfile hit radius is 16 (ERRATIC and
# LEGENDARY in source/game.c). game_fire uses a STRICT distance < radius,
# so 15 pixels is the largest integer-safe screenshot gate across classes.
# This expands the former 13px window without changing gameplay hitboxes.
SAFE_RADIUS = 15


def evaluate(plan):
    if not isinstance(plan, dict):
        raise ValueError("Aim plan must be an object")
    if type(plan.get("candidate_spheres")) is not int or plan["candidate_spheres"] != 1:
        raise ValueError("Prefire requires one uniquely observed sphere")
    if "motion_prediction" in plan or "observed_displacement" in plan:
        raise ValueError("Predicted or temporal plans cannot authorize prefire")
    point, offset = plan.get("target_screen"), plan.get("offset")
    if not isinstance(point, dict) or not isinstance(offset, dict):
        raise ValueError("Missing observed sphere coordinates")
    x, y = point.get("x"), point.get("y")
    dx, dy = offset.get("x"), offset.get("y")
    if any(type(value) is not int for value in (x, y, dx, dy)):
        raise ValueError("Noninteger sphere coordinates")
    if not (0 <= x < 256 and 0 <= y < 192):
        raise ValueError("Sphere outside DS top screen")
    if (dx, dy) != (x - RETICLE_X, y - RETICLE_Y):
        raise ValueError("Sphere offset does not match the reticle")
    distance_sq = dx * dx + dy * dy
    return {
        "fire_authorized": distance_sq <= SAFE_RADIUS * SAFE_RADIUS,
        "observed_reticle_distance_squared": distance_sq,
        "safe_radius_pixels": SAFE_RADIUS,
        "observed_target_screen": {"x": x, "y": y},
        "limitations": "One fresh aligned screenshot permits a bounded shot, not a hit, capture or persistent reward.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("fresh_plan", type=Path)
    args = parser.parse_args()
    try:
        decision = evaluate(json.loads(args.fresh_plan.read_text()))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        parser.exit(1, f"Sphere prefire refused: {exc}\n")
    print(json.dumps(decision))


if __name__ == "__main__":
    main()
