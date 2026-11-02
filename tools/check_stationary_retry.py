#!/usr/bin/env python3
"""Allow one *observation-only* stationary retry for a near-miss sphere.

A prior screenshot may justify taking another screenshot, NEVER firing.
Only the fresh frame inspector can authorize a subsequent A-button pulse.
"""
import argparse
import json
from pathlib import Path

from sphere_prefire_gate import RETICLE_X, RETICLE_Y, SAFE_RADIUS, evaluate

RETRY_RADIUS = 26


def should_retry(gate):
    if not isinstance(gate, dict):
        raise ValueError("Missing observed prefire decision")
    point = gate.get("observed_target_screen")
    if not isinstance(point, dict):
        raise ValueError("Missing observed target")
    x, y = point.get("x"), point.get("y")
    if type(x) is not int or type(y) is not int:
        raise ValueError("Invalid observed coordinates")
    expected = evaluate({
        "candidate_spheres": 1,
        "target_screen": {"x": x, "y": y},
        "offset": {"x": x - RETICLE_X, "y": y - RETICLE_Y},
    })
    if gate != expected:
        raise ValueError("Prefire decision disagrees with observed target")
    distance = expected["observed_reticle_distance_squared"]
    return SAFE_RADIUS * SAFE_RADIUS < distance <= RETRY_RADIUS * RETRY_RADIUS


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("prefire_gate", type=Path)
    args = parser.parse_args()
    try:
        decision = should_retry(json.loads(args.prefire_gate.read_text()))
    except (OSError, ValueError) as exc:
        parser.exit(2, f"Stationary retry refused: {exc}\n")
    print(json.dumps({
        "take_fresh_screenshot": decision,
        "fire_authorized": False,
        "limitations": "Near-miss is permission to observe again, not to fire.",
    }))
    return 0 if decision else 3


if __name__ == "__main__":
    raise SystemExit(main())
