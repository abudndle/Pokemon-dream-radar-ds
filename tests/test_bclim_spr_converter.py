#!/usr/bin/env python3
"""Synthetic BCLIM fixtures; no original game image bytes embedded."""
from pathlib import Path
import struct
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from convert_bclim_spr import BclimError, BPP, morton_index, parse_header, decode_bclim, to_ds_spr


def fixture(width=8, height=8, fmt=9, fill=None):
    stored_w = 1 << (width - 1).bit_length()
    stored_h = 1 << (height - 1).bit_length()
    assert fmt in BPP
    raw = bytearray(int(stored_w * stored_h * BPP[fmt]))
    if fill:
        for y in range(height):
            for x in range(width):
                index = ((y // 8) * (stored_w // 8) + x // 8) * 64 + morton_index(x % 8, y % 8)
                r, g, b, a = fill(x, y)
                if fmt == 9:
                    raw[index * 4:index * 4 + 4] = bytes((a, b, g, r))
                elif fmt == 5:
                    color = ((r >> 3) << 11) | ((g >> 2) << 5) | (b >> 3)
                    raw[index * 2:index * 2 + 2] = struct.pack('<H', color)
                elif fmt == 13:
                    raw[index // 2] |= (a // 17) << (4 * (index & 1))
    footer = struct.pack('<4sHHIII4sIHHII', b'CLIM', 0xfeff, 20,
                         0x02020000, len(raw) + 40, 1, b'imag', 16,
                         width, height, fmt, len(raw))
    return bytes(raw) + footer


def reject(raw):
    try:
        to_ds_spr(raw)
    except BclimError:
        return
    raise AssertionError('invalid texture was accepted')


b = fixture(fill=lambda x, y: (255, 0, 0, 255) if (x, y) == (1, 2) else
                            (0, 255, 0, 255) if (x, y) == (7, 7) else (0, 0, 0, 0))
assert parse_header(b) == (8, 8, 9, 8)
w, h, rgba = decode_bclim(b)
assert (w, h) == (8, 8)
assert rgba[(2 * 8 + 1) * 4:(2 * 8 + 1) * 4 + 4] == bytes((255, 0, 0, 255))
spr = to_ds_spr(b)
assert struct.unpack_from('<HH', spr) == (8, 8)
assert struct.unpack_from('<H', spr, 4 + (2 * 8 + 1) * 2)[0] == 0x801f
assert struct.unpack_from('<H', spr, 4 + (7 * 8 + 7) * 2)[0] == 0x83e0
assert struct.unpack_from('<H', spr, 4)[0] == 0

large = fixture(16, 16, fmt=5, fill=lambda x, y: (255, 0, 0, 255))
assert struct.unpack_from('<HH', to_ds_spr(large, 8, 8)) == (8, 8)
assert len(to_ds_spr(large, 8, 8)) == 4 + 8 * 8 * 2
alpha4 = fixture(fmt=13, fill=lambda x, y: (0, 0, 0, 255))
assert struct.unpack_from('<H', to_ds_spr(alpha4), 4)[0] == 0xffff

# 48x48 visible texture has a 64x64 backing image; the second tile row
# must use 64px, not 48px, as its source stride.
padded = fixture(48, 48, fill=lambda x, y: (255, 0, 0, 255)
                 if (x, y) == (7, 9) else (0, 0, 0, 0))
assert parse_header(padded) == (48, 48, 9, 64)
padded_spr = to_ds_spr(padded)
assert struct.unpack_from('<H', padded_spr, 4 + (9 * 48 + 7) * 2)[0] == 0x801f

reject(b'')
reject(b[:-1])
reject(b[:-40] + b'FAIL' + b[-36:])
reject(b[:-8] + struct.pack('<I', 11) + b[-4:])
reject(fixture())  # entirely transparent
reject(fixture(0, 8))
reject(fixture(8, 0))
reject(fixture(600, 8))
try:
    to_ds_spr(b, 0, 8)
except BclimError:
    pass
else:
    raise AssertionError('invalid DS dimensions accepted')
print('PASS: Morton tiling, power-of-two padding, RGB555/alpha, scaling and rejection')
