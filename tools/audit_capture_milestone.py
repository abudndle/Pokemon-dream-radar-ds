#!/usr/bin/env python3
"""Audit and optionally execute Dream Radar capture milestone host checks.

No private Nintendo assets are required. This is NOT an emulator acceptance test.
"""
import argparse
import json
import pathlib
import subprocess
import sys

REQUIRED = {
    "source/game.c": "portable gameplay rules",
    "tests/test_radar_resume.c": "scan resume",
    "tests/test_capture_milestone_end_to_end.c": "complete capture and persistent reward acceptance",
    "tests/test_dream_orb_entities.c": "orb collection",
    "tests/test_capture_profiles.c": "capture profile",
    "tests/test_gameplay_save_roundtrip.c": "save reload",
    "tests/test_melonds_navigation.py": "screenshot heading recognition",
    ".github/workflows/capture-host-acceptance.yml": "CI acceptance evidence",
    "docs/feature_parity.json": "feature parity tracking",
}

def audit(root, run_host=False):
    root = pathlib.Path(root).resolve()
    checks = {p: {"exists": (root / p).is_file(), "purpose": why}
              for p, why in REQUIRED.items()}
    present = all(item["exists"] for item in checks.values())
    result = {
        "checks": checks,
        "prerequisites_present": present,
        "host_tests": "not_run",
        "capture_emulator_test_passed": False,
        "note": "Host tests and screenshot-recognition tests cannot establish live emulator gameplay.",
    }
    if run_host:
        if not present:
            result["host_tests"] = "blocked_missing_prerequisites"
        else:
            try:
                proc = subprocess.run(
                    ["make", "test-host", "test-syntax"], cwd=root,
                    capture_output=True, text=True, timeout=300, check=False)
                result["host_tests"] = "passed" if proc.returncode == 0 else "failed"
                result["host_returncode"] = proc.returncode
                result["host_output_tail"] = (proc.stdout + proc.stderr)[-6000:]
            except (OSError, subprocess.TimeoutExpired) as exc:
                result["host_tests"] = "error"
                result["host_error"] = str(exc)
    return result

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("repository", nargs="?", default=".")
    parser.add_argument("--run-host", action="store_true",
                        help="Run make test-host test-syntax (up to 5 minutes)")
    args = parser.parse_args()
    result = audit(args.repository, args.run_host)
    print(json.dumps(result, indent=2))
    if not result["prerequisites_present"]:
        return 2
    if args.run_host and result["host_tests"] != "passed":
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())
