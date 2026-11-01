#!/usr/bin/env python3
"""Decode private CLPA pane transform curves; does not render original UI.

Material, color, visibility and other tag types are reported as unsupported.
Write decoded source keyframes only to a private output directory.
"""
import argparse
import bisect
import json
import math
from pathlib import Path
import struct
from map_original_ui_layouts import LayoutError, animation_metadata, sections

PROPERTIES = ("translate_x", "translate_y", "translate_z", "rotate_x", "rotate_y",
              "rotate_z", "scale_x", "scale_y", "size_x", "size_y")
MAX_BYTES = 16 * 1024 * 1024
MAX_KEYS = 100000
MAX_NODES = 100000

def decode(data):
    if len(data) > MAX_BYTES:
        raise LayoutError("BCLAN exceeds decoder byte budget")
    result = animation_metadata(data)
    block = next(b for tag, b in sections(data, b"CLAN") if tag == b"pai1")
    def bounds(offset, size):
        if offset < 0 or size < 0 or offset + size > len(block):
            raise LayoutError("BCLAN offset outside animation section")
    def read(fmt, offset):
        bounds(offset, struct.calcsize(fmt))
        return struct.unpack_from(fmt, block, offset)
    def offsets(start, count, minimum):
        bounds(start, count * 4)
        values = [read("<I", start + i * 4)[0] for i in range(count)]
        if any(value < minimum for value in values) or len(set(values)) != len(values):
            raise LayoutError("BCLAN offsets overlap their header or are duplicated")
        return values
    textures, count, table = read("<HHI", 12)
    if textures > 4096 or count > 4096:
        raise LayoutError("BCLAN exceeds entry/texture budget")
    bounds(20, textures * 4)
    if table < 20 + textures * 4:
        raise LayoutError("BCLAN entry table overlaps header")
    entries = offsets(table, count, table + count * 4)
    tracks, unsupported = [], []
    total_keys = 0
    nodes = count
    for entry in entries:
        bounds(entry, 24)
        raw_name = block[entry:entry + 20].split(b"\0", 1)[0]
        try:
            name = raw_name.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise LayoutError("invalid BCLAN target name") from exc
        if not name:
            raise LayoutError("empty BCLAN target name")
        tag_count, target = read("<BB", entry + 20)
        nodes += tag_count
        if nodes > MAX_NODES:
            raise LayoutError("BCLAN exceeds node budget")
        for relative in offsets(entry + 24, tag_count, 24 + tag_count * 4):
            tag_at = entry + relative + (4 if target == 2 else 0)
            bounds(tag_at, 8)
            try:
                tag = block[tag_at:tag_at + 4].decode("ascii")
            except UnicodeDecodeError as exc:
                raise LayoutError("invalid BCLAN tag") from exc
            channels = block[tag_at + 4]
            nodes += channels
            if nodes > MAX_NODES:
                raise LayoutError("BCLAN exceeds node budget")
            channel_offsets = offsets(tag_at + 8, channels, 8 + channels * 4)
            for channel in channel_offsets:
                bounds(tag_at + channel, 12)
            if tag != "CLPA" or target != 0:
                unsupported.append({"target": name, "target_kind": target, "tag": tag})
                continue
            for relative_channel in channel_offsets:
                at = tag_at + relative_channel
                index, prop, curve, _, keys, _, key_offset = read("<BBBBHHI", at)
                if index != 0 or prop >= len(PROPERTIES) or curve not in (0, 1, 2):
                    raise LayoutError("unsupported CLPA property/index/curve encoding")
                if key_offset < 12 or not keys:
                    raise LayoutError("missing or overlapping CLPA keys")
                total_keys += keys
                if total_keys > MAX_KEYS:
                    raise LayoutError("BCLAN exceeds key budget")
                stride = 12 if curve == 2 else 8
                start = at + key_offset
                bounds(start, stride * keys)
                decoded = []
                for i in range(keys):
                    pos = start + i * stride
                    if curve == 2:
                        frame, value, slope = read("<fff", pos)
                    else:
                        frame, value, _ = read("<fhH", pos)
                        slope = 0.0
                    if not all(math.isfinite(v) for v in (frame, value, slope)):
                        raise LayoutError("non-finite CLPA key")
                    if decoded and frame < decoded[-1]["frame"]:
                        raise LayoutError("CLPA key frames must not run backwards")
                    decoded.append({"frame": frame, "value": value, "slope": slope})
                tracks.append({"pane": name, "property": PROPERTIES[prop],
                               "curve": curve, "keys": decoded})
    result.update(tracks=tracks, unsupported_tags=unsupported)
    return result

def sample_track(track, frame):
    """Sample local step/constant or cubic Hermite values, with endpoint clamp.

    No loop wrapping, DS coordinate conversion, parent composition or layering
    is implied; callers must decide those policies explicitly.
    """
    if not math.isfinite(frame):
        raise LayoutError("non-finite sample frame")
    keys = track["keys"]
    if frame < keys[0]["frame"]:
        return keys[0]["value"]
    if frame >= keys[-1]["frame"]:
        return keys[-1]["value"]
    # Original clips contain equal-time keys. Choose the last such key at
    # the boundary, avoiding a zero-duration Hermite division.
    index = bisect.bisect_right([k["frame"] for k in keys], frame) - 1
    a, b = keys[index:index + 2]
    if track["curve"] != 2:
        return a["value"]
    duration = b["frame"] - a["frame"]
    t = (frame - a["frame"]) / duration
    return ((2*t**3 - 3*t**2 + 1) * a["value"] +
            (t**3 - 2*t**2 + t) * duration * a["slope"] +
            (-2*t**3 + 3*t**2) * b["value"] +
            (t**3 - t**2) * duration * b["slope"])

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("private_output", type=Path)
    args = parser.parse_args()
    if args.source.resolve() == args.private_output.resolve():
        raise LayoutError("decoded output must not overwrite its original source")
    if args.source.stat().st_size > MAX_BYTES:
        raise LayoutError("BCLAN exceeds decoder byte budget")
    report = decode(args.source.read_bytes())
    args.private_output.parent.mkdir(parents=True, exist_ok=True)
    args.private_output.write_text(json.dumps(report, indent=2) + "\n")
    print(f"Decoded {len(report['tracks'])} CLPA tracks; "
          f"{len(report['unsupported_tags'])} other target tags explicitly unsupported")

if __name__ == "__main__":
    main()
