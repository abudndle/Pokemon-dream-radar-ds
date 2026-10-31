#!/usr/bin/env python3
"""Convert privately extracted BCLIM 3DS UI textures to DS RGB555 .spr.

Recognizes uncompressed CLIM pixel formats 0/1/2/3/5/6/7/8/9/12/13.
ETC1, ETC1A4, and HILO8 are not handled; unsupported files fail explicitly.
No original proprietary game data is distributed by this source file.
"""
import argparse
import struct
from pathlib import Path

BPP = {0: 1, 1: 1, 2: 1, 3: 2, 5: 2, 6: 3, 7: 2,
       8: 2, 9: 4, 12: 0.5, 13: 0.5}

class BclimError(ValueError):
    pass

def parse_header(blob):
    if len(blob) < 40:
        raise BclimError('BCLIM shorter than footer')
    magic, bom, hdrlen, version, total, count, section, sectionlen, width, height, fmt, size = struct.unpack_from(
        '<4sHHIII4sIHHII', blob, len(blob) - 40)
    if (magic != b'CLIM' or bom != 0xfeff or hdrlen != 20 or
        total != len(blob) or count != 1 or section != b'imag' or
        sectionlen != 16 or size != len(blob) - 40):
        raise BclimError('invalid BCLIM footer')
    if not (1 <= width <= 512 and 1 <= height <= 512 and width * height <= 512 * 512):
        raise BclimError('BCLIM dimensions out of bounds')
    if fmt not in BPP:
        raise BclimError(f'unsupported BCLIM pixel format {fmt}')
    # Actual 3DS BCLIM images use power-of-two *storage*, even for e.g.
    # visible 400x240 or 48x48 textures. The 8x8 Morton tiles span that
    # complete padded backing image, not merely the visible width.
    stored_width = 1 << (width - 1).bit_length()
    stored_height = 1 << (height - 1).bit_length()
    required = int(stored_width * stored_height * BPP[fmt])
    if size != required:
        raise BclimError('payload size incompatible with padded texture')
    return width, height, fmt, stored_width


def morton_index(x, y):
    return ((x & 1) | ((y & 1) << 1) | ((x & 2) << 1) |
            ((y & 2) << 2) | ((x & 4) << 2) | ((y & 4) << 3))


def _expand5(v):
    return (v << 3) | (v >> 2)


def rgba_at(raw, index, fmt):
    if fmt in (12, 13):
        nibble = (raw[index // 2] >> (4 * (index & 1))) & 15
        if fmt == 12:
            return nibble * 17, nibble * 17, nibble * 17, 255
        return 255, 255, 255, nibble * 17
    if fmt in (0, 1, 2):
        value = raw[index]
        if fmt == 0:
            return value, value, value, 255
        if fmt == 1:
            return 255, 255, 255, value
        lum = (value >> 4) * 17
        return lum, lum, lum, (value & 15) * 17
    if fmt == 6:
        b, g, r = raw[index * 3:index * 3 + 3]
        return r, g, b, 255
    if fmt == 9:
        a, b, g, r = raw[index * 4:index * 4 + 4]
        return r, g, b, a
    value = int.from_bytes(raw[index * 2:index * 2 + 2], 'little')
    if fmt == 3:  # LA8
        l, a = value >> 8, value & 255
        return l, l, l, a
    if fmt == 5:  # RGB565
        return _expand5((value >> 11) & 31), ((value >> 5) & 63) * 255 // 63, _expand5(value & 31), 255
    if fmt == 7:  # RGBA5551
        return _expand5((value >> 11) & 31), _expand5((value >> 6) & 31), _expand5((value >> 1) & 31), 255 if value & 1 else 0
    if fmt == 8:  # RGBA4444
        return ((value >> 12) & 15) * 17, ((value >> 8) & 15) * 17, ((value >> 4) & 15) * 17, (value & 15) * 17
    raise BclimError('unknown pixel codec')


def decode_bclim(blob):
    """Return width, height, and row-major RGBA pixels."""
    width, height, fmt, storage_width = parse_header(blob)
    rgba = bytearray(width * height * 4)
    tiles_w = storage_width // 8
    raw = memoryview(blob)[:-40]
    for y in range(height):
        for x in range(width):
            tile = (y // 8) * tiles_w + x // 8
            index = tile * 64 + morton_index(x & 7, y & 7)
            off = (y * width + x) * 4
            rgba[off:off + 4] = bytes(rgba_at(raw, index, fmt))
    return width, height, bytes(rgba)


def to_ds_spr(blob, max_width=256, max_height=192):
    """Emit the existing DS .spr format: <u16 w, u16 h, RGB555 pixels>.

    Black-transparent means the value 0 (not opaque black 0x8000).
    Downscale by nearest neighbor when a 3DS texture exceeds DS dimensions.
    """
    width, height, rgba = decode_bclim(blob)
    if not (1 <= max_width <= 256 and 1 <= max_height <= 192):
        raise BclimError('DS target dimensions outside screen bounds')
    if width > max_width or height > max_height:
        scale = min(max_width / width, max_height / height)
        out_w, out_h = max(1, int(width * scale)), max(1, int(height * scale))
    else:
        out_w, out_h = width, height
    out = bytearray(struct.pack('<HH', out_w, out_h))
    visible = 0
    for y in range(out_h):
        for x in range(out_w):
            sx = x * width // out_w
            sy = y * height // out_h
            src = (sy * width + sx) * 4
            r, g, b, a = rgba[src:src + 4]
            if a < 128:
                pixel = 0
            else:
                pixel = 0x8000 | (r >> 3) | ((g >> 3) << 5) | ((b >> 3) << 10)
                visible += 1
            out.extend(struct.pack('<H', pixel))
    if visible == 0:
        raise BclimError('empty fully transparent DS sprite')
    return bytes(out)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('bclim', type=Path, help='privately extracted original texture')
    p.add_argument('sprite', type=Path, help='destination DS sprite')
    args = p.parse_args()
    spr = to_ds_spr(args.bclim.read_bytes())
    args.sprite.parent.mkdir(parents=True, exist_ok=True)
    args.sprite.write_bytes(spr)
    w, h = struct.unpack_from('<HH', spr)
    print(f'Converted {args.bclim.name}: {w}x{h} DS RGB555 sprite')


if __name__ == '__main__':
    main()
