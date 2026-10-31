#!/usr/bin/env python3
"""Provisional touch hit-testing for retargeted DS panes.

Uses transformed quad corners rather than their enclosing bounding boxes.
Only geometry is considered; BCLYT origins, masks and materials remain TODO.
"""
import math

def pane_hit(pane, x, y):
    """Return whether a DS touch point lies inside a visible pane quad."""
    if not (math.isfinite(x) and math.isfinite(y) and 0 <= x < 256 and 0 <= y < 192):
        return False
    if not pane.get("effective_visible", False):
        return False
    bounds=pane["world_bounds_ds"]
    if x < bounds[0] or x > bounds[2] or y < bounds[1] or y > bounds[3]:
        return False
    corners=pane["world_corners_ds"]
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
