#!/usr/bin/env python3
"""Rebuild the title-menu DS pane nodes from verified original BCLYT snapshots.

The four Touch00..03 panes have source-validated width/height and hierarchy.
Original entrance BCLAN positioning is not yet rendered. The provisional
vertical offset is kept explicit and golden-geometry checked, not disguised
as a recovered animation keyframe.
"""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "ui_mapping/original_pane_geometry.json"
OUTPUT = ROOT / "source/dr_title_pane_nodes_generated.h"
ORIGIN_DS_Y = 175.4  # approved title screenshot, provisional BCLAN position


def find_descendant(root, name):
    matches = []
    def visit(node, chain):
        if node["name"] == name:
            matches.append(chain + [node])
        for child in node["children"]:
            visit(child, chain + [node])
    visit(root, [])
    if len(matches) != 1:
        raise ValueError(f"expected one original BCLYT pane named {name}, found {len(matches)}")
    return matches[0]


def export(data):
    layouts = [layout for layout in data["layouts"]
               if Path(layout["file"]).name == "MnIf_S_TitleList.bclyt"]
    if len(layouts) != 1 or len(layouts[0]["panes"]) != 1:
        raise ValueError("expected one original MnIf_S_TitleList layout")
    root = layouts[0]["panes"][0]
    if root["name"] != "RootPane" or root["size"] != [320.0, 240.0]:
        raise ValueError("original title source canvas changed")
    scale_x, scale_y = 256 / root["size"][0], 192 / root["size"][1]
    rows = []
    for i in range(4):
        chain = find_descendant(root, f"Touch{i:02d}")
        names = [pane["name"] for pane in chain]
        if names != ["RootPane", "Pos", "SRT00", f"L{i:02d}",
                     f"List{i:02d}", f"Touch{i:02d}"]:
            raise ValueError(f"unexpected title pane ancestry: {names!r}")
        if any(p["rotation"] != [0, 0, 0] or p["scale"] != [1, 1]
               for p in chain):
            raise ValueError(f"animated title pane has an unexpected static transform: {i}")
        leaf = chain[-1]
        if leaf["origin"] != 4 or not (leaf["flags"] & 1):
            raise ValueError(f"title Touch{i:02d} origin/visibility changed")
        x = sum(p["translation"][0] for p in chain) * scale_x
        y = -sum(p["translation"][1] for p in chain) * scale_y
        w = leaf["size"][0] * scale_x
        h = leaf["size"][1] * scale_y
        rows.append((x, y, w, h))
    if any(abs(a[1] - b[1] + 32) > 0.001
           for a, b in zip(rows, rows[1:])):
        raise ValueError("original title row spacing unexpectedly changed")
    # Coordinates are DS pixels with origin at the center of each touch pane.
    lines = [
        "/* Generated from the owner's MnIf_S_TitleList.bclyt pane snapshot.",
        " * BCLAN entrance offset remains provisional; no original clip is embedded.",
        " * Regenerate: python3 tools/generate_title_pane_nodes.py",
        " */",
        "#ifndef DR_TITLE_PANE_NODES_GENERATED_H",
        "#define DR_TITLE_PANE_NODES_GENERATED_H",
        "static const DrUiPane dr_title_source_nodes[5]={",
        f"    {{-1,128.0f,{ORIGIN_DS_Y:.4f}f,256.0f,192.0f,1,1,0,4,1,255,0}},",
    ]
    for x, y, w, h in rows:
        lines.append(
            f"    {{0,{x:.4f}f,{y:.4f}f,{w:.4f}f,{h:.4f}f,1,1,0,4,1,255,0}},")
    lines.extend(["};", "#endif", ""])
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true",
                        help="Fail unless committed generated geometry matches the snapshot")
    args = parser.parse_args()
    result = export(json.loads(SNAPSHOT.read_text(encoding="utf-8")))
    if args.check:
        if not OUTPUT.is_file() or OUTPUT.read_text(encoding="utf-8") != result:
            raise SystemExit("Original title pane snapshot and generated header are out of sync")
        print("PASS: four original BCLYT title touch panes match compiled runtime")
    else:
        OUTPUT.write_text(result, encoding="utf-8")
        print(f"Generated {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
