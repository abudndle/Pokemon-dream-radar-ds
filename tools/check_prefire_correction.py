#!/usr/bin/env python3
"""Fail-closed validation of prefire no-shot correction evidence."""
import argparse
import json
import sys
from pathlib import Path

def decision(path, require_corrected=False, aim_path=None, max_distance=None):
    p = json.loads(Path(path).read_text())
    if not isinstance(p, dict):
        raise ValueError("inspection must be a JSON object")
    status, corrected, fired = (p.get(k) for k in ("status", "camera_correction_executed", "fire_executed"))
    if status != "unaligned" or type(corrected) is not bool or fired is not False:
        raise ValueError(f"unsafe prefire correction in {path}: status={status!r}, camera_correction_executed={corrected!r}, fire_executed={fired!r}")
    if require_corrected and not corrected:
        raise ValueError(f"expected an executed no-fire camera correction in {path}")
    if not corrected and aim_path is not None:
        aim = json.loads(Path(aim_path).read_text())
        offset = aim.get("offset") if isinstance(aim, dict) else None
        if not isinstance(offset, dict) or type(offset.get("x")) is not int or type(offset.get("y")) is not int:
            raise ValueError("near-miss aim must contain integer observed offsets")
        if type(max_distance) is not int or not 0 <= max_distance <= 256:
            raise ValueError("invalid maximum no-chase distance")
        if offset["x"] ** 2 + offset["y"] ** 2 > max_distance ** 2:
            raise ValueError("observed residual exceeds no-chase radius")
    elif not corrected and max_distance is not None:
        raise ValueError("near-miss radius requires an aim observation")
    return "yes" if corrected else "no"

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inspection", type=Path)
    parser.add_argument("--require-corrected", action="store_true")
    parser.add_argument("--allow-near-miss", action="store_true",
                        help="Accept a no-correction result only with a fresh aim JSON inside the stated radius")
    parser.add_argument("--aim", type=Path)
    parser.add_argument("--max-distance", type=int)
    args = parser.parse_args()
    try:
        if args.allow_near_miss:
            if args.require_corrected or args.aim is None or args.max_distance is None:
                raise ValueError("--allow-near-miss requires --aim and --max-distance, not --require-corrected")
            print(decision(args.inspection, aim_path=args.aim, max_distance=args.max_distance))
        else:
            if args.aim is not None or args.max_distance is not None:
                raise ValueError("--aim/--max-distance require --allow-near-miss")
            print(decision(args.inspection, args.require_corrected))
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
