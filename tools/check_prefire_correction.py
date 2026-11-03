#!/usr/bin/env python3
"""Fail-closed validation of prefire no-shot correction evidence."""
import argparse
import json
import sys
from pathlib import Path

def decision(path, require_corrected=False):
    p = json.loads(Path(path).read_text())
    if not isinstance(p, dict):
        raise ValueError("inspection must be a JSON object")
    status, corrected, fired = (p.get(k) for k in ("status", "camera_correction_executed", "fire_executed"))
    if status != "unaligned" or type(corrected) is not bool or fired is not False:
        raise ValueError(f"unsafe prefire correction in {path}: status={status!r}, camera_correction_executed={corrected!r}, fire_executed={fired!r}")
    if require_corrected and not corrected:
        raise ValueError(f"expected an executed no-fire camera correction in {path}")
    return "yes" if corrected else "no"

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inspection", type=Path)
    parser.add_argument("--require-corrected", action="store_true")
    args = parser.parse_args()
    try:
        print(decision(args.inspection, args.require_corrected))
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
