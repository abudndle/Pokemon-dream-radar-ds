#!/usr/bin/env python3
"""Stage source-derived title BCLYT panes and optional private BCLAN tracks.

With no clip, package public geometry for the NitroFS fallback. With a
private original clip, write only to user-controlled SD/FAT storage.
"""
import argparse
import json
import math
from pathlib import Path
import struct
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
TARGET = "MnIf_S_TitleList.bclyt"
SCAN_TARGET = "MnIf_S_ScanList.bclyt"
MAINMENU_TARGET = "MnIf_S_MainMenuList.bclyt"
SHOP_TARGET = "MnIf_S_ShopList.bclyt"
ROOT_NAME = "RootPane"
PANE_NAMES = {ROOT_NAME, "Pos", "SRT00"} | {f"L{i:02d}" for i in range(4)} | {f"List{i:02d}" for i in range(4)} | {f"Touch{i:02d}" for i in range(4)}
PROPERTIES = ("translate_x", "translate_y", "translate_z", "rotate_x", "rotate_y",
              "rotate_z", "scale_x", "scale_y", "size_x", "size_y")
MAX_PANES, MAX_TRACKS, MAX_KEYS, MAX_BYTES = 96, 256, 2048, 65536

def finite(value):
    if not isinstance(value, (int, float)) or not math.isfinite(value) or abs(value) > 100000:
        raise ValueError("invalid BCLYT/BCLAN floating value")
    return float(value)

def stage(snapshot, clips=(), *, offset_y=80, target=TARGET):
    """Create bounded four-row BCLYT scene bytes; 80px Y is provisional."""
    if target not in (TARGET, SCAN_TARGET, MAINMENU_TARGET, SHOP_TARGET):
        raise ValueError("unsupported original BCLYT layout")
    layouts = snapshot["layouts"]
    matched = [item for item in layouts if Path(item["file"]).name == target]
    if len(matched) != 1:
        raise ValueError("exactly one original four-row BCLYT snapshot is required")
    layout = matched[0]
    if len(layout["panes"]) != 1 or layout["panes"][0]["name"] != ROOT_NAME:
        raise ValueError("unrecognized four-row BCLYT root")
    w, h = [int(finite(v)) for v in layout["panes"][0]["size"]]
    if w != 320 or h != 240 or not -384 <= offset_y <= 384:
        raise ValueError("unexpected source canvas or calibration")
    allowed = (PANE_NAMES if target != MAINMENU_TARGET else
               (PANE_NAMES - {"SRT00"}) | {"SRT"})
    nodes = []
    parents = []
    names = {}

    def walk(pane, parent):
        name = pane["name"]
        if name not in allowed:
            return
        if name in names or not isinstance(name, str) or len(name.encode("ascii")) > 19:
            raise ValueError("duplicate/invalid source pane")
        index = len(nodes)
        names[name] = index
        parents.append(parent)
        nodes.append(pane)
        for child in pane["children"]:
            walk(child, index)

    walk(layout["panes"][0], -1)
    if set(names) != allowed or len(nodes) > MAX_PANES:
        raise ValueError("four-row layout missing required original panes")
    # The original alpha=0 rows rely on other animation tags still unsupported.
    # The DS title fallback keeps rows visible with an explicit documented policy.
    visible_rows = {f"L{i:02d}" for i in range(4)}
    raw_nodes = []
    for pane, parent in zip(nodes, parents):
        v = [finite(value) for value in (
            pane["translation"] + pane["rotation"] + pane["scale"] + pane["size"])]
        if len(v) != 10 or v[6] == 0 or v[7] == 0 or v[8] <= 0 or v[9] <= 0:
            raise ValueError("invalid pane values")
        origin = pane["origin"]
        flags = pane["flags"]
        alpha = 255 if pane["name"] in visible_rows else pane["alpha"]
        if not all(isinstance(value, int) and 0 <= value <= limit for value, limit in
                   ((origin, 8), (flags, 255), (alpha, 255))):
            raise ValueError("invalid pane origin, flags or alpha")
        raw_nodes.append(struct.pack("<20shBBBB10f", pane["name"].encode("ascii"),
                                     parent, origin, flags, alpha, 0, *v))
    curves = []
    keys = []
    total_frames = 0
    loop = False
    seen = set()
    if len(clips) > 1:
        raise ValueError("multiple simultaneous title clips are not layered yet")
    for clip in clips:
        duration = clip.get("frames", 0)
        if not isinstance(duration, int) or not 0 < duration <= 4096:
            raise ValueError("invalid original BCLAN frame count")
        total_frames = duration
        loop = bool(clip.get("loops", False))
        for track in clip.get("tracks", []):
            name = track["pane"]
            if name not in names:
                continue
            prop_name = track["property"]
            if prop_name not in PROPERTIES:
                raise ValueError("unsupported CLPA property")
            prop = PROPERTIES.index(prop_name)
            if (name, prop) in seen:
                raise ValueError("multiple curves for one pane/property are not supported")
            seen.add((name, prop))
            mode = track["curve"]
            if mode not in (0, 1, 2):
                raise ValueError("invalid CLPA curve type")
            series = track["keys"]
            if not series:
                raise ValueError("empty CLPA track")
            start = len(keys)
            previous = -1.0
            for key in series:
                frame = finite(key["frame"])
                value = finite(key["value"])
                slope = finite(key["slope"])
                if frame < 0 or frame < previous:
                    raise ValueError("unordered/negative CLPA frame")
                previous = frame
                keys.append(struct.pack("<fff", frame, value, slope))
            curves.append(struct.pack("<HBBHH", names[name], prop, mode, start, len(series)))
            if len(keys) > MAX_KEYS or len(curves) > MAX_TRACKS:
                raise ValueError("BCLAN scene exceeds DS runtime budget")
    header = struct.pack("<4s7HhH", b"DRUI", 1, len(nodes), len(curves),
                         len(keys), w, h, total_frames, offset_y, int(loop))
    result = header + b"".join(raw_nodes) + b"".join(curves) + b"".join(keys)
    if len(result) > MAX_BYTES:
        raise ValueError("scene exceeds 64 KiB safety budget")
    return result

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshot", type=Path, help="source-derived BCLYT geometry JSON")
    parser.add_argument("output", type=Path, help="private UI/title.drui or no-clip NitroFS")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--clip", type=Path, help="private original BCLAN file")
    group.add_argument("--clip-json", type=Path, help="private JSON from decode_bclan_panes.py")
    parser.add_argument("--layout", choices=(TARGET, SCAN_TARGET, MAINMENU_TARGET, SHOP_TARGET), default=TARGET,
                        help="original four-row menu to stage")
    parser.add_argument("--offset-y", type=int, default=80,
                        help="provisional visible DS title calibration in pixels")
    args = parser.parse_args()
    for source in (args.snapshot, args.clip, args.clip_json):
        if source and source.resolve() == args.output.resolve():
            parser.error("output must not overwrite any original input")
    if (args.clip or args.clip_json) and args.output.resolve().is_relative_to(HERE.parent.resolve()):
        parser.error("private BCLAN outputs must stay outside the public checkout")
    snapshot = json.loads(args.snapshot.read_text(encoding="utf-8"))
    clips = []
    if args.clip:
        from decode_bclan_panes import decode as decode_bclan
        clips.append(decode_bclan(args.clip.read_bytes()))
    if args.clip_json:
        clips.append(json.loads(args.clip_json.read_text(encoding="utf-8")))
    result = stage(snapshot, clips, offset_y=args.offset_y, target=args.layout)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(result)
    print(f"{args.layout} staged: {len(result)} bytes, {'private BCLAN' if clips else 'geometry only'}")

if __name__ == "__main__":
    main()
