#!/usr/bin/env python3
import pathlib
import sys
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/"tools"))
from probe_ncch_lz40 import decode_lz40, DecodeError
# Two literals AB, then a four-byte backreference at distance 2.
assert decode_lz40(bytes.fromhex("40060000e041422400"))==b"ABABAB"
assert decode_lz40(bytes.fromhex("4003000000616263"))==b"abc"
for damaged in (b"",bytes.fromhex("40060000e0414224"),
                bytes.fromhex("40060000e041420000"),
                bytes.fromhex("40060000e041422400") + b"xxxxxx",
                bytes.fromhex("40000000"),
                bytes.fromhex("11060000e041422400")):
    try:decode_lz40(damaged)
    except DecodeError:pass
    else:raise AssertionError("Invalid LZ40 stream accepted")
print("PASS: bounded standard LZ40 literals, backreferences, malformed-stream rejection")
