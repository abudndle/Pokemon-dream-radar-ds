#!/usr/bin/env python3
"""Convert a user-extracted OBJ mesh to a compact DS-oriented triangle stream.

This does not extract 3DS formats, supply original models, or implement the
Nintendo DS GPU renderer. Use only with meshes legitimately exported from the
original files; metadata records that provenance is unverified.
"""
import argparse
import json
import math
import struct
from pathlib import Path

MAGIC = b"DRM1"
FIXED_SCALE = 4096
MAX_TRIANGLES = 2048

def convert(text, max_triangles=MAX_TRIANGLES):
    vertices = []
    faces = []
    for lineno, raw in enumerate(text.splitlines(), 1):
        line = raw.partition("#")[0].strip()
        if not line:
            continue
        words = line.split()
        if words[0] == "v":
            if len(words) != 4:
                raise ValueError(f"Line {lineno}: expected 3 vertex coordinates")
            xyz = tuple(float(s) for s in words[1:])
            if not all(math.isfinite(x) and -8 <= x < 8 for x in xyz):
                raise ValueError(f"Line {lineno}: coordinate outside signed Q12 range")
            vertices.append(tuple(round(x * FIXED_SCALE) for x in xyz))
        elif words[0] == "f":
            if len(words) < 4:
                raise ValueError(f"Line {lineno}: face needs at least 3 vertices")
            indices = []
            for ref in words[1:]:
                value = ref.split("/")[0]
                if not value or not value.lstrip("-").isdigit():
                    raise ValueError(f"Line {lineno}: malformed vertex index")
                idx = int(value)
                if idx == 0:
                    raise ValueError(f"Line {lineno}: OBJ indices cannot be zero")
                idx = idx - 1 if idx > 0 else len(vertices) + idx
                if idx < 0 or idx >= len(vertices):
                    raise ValueError(f"Line {lineno}: vertex index out of range")
                indices.append(idx)
            for k in range(1, len(indices) - 1):
                tri = (indices[0], indices[k], indices[k + 1])
                if len(set(tri)) != 3:
                    raise ValueError(f"Line {lineno}: degenerate index triangle")
                a, b, c = (vertices[i] for i in tri)
                ab = tuple(b[j] - a[j] for j in range(3))
                ac = tuple(c[j] - a[j] for j in range(3))
                cross = (ab[1]*ac[2]-ab[2]*ac[1],
                         ab[2]*ac[0]-ab[0]*ac[2],
                         ab[0]*ac[1]-ab[1]*ac[0])
                if cross == (0, 0, 0):
                    raise ValueError(f"Line {lineno}: zero-area quantized triangle")
                faces.append(tri)
                if len(faces) > max_triangles:
                    raise ValueError("Triangle budget exceeded")
    if not vertices or not faces or len(vertices) > 65535:
        raise ValueError("Mesh must have vertices and faces within index limits")
    if any(any(q < -32768 or q > 32767 for q in xyz) for xyz in vertices):
        raise ValueError("Vertex outside signed Q12 range after rounding")
    blob = bytearray(struct.pack("<4sHH", MAGIC, len(vertices), len(faces)))
    for vertex in vertices:
        blob.extend(struct.pack("<hhh", *vertex))
    for face in faces:
        blob.extend(struct.pack("<HHH", *face))
    return bytes(blob), {"vertices": len(vertices), "triangles": len(faces),
                         "fixed_scale": FIXED_SCALE,
                         "source_provenance": "not_verified",
                         "gpu_compatibility": "not_verified"}

def main():
    p = argparse.ArgumentParser()
    p.add_argument("input_obj", type=Path)
    p.add_argument("output_mesh", type=Path)
    a = p.parse_args()
    blob, info = convert(a.input_obj.read_text(encoding="utf-8"))
    a.output_mesh.parent.mkdir(parents=True, exist_ok=True)
    a.output_mesh.write_bytes(blob)
    a.output_mesh.with_suffix(a.output_mesh.suffix + ".json").write_text(
        json.dumps(info, indent=2) + "\n", encoding="utf-8")
    print(f"Converted {info['vertices']} vertices and {info['triangles']} triangles (not DS-verified)")

if __name__ == "__main__":
    main()
