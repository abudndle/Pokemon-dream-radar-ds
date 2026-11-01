"""Synthetic CLAN curves; no original animation payloads in the test suite."""
import math
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from decode_bclan_panes import LayoutError, MAX_BYTES, decode, sample_track

def section(tag, body):
    return tag + struct.pack("<I", len(body) + 8) + body

def clip(keys, curve=2, tag=b"CLPA", target=0):
    raw_keys = b"".join(struct.pack("<fff", *key) if curve == 2 else
                        struct.pack("<fhH", key[0], key[1], 0) for key in keys)
    track = struct.pack("<BBBBHHI", 0, 1, curve, 0, len(keys), 0, 12) + raw_keys
    tag_body = tag + struct.pack("<B3xI", 1, 12) + track
    entry = b"TestPane".ljust(20, b"\0") + struct.pack("<BBHI", 1, target, 0, 28) + tag_body
    pai = section(b"pai1", struct.pack("<HBBHHII", 10, 1, 0, 0, 1, 20, 24) + entry)
    body = section(b"pat1", bytes(12)) + pai
    return struct.pack("<4sHHIII", b"CLAN", 0xfeff, 20, 0x02020000, len(body)+20, 2) + body

source = clip([(0, 0, 1), (10, 10, 0)])
decoded = decode(source)
assert decoded["frames"] == 10 and decoded["loops"]
assert not decoded["unsupported_tags"]
track = decoded["tracks"][0]
assert track["pane"] == "TestPane" and track["property"] == "translate_y"
assert sample_track(track, -1) == 0 and sample_track(track, 11) == 10
assert math.isclose(sample_track(track, 5), 6.25)
step = decode(clip([(0, 2, 0), (10, 7, 0)], curve=1))["tracks"][0]
assert sample_track(step, 9.99) == 2 and sample_track(step, 10) == 7
constant = decode(clip([(0, 3, 0)], curve=0))["tracks"][0]
assert sample_track(constant, 0) == sample_track(constant, 100) == 3
# Native clips legitimately contain same-frame discontinuities. They must
# remain distinct, select the last equal-time key, and never divide by zero.
equal = decode(clip([(0, 1, 0), (0, 5, 0), (10, 10, 0)]))["tracks"][0]
assert sample_track(equal, -1) == 1 and sample_track(equal, 0) == 5
assert math.isclose(sample_track(equal, 5), 7.5)
for value in (float("nan"), float("inf")):
    try:
        sample_track(track, value)
    except LayoutError:
        pass
    else:
        raise AssertionError("non-finite sample time accepted")
for value in (clip([(0, 0, 0)], tag=b"CLVC"), clip([(0, 0, 0)], target=1)):
    unsupported = decode(value)
    assert not unsupported["tracks"] and len(unsupported["unsupported_tags"]) == 1

bad = [source[:-1], source+b'\0', bytes(MAX_BYTES+1),
       clip([]), clip([(0, float("nan"), 0)]),
       clip([(0, 1, float("inf"))]), clip([(10, 0, 0), (0, 1, 0)])]
tag_at = source.index(b"CLPA")
track_at = tag_at + 12
pai_at = source.index(b"pai1")
for offset, fmt, value in ((pai_at+16, "I", 0xffffffff),
                           (pai_at+20, "I", 0),
                           (tag_at+8, "I", 0xffffffff),
                           (track_at+1, "B", 10), (track_at+2, "B", 3),
                           (track_at+4, "H", 65535), (track_at+8, "I", 0)):
    mutated = bytearray(source)
    struct.pack_into("<"+fmt, mutated, offset, value)
    bad.append(mutated)
for value in bad:
    try:
        decode(value)
    except LayoutError:
        pass
    else:
        raise AssertionError("malformed or unsupported pane data accepted")
with tempfile.TemporaryDirectory() as directory:
    path = Path(directory) / "original.bclan"
    path.write_bytes(source)
    script = Path(__file__).resolve().parents[1] / "tools/decode_bclan_panes.py"
    result = subprocess.run([sys.executable, str(script), str(path), str(path)], capture_output=True)
    assert result.returncode != 0 and path.read_bytes() == source
print("PASS: native BCLAN pane curves, Hermite/step sampling, equal-time keys and malformed offsets")
