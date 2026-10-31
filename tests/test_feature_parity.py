#!/usr/bin/env python3
"""Prevent a passing ROM build from being confused with 3DS feature parity."""
import json
from pathlib import Path

root=Path(__file__).resolve().parents[1]
report=json.loads((root/"docs/feature_parity.json").read_text(encoding="utf-8"))
features=report["features"]
assert len(features)>=30, "Original gameplay coverage categories were accidentally dropped"
statuses={"host_tested","partial","investigation_only",
          "unimplemented","hardware_limited","unverified"}
assert len({entry["id"] for entry in features})==len(features)
for entry in features:
    assert entry["status"] in statuses and entry["gap"].strip()
    assert entry["feature"].strip() and entry["id"].strip()
    for path in entry["evidence"]:
        assert (root/path).is_file(), f"Missing source evidence: {path}"

by_id={entry["id"]:entry for entry in features}
for key in ("black2_white2_transfer","unova_link_receive","hidden_abilities",
            "orb_colors","color_encounter_bias","sphere_projectiles",
            "legendary_transfer_priority"):
    assert by_id[key]["status"]=="unimplemented"
assert by_id["original_gyro_motion"]["status"]=="hardware_limited"
assert by_id["original_stereo3d"]["status"]=="hardware_limited"
assert by_id["bclan_keyframes"]["status"]=="investigation_only"
assert by_id["bclyt_layouts"]["status"]=="investigation_only"
assert by_id["device_and_emulator_tests"]["status"]=="unverified"
assert by_id["retrieval_dowsing"]["status"]=="host_tested"
assert by_id["simulator_item_rewards"]["status"]=="host_tested"

game=(root/"source/game.c").read_text(encoding="utf-8")
main=(root/"source/main.c").read_text(encoding="utf-8")
assert "case EXT_RETRIEVAL: return (rnd(g)%8u)==0u;" in game
assert "case EXT_DOWSING: return (rnd(g)%8u)<7u;" in game
assert "simulator_reward_item(g)" in game
assert "g->session_type==1 || is_simulator" in game
assert "Retail transfer not available." in main
assert "WARNING: not compatible with Unova Link" in game
pending=sum(entry["status"]!="host_tested" for entry in features)
assert pending>0, "No source-backed proof of complete feature parity"
print(f"PASS: {len(features)} feature coverage categories, {pending} remain partial/unimplemented/unverified")
