#!/usr/bin/env python3
"""Plan one conservative camera nudge for a lost, edge-clipped sphere.

This is navigation only: the beam must remain released until a fresh
screenshot independently recognizes the encounter artwork. Never infer a
capture, hit or reward from a prior plan.
"""
import argparse
import json
from pathlib import Path


def plan_edge_recovery(previous_plan):
    if not isinstance(previous_plan, dict):
        raise ValueError("Prior sphere plan must be an object")
    if previous_plan.get("candidate_spheres") != 1 or type(previous_plan.get("candidate_spheres")) is not int:
        raise ValueError("Recovery requires one previously recognized sphere")
    observed = previous_plan.get("observed_target_screen")
    if not isinstance(observed, dict):
        raise ValueError("Missing directly observed sphere coordinates")
    x, y = observed.get("x"), observed.get("y")
    if type(x) is not int or type(y) is not int or not (0 <= x < 256 and 0 <= y < 192):
        raise ValueError("Invalid observed DS top-screen coordinates")
    # Camera motion moves artwork in the opposite direction. The class HUD
    # obscures y~25..43. Never sweep blindly from a central last observation.
    if y <= 54:
        key, edge = "Up", "top"
    elif y >= 165:
        key, edge = "Down", "bottom"
    elif x <= 30:
        key, edge = "Left", "left"
    elif x >= 225:
        key, edge = "Right", "right"
    else:
        raise ValueError("No edge evidence: refusing blind camera sweep")
    return {"key": key, "seconds": 0.12, "edge": edge,
            "observed_target_screen": {"x": x, "y": y},
            "fire_authorized": False,
            "limitations": "Camera nudge only; require fresh unique sphere recognition before firing."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("previous_plan", type=Path)
    args = parser.parse_args()
    try:
        plan = plan_edge_recovery(json.loads(args.previous_plan.read_text()))
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        parser.exit(1, f"Sphere recovery refused: {exc}\n")
    print(json.dumps(plan))


if __name__ == "__main__":
    main()
