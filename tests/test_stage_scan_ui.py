#!/usr/bin/env python3
"""Validate the original ScanList adaptation and synthetic private CLPA motion."""
import copy
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tools"))
from stage_title_ui import stage
from stage_scan_ui import SCAN_LAYOUT, SCAN_Y_OFFSET

def pane(name,children=(),*,x=0,y=0,size=(30,40),alpha=255,flags=3):
    return dict(name=name,type="pan1",origin=4,flags=flags,alpha=alpha,
                translation=[float(x),float(y),0.0],rotation=[0.0,0.0,0.0],
                scale=[1.0,1.0],size=list(size),children=list(children))
rows=[]
for i,y in enumerate((157,117,77,37)):
    rows.append(pane(f"L{i:02d}",[
        pane(f"List{i:02d}",[
            pane(f"Touch{i:02d}",size=(300,36),flags=1)
        ],size=(300,38),flags=1)
    ],y=y,alpha=0))
snapshot={"layouts":[dict(file=SCAN_LAYOUT,panes=[
    pane("RootPane",[
        pane("Pos",[
            pane("SRT01",[pane("NotAHitbox")]),
            pane("SRT00",rows,x=-5)
        ])
    ],size=(320,240),flags=1)
])]}
private_clip={"frames":12,"loops":False,"tracks":[{
    "pane":"L00","property":"translate_y","curve":2,"keys":[
      {"frame":0.0,"value":157.0,"slope":0.0},
      {"frame":5.0,"value":163.0,"slope":0.0},
      {"frame":10.0,"value":169.0,"slope":0.0}
    ]}]}
with tempfile.TemporaryDirectory() as d:
    tmp=Path(d)
    public=stage(snapshot,offset_y=SCAN_Y_OFFSET,layout_name=SCAN_LAYOUT)
    moving=stage(snapshot,[private_clip],offset_y=SCAN_Y_OFFSET,layout_name=SCAN_LAYOUT)
    (tmp/"public.drui").write_bytes(public)
    (tmp/"private.drui").write_bytes(moving)
    (tmp/"corrupt.drui").write_bytes(public[:-1])
    subprocess.run([str(ROOT/"build/test_scan_ui_scene"),str(tmp/"public.drui"),
                    str(tmp/"private.drui"),str(tmp/"corrupt.drui")],check=True)
    # The real recovered metadata must stage to exactly the same four-row
    # hierarchy and valid native DS menu coordinates without any 3DS payload.
    source=json.loads((ROOT/"ui_mapping/original_pane_geometry.json").read_text())
    original=stage(source,offset_y=SCAN_Y_OFFSET,layout_name=SCAN_LAYOUT)
    (tmp/"original.drui").write_bytes(original)
    subprocess.run([str(ROOT/"build/test_scan_ui_scene"),str(tmp/"original.drui"),
                    str(tmp/"private.drui"),str(tmp/"corrupt.drui")],check=True)
    malformed=copy.deepcopy(snapshot)
    del malformed["layouts"][0]["panes"][0]["children"][0]["children"][1]["children"][3]["children"][0]["children"][0]
    try:stage(malformed,offset_y=SCAN_Y_OFFSET,layout_name=SCAN_LAYOUT)
    except ValueError:pass
    else:raise AssertionError("missing Touch03 accepted")
    for broken in [
      {"frames":12,"tracks":[{"pane":"L00","property":"translate_y","curve":2,"keys":[
        {"frame":1,"value":157,"slope":0},{"frame":0,"value":160,"slope":0}]}]},
      {"frames":12,"tracks":[{"pane":"L00","property":"translate_y","curve":2,"keys":[
        {"frame":0,"value":math.inf,"slope":0}]}]}
    ]:
        try:stage(snapshot,[broken],offset_y=SCAN_Y_OFFSET,layout_name=SCAN_LAYOUT)
        except ValueError:pass
        else:raise AssertionError("invalid CLPA keys accepted")
    (tmp/"scan.json").write_text(json.dumps(snapshot))
    (tmp/"clip.json").write_text(json.dumps(private_clip))
    subprocess.run([sys.executable,str(ROOT/"tools/stage_scan_ui.py"),
                    str(tmp/"scan.json"),str(tmp/"staged.drui")],check=True)
    assert (tmp/"staged.drui").read_bytes()==public
    # Never write private proprietary CLPA to public NitroFS, even if requested.
    result=subprocess.run([sys.executable,str(ROOT/"tools/stage_scan_ui.py"),
        str(tmp/"scan.json"),str(ROOT/"nitrofs/scan.drui"),
        "--clip-json",str(tmp/"clip.json")],capture_output=True,text=True)
    assert result.returncode!=0 and "private" in result.stderr
print("PASS: original ScanList recovered geometry, CLPA motion, private-file gating, malformed rollback")
