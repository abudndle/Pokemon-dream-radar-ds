#!/usr/bin/env python3
"""Validate privately extracted 3DS BCLYT layouts and BCLAN clip metadata.

Writes local, non-proprietary diagnostics: layout dimensions, pane transforms,
clip duration and loop flags. It does NOT decode BCLAN keyframe tracks or
reproduce the 3DS compositor's pivot/rotation/alpha behavior.
"""
import argparse
import json
import math
import struct
from collections import Counter
from pathlib import Path

class LayoutError(ValueError):
    pass

PANE_TAGS = {b"pan1", b"pic1", b"txt1", b"wnd1", b"bnd1"}
HEADER = "<4sHHIII"

def sections(data, magic):
    if len(data) < 20:
        raise LayoutError("truncated NW4C file")
    tag, bom, header_size, version, size, count = struct.unpack_from(HEADER, data)
    if (tag != magic or bom != 0xfeff or header_size != 20 or
            size != len(data) or version != 0x02020000 or count > 10000):
        raise LayoutError("invalid NW4C file header")
    result = []
    offset = header_size
    for _ in range(count):
        if offset + 8 > len(data):
            raise LayoutError("truncated NW4C section")
        kind, length = struct.unpack_from("<4sI", data, offset)
        if length < 8 or length > len(data) - offset:
            raise LayoutError("out-of-bounds NW4C section")
        result.append((kind, data[offset:offset + length]))
        offset += length
    if offset != len(data):
        raise LayoutError("trailing bytes or mismatched section count")
    return result

def layout_metadata(data):
    chunks = sections(data, b"CLYT")
    if not chunks or chunks[0][0] != b"lyt1" or len(chunks[0][1]) < 20:
        raise LayoutError("missing layout dimensions")
    width, height = struct.unpack_from("<ff", chunks[0][1], 12)
    if not (math.isfinite(width) and math.isfinite(height) and
            0 < width <= 4096 and 0 < height <= 4096):
        raise LayoutError("invalid 3DS screen dimensions")
    panes = []
    depth = 0
    for kind, block in chunks:
        if kind == b"pas1":
            if len(block) != 8 or not panes:
                raise LayoutError("unmatched pane start")
            depth += 1
        elif kind == b"pae1":
            if len(block) != 8 or depth == 0:
                raise LayoutError("unmatched pane end")
            depth -= 1
        elif kind in PANE_TAGS:
            if len(block) < 76:
                raise LayoutError("truncated pane transform")
            name = block[12:36].split(b"\x00", 1)[0].decode("ascii", "replace")
            if not name:
                raise LayoutError("empty pane name")
            transform = struct.unpack_from("<10f", block, 36)
            if any(not math.isfinite(v) for v in transform):
                raise LayoutError("invalid pane transform")
            tx, ty, tz, rx, ry, rz, sx, sy, w, h = transform
            if w < 0 or h < 0:
                raise LayoutError("negative pane dimensions")
            panes.append({
                "name": name, "kind": kind.decode("ascii"), "depth": depth,
                "translation": [tx, ty, tz], "rotation": [rx, ry, rz],
                "scale": [sx, sy], "size": [w, h],
                # LOCAL coordinates only. Do not treat these as screen bounds.
                "ds_local_translation": [round(tx * 256 / width, 4),
                                         round(ty * 192 / height, 4)],
                "ds_unscaled_size": [round(w * 256 / width, 4),
                                     round(h * 192 / height, 4)]
            })
    if depth:
        raise LayoutError("unclosed pane hierarchy")
    return {"source_canvas": [width, height],
            "ds_canvas": [256, 192],
            "pane_count": len(panes), "panes": panes}

def animation_metadata(data):
    chunks = sections(data, b"CLAN")
    pai = [block for tag, block in chunks if tag == b"pai1"]
    pat = [block for tag, block in chunks if tag == b"pat1"]
    if len(pai) != 1 or len(pat) != 1 or len(pai[0]) < 20:
        raise LayoutError("missing BCLAN animation information")
    frames, loop = struct.unpack_from("<HH", pai[0], 8)
    if not (0 < frames <= 60000 and loop in (0, 1)):
        raise LayoutError("invalid animation length or loop flag")
    return {"frames": frames, "loops": bool(loop),
            "sections": [tag.decode("ascii", "replace") for tag, _ in chunks]}

def inventory(root):
    root = Path(root)
    if not root.is_dir():
        raise LayoutError("original assets directory does not exist")
    layouts = sorted(root.rglob("*.bclyt"))
    animations = sorted(root.rglob("*.bclan"))
    if not layouts:
        raise LayoutError("no original layouts found")
    groups = {}
    for path in layouts:
        parts = path.relative_to(root).parts
        if len(parts) < 4 or parts[-2] != "blyt":
            raise LayoutError("unexpected layout path")
        key = "/".join(parts[:-2])
        if key in groups:
            raise LayoutError("multiple ambiguous layouts in group")
        entry = layout_metadata(path.read_bytes())
        entry["group"] = key
        entry["source_file"] = path.name
        entry["animations"] = []
        groups[key] = entry
    total_looped = 0
    for path in animations:
        parts = path.relative_to(root).parts
        if len(parts) < 4 or parts[-2] != "anim":
            raise LayoutError("unexpected animation path")
        key = "/".join(parts[:-2])
        if key not in groups:
            raise LayoutError("animation without corresponding layout")
        clip = animation_metadata(path.read_bytes())
        clip["source_file"] = path.name
        groups[key]["animations"].append(clip)
        total_looped += int(clip["loops"])
    dimensions = Counter(
        f"{int(g['source_canvas'][0])}x{int(g['source_canvas'][1])}"
        for g in groups.values())
    return {
        "layout_count": len(layouts),
        "animation_count": len(animations),
        "looped_animation_count": total_looped,
        "groups_with_animation": sum(bool(g["animations"]) for g in groups.values()),
        "source_canvas_counts": dict(sorted(dimensions.items())),
        "note": "Source-backed local transforms/durations only; 3DS pane compositing and BCLAN keyframe playback are not implemented.",
        "layouts": [groups[k] for k in sorted(groups)]
    }

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("private_asset_directory", type=Path)
    parser.add_argument("report_json", type=Path)
    args = parser.parse_args()
    report = inventory(args.private_asset_directory)
    args.report_json.parent.mkdir(parents=True, exist_ok=True)
    args.report_json.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Verified {report['layout_count']} layouts and "
          f"{report['animation_count']} animation clips")

if __name__ == "__main__":
    main()
