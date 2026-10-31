#!/usr/bin/env python3
"""CARC signature classification: unknown formats must never be guessed."""
import pathlib
import sys
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/"tools"))
from audit_ncch_carc import classify_header, inspect_size_header, inspect_possible_table_header
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
candidate=inspect_possible_table_header(bytes.fromhex("40a88101cf00000005a80378"),9332)
assert candidate["table_size_byte"]==207
assert candidate["candidate_table_bytes"]==416
assert candidate["payload_after_candidate_table"]==9332-8-416
assert inspect_possible_table_header(bytes.fromhex("40a88101cf000000"),100) is None
assert inspect_possible_table_header(bytes.fromhex("10a88101cf000000"),9332) is None
assert inspect_possible_table_header(b"\\x40",9332) is None
print("PASS: CARC header sizing and tentative coding-table bounds")
