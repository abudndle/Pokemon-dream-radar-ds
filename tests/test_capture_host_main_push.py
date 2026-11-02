#!/usr/bin/env python3
"""Keep capture acceptance active for each integrated main-branch revision.

The normal five-minute host workflow is useful but not a substitute for the
capture-specific evidence/audit job. This regression uses no Nintendo assets.
"""
from pathlib import Path
import re

root = Path(__file__).resolve().parents[1]
workflow = (root / ".github/workflows/capture-host-acceptance.yml").read_text()
trigger = re.search(r"(?ms)^on:\s*\n(.*?)(?=^[^\s#]|\Z)", workflow)
assert trigger, "Missing GitHub Actions event triggers"
events = trigger.group(1)
push = re.search(r"(?ms)^  push:\s*\n(.*?)(?=^  [a-z_]+:|\Z)", events)
assert push, "Capture acceptance must run on pushes"
branches = re.search(r"(?m)^    branches:\s*\[([^\]]+)\]", push.group(1))
assert branches, "Capture acceptance push branches must be explicit"
names = [item.strip().strip("'\\\"") for item in branches.group(1).split(",")]
assert "main" in names, "Every integrated main push must trigger capture acceptance"
assert re.search(r"(?m)^  pull_request:", events), "PR acceptance trigger missing"
assert re.search(r"(?m)^  workflow_dispatch:", events), "Manual acceptance trigger missing"
assert "python3 tools/audit_capture_milestone.py --run-host" in workflow
assert "capture-evidence/host-audit.json" in workflow
assert "actions/upload-artifact@v4" in workflow
assert "python3 tests/test_capture_emulator_evidence.py" in workflow
assert "python3 tests/test_capture_host_main_push.py" in workflow
print("PASS: capture-specific host evidence runs on main pushes, PRs and manual dispatch")
