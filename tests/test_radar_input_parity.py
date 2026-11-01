#!/usr/bin/env python3
"""Regression guard: radar/encounter A fires only after release-to-arm."""
from pathlib import Path
import re

root = Path(__file__).resolve().parents[1]
source = (root / "source/main.c").read_text()
block = source.split("if(game.screen==STATE_RADAR || game.screen==STATE_SPHERE){", 1)[1].split("if(game.screen==STATE_INTRO){", 1)[0]
assert re.search(r"if\s*\(\s*dr_search_fire_gate\s*\(\s*\(keys\s*&\s*KEY_A\)\s*!=\s*0\s*,\s*&radar_fire_armed\s*\)\s*&&\s*\(game\.save\.frames_played\s*%\s*5\s*==\s*0\)\s*\)\s*game_fire\s*\(\s*&game\s*\)", block), "Shared radar/encounter A-button beam firing must require release-to-arm"
assert block.count("game_fire(&game)") == 1, "Unexpected additional firing path"
assert "if(next==STATE_RADAR || next==STATE_SPHERE)radar_fire_armed=0;" in source, "Transition must disarm fire until A release"
assert "radar_fire_armed=0;" in source.split("static void from_results(", 1)[1].split("static void handle_key(", 1)[0], "Resuming the radar must disarm fire"
assert "save_photo(" not in block, "Radar/encounter input must not capture photos"
assert "dr_photo_shortcut(" not in block, "Photo shortcut must not run during radar/encounter"
assert "game.screen==STATE_SPHERE && (keys&KEY_A)" not in block, "Encounter-only A-button gate reintroduced"
smoke = (root / "scripts/melonds_smoke.sh").read_text()
radar = smoke.split("snapshot 05-radar", 1)[1].split("snapshot 06-results", 1)[0]
assert "press_ds_key z" in radar, "Emulator smoke test must fire A during radar"
assert "snapshot 05-radar-after-shot" not in radar, "Firing must not trigger a post-shot screenshot"
assert radar.index("press_ds_key z") < radar.index("press_ds_key x"), "Shot must precede radar exit"
print("PASS: release-armed A-button beam in radar/sphere; emulator shot coverage without a post-shot screenshot")
