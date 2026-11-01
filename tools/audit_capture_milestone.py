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
    "scripts/melonds_smoke.sh": "real emulator navigation smoke",
    "tools/verify_melonds_navigation.py": "recognize native DS emulator frames",
    ".github/workflows/capture-host-acceptance.yml": "CI acceptance evidence",
    "docs/feature_parity.json": "feature parity tracking",
    "source/main.c": "real DS input and display integration",
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
        "capture_emulator_test_status": "not_run",
        "capture_emulator_evidence": None,
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

def audit_emulator_evidence(root, evidence_dir):
    """Only accept explicit end-to-end emulator evidence, not navigation screenshots."""
    evidence = pathlib.Path(evidence_dir).resolve()
    report = evidence / "capture-report.json"
    if not report.is_file():
        return {"status": "missing_report", "passed": False, "path": str(report)}
    try:
        payload = json.loads(report.read_text())
    except (OSError, ValueError) as exc:
        return {"status": "invalid_report", "passed": False, "error": str(exc)}
    # Require each independently verified stage and the actual emulator source.
    required = ("cloud_search", "cloud_shot", "orb_collected",
                "sphere_encounter", "capture_reward", "results",
                "resume_radar", "save", "restart", "restored_reward")
    valid = (isinstance(payload, dict) and
             payload.get("emulator") == "melonDS" and
             payload.get("test_kind") == "live_emulator_capture" and
             isinstance(payload.get("stages"), dict) and
             all(payload["stages"].get(stage) is True for stage in required))
    return {"status": "passed" if valid else "incomplete",
            "passed": bool(valid), "path": str(report),
            "required_stages": list(required)}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("repository", nargs="?", default=".")
    parser.add_argument("--run-host", action="store_true",
                        help="Run make test-host test-syntax (up to 5 minutes)")
    parser.add_argument("--emulator-evidence", metavar="DIR",
                        help="Inspect a live emulator capture-report.json; navigation alone is insufficient")
    args = parser.parse_args()
    result = audit(args.repository, args.run_host)
    if args.emulator_evidence:
        evidence = audit_emulator_evidence(args.repository, args.emulator_evidence)
        result["capture_emulator_test_passed"] = evidence["passed"]
        result["capture_emulator_test_status"] = evidence["status"]
        result["capture_emulator_evidence"] = evidence
    print(json.dumps(result, indent=2))
    if not result["prerequisites_present"]:
        return 2
    if args.run_host and result["host_tests"] != "passed":
        return 1
    if args.emulator_evidence and not result["capture_emulator_test_passed"]:
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())
