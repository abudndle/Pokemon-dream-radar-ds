"""Regression tests for the strict emulator milestone evidence gate."""
import json
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from audit_capture_milestone import audit_emulator_evidence

REQUIRED = (
    "cloud_search", "cloud_shot", "orb_collected", "sphere_encounter",
    "capture_reward", "results", "resume_radar", "save", "restart",
    "restored_reward",
)

with tempfile.TemporaryDirectory() as temp:
    root = Path(temp)
    report = root / "capture-report.json"
    assert audit_emulator_evidence(root, root)["status"] == "missing_report"
    report.write_text("{broken json")
    assert audit_emulator_evidence(root, root)["status"] == "invalid_report"
    good = {"emulator": "melonDS", "test_kind": "live_emulator_capture",
            "stages": {stage: True for stage in REQUIRED}}
    report.write_text(json.dumps(good))
    assert audit_emulator_evidence(root, root)["passed"]
    for stage in REQUIRED:
        invalid = json.loads(json.dumps(good))
        invalid["stages"][stage] = False
        report.write_text(json.dumps(invalid))
        assert not audit_emulator_evidence(root, root)["passed"], stage
        del invalid["stages"][stage]
        report.write_text(json.dumps(invalid))
        assert not audit_emulator_evidence(root, root)["passed"], stage
    for key, bad in (("emulator", "other"), ("test_kind", "navigation")):
        invalid = json.loads(json.dumps(good))
        invalid[key] = bad
        report.write_text(json.dumps(invalid))
        assert not audit_emulator_evidence(root, root)["passed"], key
    invalid = json.loads(json.dumps(good))
    invalid["stages"]["save"] = 1
    report.write_text(json.dumps(invalid))
    assert not audit_emulator_evidence(root, root)["passed"], "numeric truthiness must not pass"
print("PASS: missing, malformed, partial and fabricated stage evidence rejected")
