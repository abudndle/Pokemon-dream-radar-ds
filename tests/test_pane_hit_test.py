import math
import pathlib
import sys
root=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/"tools"))
from pane_hit_test import pane_hit, pane_at
from retarget_panes import convert
import json

def pane(corners,visible=True):
    return {"world_corners_ds":corners,"world_bounds_ds":[min(p[0] for p in corners),min(p[1] for p in corners),max(p[0] for p in corners),max(p[1] for p in corners)],"effective_visible":visible}

square=pane([[10,10],[30,10],[10,30],[30,30]])
assert pane_hit(square,20,20)
assert not pane_hit(square,31,20)
assert not pane_hit(square,-1,20)
assert not pane_hit(square,None,20)
assert not pane_hit(square,"20",20)
assert not pane_hit({"effective_visible":True},20,20)
assert not pane_hit({"effective_visible":True,"world_bounds_ds":[0,0,50,50]},20,20)
assert not pane_hit({"effective_visible":True,"world_bounds_ds":[0,0,50,50],"world_corners_ds":[[0,0],[50,"bad"],[0,50],[50,50]]},20,20)
assert not pane_hit(pane(square["world_corners_ds"],False),20,20)
transparent=pane(square["world_corners_ds"])
transparent["effective_alpha"]=0
assert not pane_hit(transparent,20,20)
transparent["effective_alpha"]=255
assert pane_hit(transparent,20,20)
transparent["effective_alpha"]=256
assert not pane_hit(transparent,20,20)
transparent["effective_alpha"]=-1
assert not pane_hit(transparent,20,20)
transparent["effective_alpha"]=True
assert not pane_hit(transparent,20,20)
transparent["effective_alpha"]=128
assert pane_hit(transparent,20,20)

# Diamond's bounding rectangle contains a large region outside its quad.
diamond=pane([[100,70],[130,100],[70,100],[100,130]])
assert pane_hit(diamond,100,100)
assert not pane_hit(diamond,71,71)
assert not pane_hit(diamond,129,129)
# Malformed/self-crossing quads must not become interactive panes.
bowtie=pane([[20,20],[40,40],[20,40],[40,20]])
assert not pane_hit(bowtie,30,30)
concave=pane([[20,20],[40,20],[30,25],[20,40]])
assert not pane_hit(concave,28,26)
assert not pane_hit(pane([[20,20]]*4),20,20)
assert not pane_hit(pane([[10,10],[30,10],[10,30],[math.inf,30]]),20,20)
parent=pane([[10,10],[90,10],[10,90],[90,90]])
child=pane([[20,20],[40,20],[20,40],[40,40]])
parent["name"]="parent"
child["name"]="child"
parent["children"]=[child]
assert pane_at({"panes":[parent]},25,25)["name"]=="child"
assert pane_at({"panes":[parent]},60,60)["name"]=="parent"
assert pane_at({"panes":[parent]},100,100) is None
sibling=pane([[20,20],[40,20],[20,40],[40,40]])
sibling["name"]="later sibling"
assert pane_at({"panes":[parent,sibling]},25,25)["name"]=="later sibling"
# Exercise the picker against original extracted layouts, not only synthetic
# geometry, and ensure the returned pane itself is hittable.
source=json.loads((root/"ui_mapping/original_pane_geometry.json").read_text())
assert len(source["layouts"])==22
for original in source["layouts"]:
    layout=convert(original)
    for x,y in ((0,0),(32,48),(128,96),(224,160),(255,191)):
        selected=pane_at(layout,x,y)
        assert selected is None or pane_hit(selected,x,y)
print("PASS: transformed UI quadrilateral touch tests, picking, and 22 layout integration")
