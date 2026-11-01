#!/usr/bin/env python3
"""Regression guard: A fires the beam on both radar and encounter screens."""
from pathlib import Path
import re

root = Path(__file__).resolve().parents[1]
source = (root / "source/main.c").read_text()
block = source.split("if(game.screen==STATE_RADAR || game.screen==STATE_SPHERE){", 1)[1].split("if(game.screen==STATE_INTRO){", 1)[0]
assert re.search(r"if\s*\(\s*\(keys\s*&\s*KEY_A\)\s*&&\s*\(game\.save\.frames_played\s*%\s*5\s*==\s*0\)\s*\)\s*game_fire\s*\(\s*&game\s*\)", block), "Shared radar/encounter A-button beam firing missing"
assert block.count("game_fire(&game)") == 1, "Unexpected additional firing path"
assert "game.screen==STATE_SPHERE && (keys&KEY_A)" not in block, "Encounter-only A-button gate reintroduced"
smoke = (root / "scripts/melonds_smoke.sh").read_text()
radar = smoke.split("snapshot 05-radar", 1)[1].split("snapshot 06-results", 1)[0]
assert "press_ds_key z" in radar, "Emulator smoke test must fire A during radar"
assert "snapshot 05-radar-after-shot" in radar, "Emulator must capture post-shot evidence"
assert radar.index("press_ds_key z") < radar.index("snapshot 05-radar-after-shot"), "Screenshot must follow A shot"
assert radar.index("snapshot 05-radar-after-shot") < radar.index("press_ds_key x"), "Shot must precede radar exit"
print("PASS: A-button beam firing available in radar and sphere; emulator shot coverage present")
