#!/usr/bin/env python3
"""Synthetic fail-closed tests for the second-process Orb balance gate."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from check_restored_orbs import require_restored_orbs


assert require_restored_orbs({"saved_orbs": 2}, 2) == 2
assert require_restored_orbs({"saved_orbs": 2}) == 2
for observation, expected in (
    ({"saved_orbs": 1}, 2),     # A positive but stale balance is not persistence.
    ({"saved_orbs": 3}, 2),     # A larger unrelated balance is also not proof.
    ({"saved_orbs": 0}, 2),
    ({"saved_orbs": True}, 1),  # bool is an int subclass; reject it.
    ({"saved_orbs": 2.0}, 2),
    ({"saved_orbs": -1}, 2),
    ({"saved_orbs": 0x100000000}, 2),
    ({}, 2),
    ([], 2),
    ({"saved_orbs": 2}, True),
    ({"saved_orbs": 2}, 0),
    ({"saved_orbs": 2}, 0x100000000),
):
    try:
        require_restored_orbs(observation, expected)
    except ValueError:
        pass
    else:
        raise AssertionError(f"Accepted invalid restart balance: {observation!r} expected={expected!r}")

with tempfile.TemporaryDirectory() as temporary:
    observed = Path(temporary) / "restarted.json"
    observed.write_text(json.dumps({"saved_orbs": 2}))
    command = [sys.executable, str(ROOT / "tools/check_restored_orbs.py"), str(observed)]
    assert subprocess.run(command + ["--expected-balance", "2"],
                          capture_output=True, text=True).returncode == 0
    for value in ("1", "3", "0", "-1", "4294967296"):
        assert subprocess.run(command + ["--expected-balance", value],
                              capture_output=True, text=True).returncode != 0
    observed.write_text('{"saved_orbs": true}')
    assert subprocess.run(command + ["--expected-balance", "1"],
                          capture_output=True, text=True).returncode != 0

workflow = (ROOT / ".github/workflows/melonds-smoke.yml").read_text()
smoke = (ROOT / "scripts/melonds_smoke.sh").read_text()
assert 'EXPECTED_RESTORED_ORBS="$expected_orbs"' in workflow
assert '--expected-balance "$EXPECTED_RESTORED_ORBS"' in smoke
assert 'REQUIRE_PREEXISTING_ORB=1' in workflow
print("PASS: exact clean-restart Orb balance gate rejects stale, inflated and malformed evidence")
