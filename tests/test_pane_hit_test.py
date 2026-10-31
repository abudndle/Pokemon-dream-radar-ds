import math
import pathlib
import sys
root=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/"tools"))
from pane_hit_test import pane_hit

def pane(corners,visible=True):
    return {"world_corners_ds":corners,"world_bounds_ds":[min(p[0] for p in corners),min(p[1] for p in corners),max(p[0] for p in corners),max(p[1] for p in corners)],"effective_visible":visible}

square=pane([[10,10],[30,10],[10,30],[30,30]])
assert pane_hit(square,20,20)
assert not pane_hit(square,31,20)
assert not pane_hit(square,-1,20)
assert not pane_hit(pane(square["world_corners_ds"],False),20,20)
# Diamond's bounding rectangle contains a large region outside its quad.
diamond=pane([[100,70],[130,100],[70,100],[100,130]])
assert pane_hit(diamond,100,100)
assert not pane_hit(diamond,71,71)
assert not pane_hit(diamond,129,129)
assert not pane_hit(pane([[20,20]]*4),20,20)
assert not pane_hit(pane([[10,10],[30,10],[10,30],[math.inf,30]]),20,20)
print("PASS: transformed UI quadrilateral touch tests")
