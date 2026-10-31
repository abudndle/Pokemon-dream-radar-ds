#!/usr/bin/env python3
"""Synthetic LZH8 vectors; no Nintendo game bytes included."""
import pathlib
import sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'tools'))
from decode_ncch_lzh8 import decompress_lzh8, Lzh8Error

def pack_table(values, width, payload_size):
    bits = ''.join(format(v, f'0{width}b') for v in values)
    assert len(bits) <= payload_size * 8
    bits = bits.ljust(payload_size * 8, '0')
    return bytes(int(bits[i:i + 8], 2) for i in range(0, len(bits), 8))

# 9-bit tree: root -> two inner nodes -> A, B, C, match(3).
# 5-bit tree: displacement symbol 2 -> normalized distance 3.
length_tree = b'\x02\x00' + pack_table([0, 0x180, 0x181, 65, 66, 67, 256], 9, 10)
disp_tree = b'\x00' + pack_table([0x18, 2, 2], 5, 3)
# '00'=A, '01'=B, '10'=C, '11'=match; '0'=displen2, '0'=dist3.
fixture = b'\x40\x06\x00\x00' + length_tree + disp_tree + bytes.fromhex('1b00')
assert decompress_lzh8(fixture) == b'ABCABC'
# Equal backreference length and distance previously produced an empty slice.
assert decompress_lzh8(fixture + b'\x00\x00') == b'ABCABC'
for bad in (b'', b'\x40\x00\x00\x00', fixture[:-1],
            b'\x10' + fixture[1:],
            fixture[:4] + b'\xff\xff' + fixture[6:],
            b'\x40\xff\xff\xff' + fixture[4:]):
    try:
        decompress_lzh8(bad)
    except Lzh8Error:
        pass
    else:
        raise AssertionError('Invalid synthetic LZH8 stream was accepted')
try:
    decompress_lzh8(fixture, max_output=5)
except Lzh8Error:
    pass
else:
    raise AssertionError('output limit not enforced')
print('PASS: LZH8 Huffman literals, equal-distance copy, truncation and bounds')
