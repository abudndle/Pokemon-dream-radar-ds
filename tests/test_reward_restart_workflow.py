#!/usr/bin/env python3
"""Require screenshot-backed reward restart to remain wired into melonDS CI."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
script = (ROOT / "scripts/melonds_smoke.sh").read_text()
workflow = (ROOT / ".github/workflows/melonds-smoke.yml").read_text()

assert 'if [[ "${REQUIRE_PREEXISTING_REWARD:-0}" == 1 ]]; then' in script
assert '--observe-reward-screenshot "$out/01-title.png"' in script
assert 'cp "$out/01-title.png" "$out/03-restored-capture-reward.png"' in script
assert 'exit 0' in script[script.index('if [[ "${REQUIRE_PREEXISTING_REWARD:-0}"'):script.index('if [[ "${REQUIRE_PREEXISTING_ORB:-0}"')]
preserve = script.index('if [[ -f "$out/05-capture-reward.png" ]]; then', script.index('# A verified reward must remain'))
leave = script.index('press_ds_key x\nsnapshot 07-lab-return', preserve)
assert preserve < leave
assert 'snapshot 06-results-preserved' in script[preserve:leave]
assert 'if original != visible:' in script[preserve:leave]
assert 'raise SystemExit("Results reward changed before save/restart")' in script[preserve:leave]
assert 'exit 0' in script[preserve:leave]
assert 'REQUIRE_ORB_COLLECTION:-0' in script[preserve:leave]
assert 'REQUIRE_TOUCH:-0' in script[preserve:leave]
# Strict manual AND daily scheduled capture must run a second process,
# not accept a Results screenshot alone.
strict = workflow.index('if [[ "$REQUIRE_CAPTURE" == 1 ]]; then')
optional = workflow.index('elif [[ "${{ inputs.require_restart_persistence && \'1\' || \'0\' }}" != 1', strict)
strict_block = workflow[strict:optional]
assert "cron: '17 3 * * *'" in workflow
assert "REQUIRE_CAPTURE: ${{ (github.event_name == 'schedule' || inputs.require_capture) && '1' || '0' }}" in workflow
assert "github.event_name != 'workflow_dispatch' && github.event_name != 'schedule'" in workflow
assert "(github.event_name == 'workflow_dispatch' || github.event_name == 'schedule') && github.run_id" in workflow
assert workflow.index("REQUIRE_CAPTURE: ${{") < workflow.index("Launch melonDS and capture actual emulator window")
assert 'REQUIRE_PREEXISTING_REWARD=1' in strict_block
assert 'tools/verify_melonds_reward_restart.py' in strict_block
assert 'melonds-results/06-results-preserved.png' in strict_block
assert 'melonds-dldi/saves/dream_radar.dreamradar.sav' in strict_block
assert 'REQUIRE_PREEXISTING_REWARD=1' in workflow
assert 'tools/verify_melonds_reward_restart.py' in workflow
assert 'tests/test_melonds_reward_restart.py' in workflow
assert 'melonds-results/05-capture-reward.png' in workflow
assert 'melonds-results/sphere-reward.json' in workflow
assert 'reward-restart-report.txt' in workflow
assert 'elif [[ "${{ inputs.require_restart_persistence' in workflow
print("PASS: actual capture preserves Results and automatically checks exact reward in a fresh melonDS process")
