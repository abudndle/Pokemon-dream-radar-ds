"""Synthetic-only tests for private BCLAN-to-DS title CLPA compilation."""
import copy
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from stage_title_clpa import stage

def keys(values):
    return [{"frame":frame,"value":value,"slope":0.0}
            for frame,value in values]
source={
    "frames":10,"loops":False,
    "tracks":[
        {"pane":"L00","property":"translate_y","curve":2,
         "keys":keys([(0,130),(10,110)])},
        {"pane":"Touch01","property":"scale_x","curve":1,
         "keys":keys([(0,1),(5,1.25),(10,1)])},
        {"pane":"SRT00","property":"translate_x","curve":2,
         "keys":keys([(0,0),(10,5)])},
        {"pane":"UnrelatedMaterial","property":"rotate_z","curve":2,
         "keys":keys([(0,1),(10,2)])},
    ],
}
generated,count,key_count=stage(source)
assert count==3 and key_count==7
assert "dr_private_title_animation" in generated
assert "{1,1,2,2,dr_private_keys_0}" in generated
assert "{2,6,1,3,dr_private_keys_1}" in generated
assert "{0,0,2,2,dr_private_keys_2}" in generated
assert "-116.8f" in generated and "-100.8f" in generated
assert "132.0f" in generated
assert "UnrelatedMaterial" not in generated
assert "0f," not in generated and "5f," not in generated
with tempfile.TemporaryDirectory() as directory:
    root=Path(directory)
    src=root/"clip.json"
    out=root/"private_title_clpa.h"
    src.write_text(json.dumps(source),encoding="utf-8")
    command=[sys.executable,str(Path(__file__).resolve().parents[1]/
            "tools/stage_title_clpa.py"),str(src),str(out)]
    subprocess.run(command,check=True,capture_output=True,text=True)
    assert out.read_text(encoding="utf-8")==generated
    existing=src.read_bytes()
    same=subprocess.run(command[:-1]+[str(src)],capture_output=True)
    assert same.returncode and src.read_bytes()==existing

for bad in (
    {**source,"frames":math.nan},
    {**source,"loops":1},
    {**source,"tracks":[]},
    {**source,"tracks":source["tracks"]+[copy.deepcopy(source["tracks"][0])]},
    {**source,"tracks":[{**source["tracks"][0],"curve":99}]},
    {**source,"tracks":[{**source["tracks"][0],
        "keys":keys([(5,1),(4,2)])}]},
    {**source,"tracks":[{**source["tracks"][0],
        "keys":keys([(0,0)]*1025)}]},
):
    try:
        stage(bad)
    except (ValueError,TypeError):
        pass
    else:
        raise AssertionError("malformed private BCLAN input was accepted")
print("PASS: original title clip retargeting, privacy, budget and malformed input checks")
