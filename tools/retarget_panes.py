#!/usr/bin/env python3
"""Retarget extracted 3DS pane dimensions into provisional DS coordinates.

Parent XY transforms and Z rotations are composed for inspection, but origins,
3D transforms, material binding and BCLAN animation need separate work.
"""
import argparse
import json
import math
from pathlib import Path

DS_WIDTH, DS_HEIGHT = 256, 192

def convert(layout):
    roots = layout["panes"]
    if not roots:
        raise ValueError("layout has no root panes")
    source_width, source_height = roots[0]["size"]
    if not all(math.isfinite(v) and v > 0 for v in (source_width, source_height)):
        raise ValueError("invalid root dimensions")
    scale_x, scale_y = DS_WIDTH/source_width, DS_HEIGHT/source_height
    def walk(pane, parent_x=0.0, parent_y=0.0, parent_angle=0.0, parent_sx=1.0, parent_sy=1.0, parent_visible=True, parent_alpha=255):
        values = (pane["translation"] + pane["rotation"] + pane["scale"] + pane["size"])
        if not all(math.isfinite(v) for v in values):
            raise ValueError(f'non-finite geometry in pane {pane["name"]}')
        # Compose parent translation, scale and Z rotation for approximate
        # screen-space positions. Other 3D transforms, origins and anchors
        # still require a full BCLYT renderer.
        local_x=pane["translation"][0]*parent_sx
        local_y=pane["translation"][1]*parent_sy
        angle=math.radians(parent_angle)
        x=parent_x+local_x*math.cos(angle)-local_y*math.sin(angle)
        y=parent_y+local_x*math.sin(angle)+local_y*math.cos(angle)
        z_angle=parent_angle+pane["rotation"][2]
        sx=parent_sx*pane["scale"][0]
        sy=parent_sy*pane["scale"][1]
        if not all(math.isfinite(v) for v in (x,y,z_angle,sx,sy)):
            raise ValueError(f'non-finite composed geometry in pane {pane["name"]}')
        # Axis-aligned envelope of the rotated pane in DS pixel coordinates.
        # Useful for inspection and broad-phase hit testing, not a replacement
        # for origin/anchor-aware material geometry.
        width=pane["size"][0]*sx
        height=pane["size"][1]*sy
        theta=math.radians(z_angle)
        corners=[(x+u*math.cos(theta)-v*math.sin(theta),
                  y+u*math.sin(theta)+v*math.cos(theta))
                 for u,v in ((0,0),(width,0),(0,height),(width,height))]
        bounds=[round(min(pt[0] for pt in corners)*scale_x,4),
                round(min(pt[1] for pt in corners)*scale_y,4),
                round(max(pt[0] for pt in corners)*scale_x,4),
                round(max(pt[1] for pt in corners)*scale_y,4)]
        # Clamp the envelope to the physical DS screen. Empty intersections
        # are marked invisible rather than creating negative-size hit regions.
        left=max(0.0,bounds[0]);top=max(0.0,bounds[1])
        right=min(float(DS_WIDTH),bounds[2]);bottom=min(float(DS_HEIGHT),bounds[3])
        visible=right>left and bottom>top
        clipped=[left,top,right,bottom] if visible else None
        # This ratio describes how much of the axis-aligned pane envelope
        # overlaps the DS viewport; it is not pixel-accurate rotated coverage.
        area=max(0.0,bounds[2]-bounds[0])*max(0.0,bounds[3]-bounds[1])
        covered=(right-left)*(bottom-top) if visible else 0.0
        coverage=round(covered/area,4) if area>0 else 0.0
        # Pane flags can mark a node hidden; preserve that separately from
        # geometry, because a hidden in-bounds node must not receive input.
        flag_visible=bool(pane["flags"] & 1)
        hierarchy_visible=flag_visible and parent_visible
        effective_visible=visible and hierarchy_visible
        effective_alpha=(parent_alpha*pane["alpha"]+127)//255
        effective_visible=effective_visible and effective_alpha>0
        return {
            "flag_visible": flag_visible,
            "hierarchy_visible": hierarchy_visible,
            "effective_alpha": effective_alpha,
            "effective_visible": effective_visible,
            "viewport_coverage": coverage,
            "visible_in_viewport": visible,
            "clipped_bounds_ds": clipped,
            "world_corners_ds": [[round(px*scale_x,4),round(py*scale_y,4)] for px,py in corners],
            "world_bounds_ds": bounds,
            "world_translation_ds": [round(x*scale_x,4),round(y*scale_y,4)],
            "world_rotation_z": round(z_angle,4),
            "world_scale": [round(sx,4),round(sy,4)],
            "world_size_ds": [round(abs(pane["size"][0]*sx*scale_x),4),round(abs(pane["size"][1]*sy*scale_y),4)],
            "name": pane["name"],
            "type": pane["type"],
            "flags": pane["flags"],
            "origin": pane["origin"],
            "alpha": pane["alpha"],
            "rotation": pane["rotation"],
            "scale": pane["scale"],
            "translation_z": pane["translation"][2],
            "translation_ds": [
                round(pane["translation"][0]*scale_x, 4),
                round(pane["translation"][1]*scale_y, 4)
            ],
            "size_ds": [
                round(pane["size"][0]*scale_x, 4),
                round(pane["size"][1]*scale_y, 4)
            ],
            "children": [walk(child,x,y,z_angle,sx,sy, hierarchy_visible, effective_alpha) for child in pane["children"]]
        }
    return {
        "source": Path(layout["file"]).name,
        "source_path": layout["file"],
        "source_size": [source_width, source_height],
        "target_size": [DS_WIDTH, DS_HEIGHT],
        "scale": [scale_x, scale_y],
        "panes": [walk(root) for root in roots]
    }

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args=parser.parse_args()
    source=json.loads(args.input.read_text())
    output={
        "notice": "Provisional composed X/Y transforms (Z rotation, XY scale) only; NOT a rendered original UI. Origins, anchors, 3D transforms, textures and animations remain unresolved.",
        "layouts": [convert(layout) for layout in source["layouts"]]
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2)+"\n")
    print("Retargeted",len(output["layouts"]),"layouts")

if __name__=="__main__":
    main()
