#!/usr/bin/env python3
"""Read-only capture milestone prerequisite audit. No ROM or proprietary assets."""
import argparse
import pathlib
import json
import sys

REQUIRED = {
    "source/game.c": "portable gameplay rules",
    "tests/test_radar_resume.c": "scan resume",
    "tests/test_dream_orb_entities.c": "orb collection",
    "tests/test_capture_profiles.c": "capture profile",
    "tests/test_gameplay_save_roundtrip.c": "save reload",
    "tests/test_melonds_navigation.py": "emulator navigation",
    "docs/feature_parity.json": "feature parity tracking",
}

def audit(root):
    root = pathlib.Path(root)
    checks = {p: {"exists": (root / p).is_file(), "purpose": why} for p, why in REQUIRED.items()}
    return {"checks": checks, "prerequisites_present": all(c["exists"] for c in checks.values()),
            "capture_emulator_test_passed": False,
            "note": "Presence checks do not run gameplay or establish emulator success."}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("repository", nargs="?", default=".")
    args = ap.parse_args()
    result = audit(args.repository)
    print(json.dumps(result, indent=2))
    return 0 if result["prerequisites_present"] else 2

if __name__ == "__main__":
    sys.exit(main())
