#!/usr/bin/env python3
"""Provisional touch hit-testing for retargeted DS panes.

Uses transformed quad corners rather than their enclosing bounding boxes.
Only geometry is considered; BCLYT origins, masks and materials remain TODO.
"""
import math

def pane_hit(pane, x, y):
    """Return whether a DS touch point lies inside a visible pane quad."""
    if not (isinstance(x,(int,float)) and isinstance(y,(int,float)) and math.isfinite(x) and math.isfinite(y) and 0 <= x < 256 and 0 <= y < 192):
        return False
    if not pane.get("effective_visible", False):
        return False
    bounds=pane.get("world_bounds_ds")
    if not isinstance(bounds,(list,tuple)) or len(bounds)!=4 or any(not isinstance(v,(int,float)) or not math.isfinite(v) for v in bounds):
        return False
    if x < bounds[0] or x > bounds[2] or y < bounds[1] or y > bounds[3]:
        return False
    corners=pane.get("world_corners_ds")
    if not isinstance(corners,(list,tuple)):
        return False
    if len(corners)!=4 or any(not isinstance(p,(list,tuple)) or len(p)!=2 or not all(isinstance(v,(int,float)) and math.isfinite(v) for v in p) for p in corners):
        return False
    # Export ordering is TL,TR,BL,BR. Traverse the perimeter clockwise.
    quad=[corners[i] for i in (0,1,3,2)]
    signs=[]
    for i in range(4):
        a,b=quad[i],quad[(i+1)%4]
        cross=(b[0]-a[0])*(y-a[1])-(b[1]-a[1])*(x-a[0])
        signs.append(cross)
    area=sum(quad[i][0]*quad[(i+1)%4][1]-quad[(i+1)%4][0]*quad[i][1] for i in range(4))
    if abs(area)<1e-8:
        return False
    return all(v>=-1e-6 for v in signs) or all(v<=1e-6 for v in signs)

def pane_at(layout, x, y):
    """Return the topmost visible pane hit, or None.

    This is a provisional source-order picker. Child panes are drawn after
    parents, and later siblings are presumed above earlier siblings.
    """
    def visit(panes):
        for pane in reversed(panes):
            child=visit(pane.get("children",[]))
            if child is not None:
                return child
            if pane_hit(pane,x,y):
                return pane
        return None
    return visit(layout["panes"])
