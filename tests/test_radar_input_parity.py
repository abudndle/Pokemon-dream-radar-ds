#!/usr/bin/env python3
"""Regression guard: radar/encounter A fires only after release-to-arm."""
from pathlib import Path
import re

root = Path(__file__).resolve().parents[1]
source = (root / "source/main.c").read_text()
block = source.split("if(game.screen==STATE_RADAR || game.screen==STATE_SPHERE){", 1)[1].split("if(game.screen==STATE_INTRO){", 1)[0]
assert "dr_search_fire_gate((keys&KEY_A)!=0,&radar_fire_armed)" in block, "Radar A firing must remain release-to-arm"
assert "game.save.frames_played%5==0" in block, "Radar firing cadence must remain unchanged"
sphere_marker = "} else if(game.screen==STATE_SPHERE)"
sphere_branch = block.split(sphere_marker, 1)[1] if sphere_marker in block else ""
assert "dr_sphere_fire_repeat((keys&KEY_A)!=0,(down&KEY_A)!=0," in sphere_branch, "Sphere must sustain capture beam on held A"
assert "game.save.frames_played))game_fire(&game);" in sphere_branch, "Sphere beam must use ordinary game_fire"
compat = (root / "source/platform_compat.c").read_text()
assert "return a_pressed || (a_held && frames_played%3u==0u);" in compat, "Sphere beam must fire on edge and held cadence"
assert "game.save.frames_played%5==0" not in sphere_branch, "Sphere capture must not wait for the radar's five-frame cadence"
assert block.count("game_fire(&game)") == 2, "Expected separate radar and immediate sphere firing paths"
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
print("PASS: release-armed radar and sustained sphere beam with emulator shot coverage")
