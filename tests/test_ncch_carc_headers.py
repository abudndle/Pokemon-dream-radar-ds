#!/usr/bin/env python3
"""CARC signature classification: unknown formats must never be guessed."""
import pathlib
import sys
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/"tools"))
from audit_ncch_carc import classify_header
assert classify_header(0x10)=="lz10"
assert classify_header(0x11)=="lz11"
assert classify_header(0x40)=="unverified"
assert classify_header(0x00)=="unverified"
assert classify_header(0xff)=="unverified"
print("PASS: CARC signatures distinguish standard LZ from unknown 0x40")
