#!/usr/bin/env python3
"""Pack user-owned UV coordinates and opaque RGB555 texels into DRT1.

No proprietary game files or assets are distributed by this converter.
"""
import argparse
import json
import struct
from pathlib import Path


def pack(mesh_bytes: bytes, uvs: list, texels: bytes, width: int, height: int) -> bytes:
    if len(mesh_bytes) < 8 or mesh_bytes[:4] != b"DRM1":
        raise ValueError("expected DRM1 model")
    vertices, triangles = struct.unpack_from("<HH", mesh_bytes, 4)
    if vertices < 3 or triangles < 1 or len(mesh_bytes) != 8 + 6 * (vertices + triangles):
        raise ValueError("invalid DRM1 mesh size or count")
    if not 1 <= width <= 64 or not 1 <= height <= 64:
        raise ValueError("DRT1 texture dimensions must be 1..64")
    if not isinstance(uvs, list) or len(uvs) != vertices:
        raise ValueError("one UV pair required per DRM1 vertex")
    if len(texels) != width * height * 2:
        raise ValueError("expected exactly width*height little-endian RGB555 pixels")
    if any(not (value & 0x8000) for (value,) in struct.iter_unpack("<H", texels)):
        raise ValueError("every RGB555 texel must be opaque (bit 15 set)")
    pairs = bytearray()
    for uv in uvs:
        if (not isinstance(uv, list) or len(uv) != 2 or
                any(type(v) is not int or not 0 <= v <= 4096 for v in uv)):
            raise ValueError("UV pairs must contain Q12 integers in 0..4096")
        pairs += struct.pack("<HH", *uv)
    return b"DRT1" + struct.pack("<BBH", width, height, vertices) + pairs + texels


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mesh", type=Path, required=True, help="DRM1 geometry file")
    parser.add_argument("--uv-json", type=Path, required=True, help="JSON array of Q12 [u,v] per vertex")
    parser.add_argument("--pixels-rgb555", type=Path, required=True, help="raw opaque little-endian RGB555 pixels")
    parser.add_argument("--width", type=int, required=True)
    parser.add_argument("--height", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    data = pack(args.mesh.read_bytes(), json.loads(args.uv_json.read_text()),
                args.pixels_rgb555.read_bytes(), args.width, args.height)
    args.output.write_bytes(data)
    print(f"Wrote {args.output}: {len(data)} bytes")


if __name__ == "__main__":
    main()
