import json
import copy
import math
import sys
import pathlib
import subprocess
import tempfile

root=pathlib.Path(__file__).resolve().parents[1]
source=root/"ui_mapping/original_pane_geometry.json"
with tempfile.TemporaryDirectory() as d:
    output=pathlib.Path(d)/"retarget.json"
    subprocess.run(["python3",str(root/"tools/retarget_panes.py"),str(source),str(output)],check=True)
    data=json.loads(output.read_text())
    assert len(data["layouts"])==22
    for layout in data["layouts"]:
        assert layout["target_size"]==[256,192]
        assert pathlib.Path(layout["source_path"]).name==layout["source"]
        w,h=layout["source_size"]
        assert layout["scale"]==[256/w,192/h]
        def verify(p):
            assert isinstance(p["flags"],int) and 0<=p["flags"]<=255
            assert isinstance(p["origin"],int) and 0<=p["origin"]<=255
            assert isinstance(p["alpha"],int) and 0<=p["alpha"]<=255
            assert len(p["rotation"])==3 and len(p["scale"])==2
            assert isinstance(p["translation_z"],(int,float))
            assert len(p["world_translation_ds"])==2
            assert len(p["world_scale"])==2
            assert len(p["world_size_ds"])==2
            assert 0<=p["effective_alpha"]<=255
            assert isinstance(p["flag_visible"],bool)
            assert not p["effective_visible"] or (p["flag_visible"] and p["visible_in_viewport"] and p["effective_alpha"]>0)
            assert 0<=p["viewport_coverage"]<=1
            assert isinstance(p["visible_in_viewport"],bool)
            if p["clipped_bounds_ds"] is not None:
                a,b,c,d=p["clipped_bounds_ds"]
                assert 0<=a<c<=256 and 0<=b<d<=192
            assert len(p["world_bounds_ds"])==4
            assert p["world_bounds_ds"][0]<=p["world_bounds_ds"][2]
            assert p["world_bounds_ds"][1]<=p["world_bounds_ds"][3]
            assert isinstance(p["world_rotation_z"],(int,float))
            assert len(p["translation_ds"])==2
            assert len(p["size_ds"])==2
            for c in p["children"]:verify(c)
        for pane in layout["panes"]:verify(pane)
    title=next(x for x in data["layouts"] if x["source"]=="MnIf_U_Title.bclyt")
    assert title["source_size"]==[400.0,240.0]
    assert title["scale"]==[0.64,0.8]
    assert title["panes"][0]["size_ds"]==[256,192]
# Malformed or non-finite geometry must fail instead of generating broken UI.
sys.path.insert(0,str(root/"tools"))
from retarget_panes import convert
original=json.loads(source.read_text())["layouts"][0]
for field,value in (("size",0),("translation",math.inf),("scale",math.nan)):
    broken=copy.deepcopy(original)
    if field=="size":
        broken["panes"][0]["size"][0]=value
    else:
        broken["panes"][0][field][0]=value
    try:
        convert(broken)
    except ValueError:
        pass
    else:
        raise AssertionError("invalid original geometry was accepted: "+field)
# Parent translations, rotation and scale must propagate to nested children.
synthetic={
    "file":"synthetic.bclyt",
    "panes":[{
        "name":"root","type":"pan1","flags":0,"origin":0,"alpha":255,
        "translation":[0,0,0],"rotation":[0,0,90],"scale":[2,2],"size":[400,240],
        "children":[{
            "name":"child","type":"pan1","flags":0,"origin":0,"alpha":255,
            "translation":[10,0,0],"rotation":[0,0,0],"scale":[1,1],"size":[20,20],
            "children":[]
        }]
    }]
}
child=convert(synthetic)["panes"][0]["children"][0]
assert child["world_translation_ds"]==[0.0,16.0]
assert child["world_rotation_z"]==90
assert child["world_scale"]==[2,2]
assert child["world_size_ds"]==[25.6,32.0]
assert child["world_bounds_ds"]==[-25.6,16.0,0.0,48.0]
assert child["viewport_coverage"]==0
assert child["visible_in_viewport"] is False
assert child["clipped_bounds_ds"] is None
assert child["effective_visible"] is False
hidden=copy.deepcopy(synthetic)
hidden["panes"][0]["flags"]=0
hidden["panes"][0]["alpha"]=0
hidden["panes"][0]["children"][0]["flags"]=1
nested=convert(hidden)["panes"][0]["children"][0]
assert nested["effective_alpha"]==0
assert nested["effective_visible"] is False
# Alpha inheritance uses integer half-up rounding, never floating ties.
transparent=copy.deepcopy(synthetic)
transparent["panes"][0]["flags"]=1
transparent["panes"][0]["alpha"]=128
transparent["panes"][0]["children"][0]["alpha"]=128
assert convert(transparent)["panes"][0]["children"][0]["effective_alpha"]==64
print("PASS: 22 original UI pane hierarchies retargeted to DS viewport")
