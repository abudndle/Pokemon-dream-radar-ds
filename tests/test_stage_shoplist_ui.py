#!/usr/bin/env python3
"""Validate recovered 3DS ShopList rows against the existing bounded DRUI runtime."""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tools"))
from stage_title_ui import SHOP_TARGET,stage

metadata=ROOT/"ui_mapping/original_pane_geometry.json"
snapshot=json.loads(metadata.read_text(encoding="utf-8"))
base=stage(snapshot,target=SHOP_TARGET)
assert base[:4]==b"DRUI"
# This is a synthetic, non-proprietary CLPA track; no original keyframes
# are checked into the public repository.
clip={"frames":12,"loops":False,"tracks":[
    {"pane":"L00","property":"translate_y","curve":0,"keys":[
        {"frame":0,"value":157,"slope":0},
        {"frame":10,"value":167,"slope":0}
    ]}
]}
animated=stage(snapshot,[clip],target=SHOP_TARGET)
with tempfile.TemporaryDirectory() as d:
    root=Path(d)
    files=[root/x for x in ("shoplist.drui","moving.drui","truncated.drui")]
    for path,data in zip(files,(base,animated,base[:-1])):
        path.write_bytes(data)
    subprocess.run([str(ROOT/"build/test_scanlist_ui"),*(str(p) for p in files)],check=True)
    staged=root/"staged.drui"
    subprocess.run([sys.executable,str(ROOT/"tools/stage_title_ui.py"),
                   str(metadata),str(staged),"--layout",SHOP_TARGET],check=True)
    assert staged.read_bytes()==base
    (root/"private-clip.json").write_text(json.dumps(clip),encoding="utf-8")
    rejected=subprocess.run([sys.executable,str(ROOT/"tools/stage_title_ui.py"),
        str(metadata),str(ROOT/"nitrofs/shoplist.drui"),"--layout",SHOP_TARGET,
        "--clip-json",str(root/"private-clip.json")],capture_output=True,text=True)
    assert rejected.returncode!=0 and "outside the public checkout" in rejected.stderr
try:stage({"layouts":[]},target=SHOP_TARGET)
except ValueError:pass
else:raise AssertionError("missing original ShopList accepted")
renderer=(ROOT/"source/main.c").read_text()
assert 'shoplist_live_rects(shop_rows);' in renderer
assert 'dr_ui_title_hit(shop_rows,touch->px,touch->py)' in renderer
assert 'if(touched>=6)touched=-1;' in renderer
assert 'for(int slot=0;slot<4 && base+slot<6;slot++)' in renderer
print("PASS: original ShopList geometry, six rows through four-pane pages, private CLPA safety")
