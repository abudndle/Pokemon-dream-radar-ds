#!/usr/bin/env python3
"""Source-derived title BCLYT staging and deliberately synthetic CLPA tracks."""
import copy
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from stage_title_ui import stage

def pane(name, children=(), *, y=0, size=(30, 40), flags=3, alpha=255):
    return dict(name=name, type="pan1", origin=4, flags=flags, alpha=alpha,
                translation=[0.0, float(y), 0.0], rotation=[0.0, 0.0, 0.0],
                scale=[1.0, 1.0], size=list(size), children=list(children))

rows = [pane(f"L{i:02d}", [pane(f"List{i:02d}", [pane(f"Touch{i:02d}", size=(286, 34))], size=(290, 38))],
             y=130 - i * 40, alpha=0) for i in range(4)]
snapshot = {"layouts": [dict(file="MnIf_S_TitleList.bclyt", sections=17, panes=[
    pane("RootPane", [pane("Pos", [pane("SRT00", rows, y=16)])], size=(320, 240), flags=1)
])]}

def track(keys, *, name="L00", prop="translate_y", curve=2):
    return {"pane": name, "property": prop, "curve": curve,
            "keys": [dict(frame=f, value=v, slope=m) for f, v, m in keys]}

clip = {"frames": 12, "loops": False, "tracks": [track([
    (0, 130, 0), (5, 140, 0), (5, 145, 0), (10, 150, 0)])]}
with tempfile.TemporaryDirectory() as d:
    root = Path(d)
    base = stage(snapshot)
    moving = stage(snapshot, [clip])
    assert base[:4] == moving[:4] == b"DRUI"
    (root / "base.drui").write_bytes(base)
    (root / "moving.drui").write_bytes(moving)
    (root / "bad.drui").write_bytes(base[:-1])
    subprocess.run([str(ROOT / "build/test_dr_ui_scene"), str(root / "base.drui"),
                    str(root / "moving.drui"), str(root / "bad.drui")], check=True)
    errors = []
    for broken in (
        {"frames": 12, "tracks": [track([(1, 130, 0), (0, 150, 0)])]},
        {"frames": 12, "tracks": [track([(0, 130, 0), (1, math.inf, 0)])]},
        {"frames": 12, "tracks": [track([(0, 130, 0)]), track([(0, 140, 0)])]},
        {"frames": 12, "tracks": [track([(0, 130, 0)], prop="unknown")]},
    ):
        try: stage(snapshot, [broken])
        except ValueError: errors.append(True)
        else: errors.append(False)
    assert all(errors)
    damaged = copy.deepcopy(snapshot)
    damaged["layouts"][0]["panes"][0]["children"][0]["children"][0]["children"].pop()
    try: stage(damaged)
    except ValueError: pass
    else: raise AssertionError("missing Touch03 accepted")

    source = ROOT / "ui_mapping/original_pane_geometry.json"
    if source.exists():
        public_snapshot = json.loads(source.read_text(encoding="utf-8"))
        first = stage(public_snapshot)
        assert len(first) == len(base)
        (root / "original-title.drui").write_bytes(first)
        subprocess.run([str(ROOT / "build/test_dr_ui_scene"),
                        str(root / "original-title.drui")], check=True)
print("PASS: source-derived title scene, synthetic BCLAN playback and bad asset rejection")
