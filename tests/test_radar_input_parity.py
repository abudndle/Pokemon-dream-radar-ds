#!/usr/bin/env python3
"""Regression guard: DS radar cannot fire through the A-button fallback.

This is a source-level contract, not proof of original 3DS input parity.
"""
from pathlib import Path
import re

root = Path(__file__).resolve().parents[1]
source = (root / "source/main.c").read_text()
block = source.split("if(game.screen==STATE_RADAR || game.screen==STATE_SPHERE){", 1)[1].split("if(game.screen==STATE_INTRO){", 1)[0]
assert re.search(r"if\s*\(\s*game\.screen\s*==\s*STATE_SPHERE\s*&&\s*\(keys\s*&\s*KEY_A\)", block), "Encounter-only fallback guard missing"
assert not re.search(r"if\s*\(\s*\(keys\s*&\s*KEY_A\)", block), "Ungated A-button firing found in radar"
smoke = (root / "scripts/melonds_smoke.sh").read_text()
radar = smoke.split("snapshot 05-radar", 1)[1].split("snapshot 06-results", 1)[0]
assert "press_ds_key z" not in radar, "Smoke test incorrectly presses A on radar"
print("PASS: radar A-button firing disabled; smoke navigation does not fake a shot")
