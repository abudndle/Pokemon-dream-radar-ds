#!/usr/bin/env python3
"""CARC signature classification: unknown formats must never be guessed."""
import pathlib
import sys
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/"tools"))
from audit_ncch_carc import classify_header, inspect_size_header
assert classify_header(0x10)=="lz10"
assert classify_header(0x11)=="lz11"
assert classify_header(0x40)=="unverified"
assert classify_header(0x00)=="unverified"
assert classify_header(0xff)=="unverified"
assert inspect_size_header(bytes.fromhex("40a88101"),9332)==0x0181a8
assert inspect_size_header(bytes.fromhex("40a84108"),79220)==0x0841a8
assert inspect_size_header(bytes.fromhex("40a88101"),9332,1000) is None
assert inspect_size_header(bytes.fromhex("40000000"),9332) is None
assert inspect_size_header(bytes.fromhex("10a88101"),9332) is None
assert inspect_size_header(b"\\x40",9332) is None
print("PASS: CARC signatures and bounded 0x40 unpacked-size candidates")
