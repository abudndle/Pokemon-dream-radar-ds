#!/usr/bin/env python3
"""Guard cancellation policy for expensive DS emulator/build workflows."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for filename in ("blocksds.yml", "emulator-smoke.yml",
                 "capture-host-acceptance.yml", "melonds-smoke.yml"):
    text = (ROOT / ".github/workflows" / filename).read_text()
    assert text.count("\nconcurrency:\n") == 1, filename
    assert "github.event.pull_request.number || github.ref" in text, filename
    assert "github.event_name == 'workflow_dispatch' && github.run_id" in text, filename
    assert "cancel-in-progress: ${{ github.event_name != 'workflow_dispatch' }}" in text, filename
print("PASS: long-running workflows cancel stale CI but preserve manual acceptance")
