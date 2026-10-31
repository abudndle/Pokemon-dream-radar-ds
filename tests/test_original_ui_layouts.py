#!/usr/bin/env python3
"""Synthetic BCLYT/BCLAN fixtures; no copyrighted game files included."""
import json
import pathlib
import struct
import sys
import tempfile
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tools"))
from map_original_ui_layouts import LayoutError, layout_metadata, animation_metadata, inventory

def section(tag, content):
    return tag + struct.pack("<I", len(content)+8) + content

def nw4c(tag, blocks):
    body = b"".join(blocks)
    return struct.pack("<4sHHIII", tag, 0xfeff, 20, 0x02020000,
                       20 + len(body), len(blocks)) + body

def pane(name, tx, ty, width=100, height=60):
    name = name.encode("ascii").ljust(24, b"\0")
    # flags, origin, opacity, reserved followed by name and ten floats
    payload = struct.pack("<4B", 1, 4, 255, 0) + name
    payload += struct.pack("<10f", tx, ty, 0, 0, 0, 0, 1, 1, width, height)
    return section(b"pan1", payload)

layout = nw4c(b"CLYT", [
    section(b"lyt1", struct.pack("<Iff", 1, 400.0, 240.0)),
    pane("RootPane", 0, 0, 400, 240),
    section(b"pas1", b""),
    pane("Button", 50, -20),
    section(b"pae1", b"")])
clip = nw4c(b"CLAN", [
    section(b"pat1", b"\0"*12),
    section(b"pai1", struct.pack("<HHI", 74, 1, 0) + b"\0"*4)])

m = layout_metadata(layout)
assert m["source_canvas"] == [400.0, 240.0]
assert m["pane_count"] == 2
assert m["panes"][1]["depth"] == 1
assert m["panes"][1]["ds_local_translation"] == [32.0, -16.0]
assert m["panes"][1]["ds_unscaled_size"] == [64.0, 48.0]
assert animation_metadata(clip)["frames"] == 74
assert animation_metadata(clip)["loops"] is True

with tempfile.TemporaryDirectory() as d:
    root = pathlib.Path(d)
    folder = root/"Ui"/"Menu"
    (folder/"blyt").mkdir(parents=True)
    (folder/"anim").mkdir()
    (folder/"blyt"/"Menu.bclyt").write_bytes(layout)
    (folder/"anim"/"Menu_In.bclan").write_bytes(clip)
    report = inventory(root)
    assert report["layout_count"] == 1 and report["animation_count"] == 1
    assert report["source_canvas_counts"] == {"400x240": 1}
    assert report["groups_with_animation"] == 1
    assert report["layouts"][0]["group"] == "Ui/Menu"
    bad = root/"Ui"/"Menu"/"anim"/"Menu_In.bclan"
    bad.write_bytes(clip[:-1])
    try:
        inventory(root)
    except LayoutError:
        pass
    else:
        raise AssertionError("truncated source animation was accepted")

for data, which in (
    (layout[:-1], layout_metadata),
    (layout[:20] + section(b"lyt1", struct.pack("<Iff", 1, float("nan"), 240.0))
     + layout[40:], layout_metadata),
    (nw4c(b"CLYT", [section(b"lyt1", struct.pack("<Iff",1,400.0,240.0)),
                   section(b"pae1",b"")]), layout_metadata),
    (clip[:-1], animation_metadata),
    (nw4c(b"CLAN", [section(b"pai1",struct.pack("<HHI",0,1,0)+b"\0"*4),
                    section(b"pat1",b"\0"*12)]), animation_metadata)):
    try:
        which(data)
    except LayoutError:
        pass
    else:
        raise AssertionError("invalid NW4C fixture accepted")
print("PASS: source-backed 3DS layout scales, hierarchy, BCLAN timing and validation")
