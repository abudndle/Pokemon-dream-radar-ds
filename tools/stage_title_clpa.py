#!/usr/bin/env python3
"""Stage PRIVATE native BCLAN CLPA keys for the five-node DS title pane runtime.

Input: JSON from tools/decode_bclan_panes.py, generated from the owner's BCLAN.
Output: private_title_clpa.h, normally placed in source/ only for a private
local build. DO NOT COMMIT its original keyframe payloads to public Git.
Unmappable/material/skeletal tracks are not silently treated as DS geometry.
"""
import argparse
import json
import math
from pathlib import Path

PROPERTIES = {
    "translate_x": 0, "translate_y": 1, "rotate_z": 5,
    "scale_x": 6, "scale_y": 7, "size_x": 8, "size_y": 9,
}
ORIGINAL_ROWS_Y = (130, 90, 50, 10)
ORIGINAL_ROWS_X = (0, 0, 0, 0)
BASE_DS_ROW_Y = tuple(-(16 + y) * .8 for y in ORIGINAL_ROWS_Y)


def target_info(name, property_name):
    if name in ("Pos", "SRT00"):
        if property_name in ("size_x", "size_y"):
            return None
        baseline = 16 if name == "SRT00" and property_name == "translate_y" else (
            1 if property_name.startswith("scale") else 0)
        dest_base = (128 if property_name == "translate_x" else
                     175.4 if property_name == "translate_y" else
                     1 if property_name.startswith("scale") else 0)
        return 0, baseline, dest_base
    for i in range(4):
        if name in (f"L{i:02d}", f"List{i:02d}", f"Touch{i:02d}"):
            if property_name in ("size_x", "size_y") and name != f"Touch{i:02d}":
                return None
            baseline = (ORIGINAL_ROWS_Y[i] if name == f"L{i:02d}" and
                        property_name == "translate_y" else
                        ORIGINAL_ROWS_X[i] if property_name == "translate_x" else
                        286 if property_name == "size_x" else
                        34 if property_name == "size_y" else
                        1 if property_name.startswith("scale") else 0)
            dest_base = (BASE_DS_ROW_Y[i] if property_name == "translate_y" else
                         228.8 if property_name == "size_x" else
                         27.2 if property_name == "size_y" else
                         1 if property_name.startswith("scale") else 0)
            return i + 1, baseline, dest_base
    return None


def cfloat(value):
    token = f"{value:.8g}"
    if "." not in token and "e" not in token:
        token += ".0"
    return token + "f"


def stage(source):
    if not isinstance(source, dict):
        raise ValueError("BCLAN decoder report must be an object")
    duration = source.get("frames")
    loop = source.get("loops")
    tracks = source.get("tracks")
    if not isinstance(duration, (int, float)) or not math.isfinite(duration) or duration <= 0 or duration > 60000:
        raise ValueError("unsupported BCLAN duration")
    if not isinstance(loop, bool) or not isinstance(tracks, list):
        raise ValueError("malformed BCLAN metadata")
    result = []
    used = set()
    total_keys = 0
    for item in tracks:
        name, prop = item["pane"], item["property"]
        if prop not in PROPERTIES:
            continue
        mapping = target_info(name, prop)
        if mapping is None:
            continue
        pane, baseline, dest_base = mapping
        marker = (pane, prop)
        if marker in used:
            raise ValueError(f"two source tracks compete for title pane/property {marker}")
        used.add(marker)
        curve = item["curve"]
        keys = item["keys"]
        if curve not in (0, 1, 2) or not isinstance(keys, list) or not keys:
            raise ValueError("invalid title CLPA curve")
        total_keys += len(keys)
        if total_keys > 1024 or len(result) >= 128:
            raise ValueError("title CLPA exceeds DS memory budgets")
        factor = (-.8 if prop == "translate_y" else
                  .8 if prop in ("translate_x", "size_x", "size_y") else
                  -1 if prop == "rotate_z" else 1)
        if prop == "size_y":
            factor = .8
        entries = []
        prev = -1
        for key in keys:
            frame, value, slope = (key[k] for k in ("frame", "value", "slope"))
            if not all(isinstance(v, (int,float)) and math.isfinite(v) for v in (frame, value, slope)):
                raise ValueError("non-finite original CLPA key")
            if frame < prev or frame < 0:
                raise ValueError("out of order BCLAN frame")
            prev = frame
            translated = dest_base + (value - baseline) * factor
            if not math.isfinite(translated) or abs(translated)>100000:
                raise ValueError("unbounded private title CLPA transform")
            entries.append((float(frame), translated, slope * factor))
        result.append((pane, PROPERTIES[prop], curve, entries))
    if not result:
        raise ValueError("no supported title pane animation tracks")
    lines = [
        "/* PRIVATE BCLAN-derived keyframes; owner-owned local build ONLY.",
        " * NEVER commit or redistribute this generated header.",
        " */",
        "#ifndef DR_PRIVATE_TITLE_CLPA_H",
        "#define DR_PRIVATE_TITLE_CLPA_H",
    ]
    for i, (_, _, _, keys) in enumerate(result):
        lines.append(f"static const DrUiKey dr_private_keys_{i}[]={{")
        for frame, value, slope in keys:
            lines.append(f"    {{{cfloat(frame)},{cfloat(value)},{cfloat(slope)}}},")
        lines.append("};")
    lines.append("static const DrUiTrack dr_private_title_tracks[]={")
    for i, (pane, property_index, curve, keys) in enumerate(result):
        lines.append(f"    {{{pane},{property_index},{curve},{len(keys)},dr_private_keys_{i}}},")
    lines.append("};")
    lines.append(
        f"static const DrUiAnimation dr_private_title_animation={{"
        f"dr_private_title_tracks,{len(result)},{cfloat(float(duration))},{int(loop)}}};")
    lines.extend(["#endif", ""])
    return "\n".join(lines), len(result), total_keys


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("private_decoded_clpa_json",type=Path)
    parser.add_argument("private_header_output",type=Path)
    args=parser.parse_args()
    inp=args.private_decoded_clpa_json.resolve()
    out=args.private_header_output.resolve()
    if inp == out:
        raise ValueError("cannot overwrite original BCLAN report")
    if inp.stat().st_size > 16 * 1024 * 1024:
        raise ValueError("private BCLAN report exceeds size limit")
    content,tracks,keys=stage(json.loads(inp.read_text(encoding="utf-8")))
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(content,encoding="utf-8")
    print(f"PRIVATE title clip: {tracks} tracks, {keys} keys, output={out}")
    print("Do not commit source/private_title_clpa.h to GitHub.")


if __name__ == "__main__":
    main()
