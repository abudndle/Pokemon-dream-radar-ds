#!/usr/bin/env python3
"""Retarget extracted 3DS pane dimensions into DS viewport coordinates.

This produces inspection metadata, not a faithful BCLYT renderer: rotations,
parent transforms, anchors, textures and BCLAN animations require separate work.
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
    def walk(pane):
        values = (pane["translation"] + pane["rotation"] + pane["scale"] + pane["size"])
        if not all(math.isfinite(v) for v in values):
            raise ValueError(f'non-finite geometry in pane {pane["name"]}')
        return {
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
            "children": [walk(child) for child in pane["children"]]
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
        "notice": "Provisional scaled pane metadata; NOT a composed or rendered original UI.",
        "layouts": [convert(layout) for layout in source["layouts"]]
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2)+"\n")
    print("Retargeted",len(output["layouts"]),"layouts")

if __name__=="__main__":
    main()
