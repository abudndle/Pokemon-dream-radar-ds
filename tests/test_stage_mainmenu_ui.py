#!/usr/bin/env python3
"""Source-derived 3DS Research Lab four-row menu staging and clip tests."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tools"))
from stage_title_ui import stage, MAINMENU_TARGET

source=ROOT/"ui_mapping/original_pane_geometry.json"
snapshot=json.loads(source.read_text(encoding="utf-8"))
public=stage(snapshot,target=MAINMENU_TARGET,offset_y=24)
assert public[:4]==b"DRUI"
clip={"frames":12,"loops":False,"tracks":[{
    "pane":"L03","property":"translate_y","curve":0,
    "keys":[
      {"frame":0,"value":-10,"slope":0},
      {"frame":10,"value":-20,"slope":0}
    ]}]}
animated=stage(snapshot,[clip],target=MAINMENU_TARGET,offset_y=24)
assert len(animated)>len(public)
with tempfile.TemporaryDirectory() as d:
    root=Path(d)
    paths=[root/x for x in ("mainmenu.drui","moving.drui","corrupt.drui")]
    paths[0].write_bytes(public)
    paths[1].write_bytes(animated)
    paths[2].write_bytes(public[:-1])
    subprocess.run([str(ROOT/"build/test_mainmenu_ui"),*(str(x) for x in paths)],
                   check=True)
    result=subprocess.run([sys.executable,str(ROOT/"tools/stage_title_ui.py"),
                           str(source),str(root/"cli.drui"),
                           "--layout",MAINMENU_TARGET,"--offset-y","24"],
                          capture_output=True,text=True)
    assert result.returncode==0,result.stderr
    assert (root/"cli.drui").read_bytes()==public
    clipfile=root/"clip.json"
    clipfile.write_text(json.dumps(clip))
    denied=subprocess.run([sys.executable,str(ROOT/"tools/stage_title_ui.py"),
                           str(source),str(ROOT/"nitrofs/mainmenu.drui"),
                           "--layout",MAINMENU_TARGET,"--offset-y","24",
                           "--clip-json",str(clipfile)],
                          capture_output=True,text=True)
    assert denied.returncode!=0 and "outside the public checkout" in denied.stderr
try:stage({"layouts":[]},target=MAINMENU_TARGET,offset_y=24)
except ValueError:pass
else:raise AssertionError("missing original MainMenuList accepted")
try:stage(snapshot,target="unverified.bclyt",offset_y=24)
except ValueError:pass
else:raise AssertionError("unsupported original layout accepted")
print("PASS: recovered MainMenuList, source pane bounds, private CLPA and rejected malformed inputs")
