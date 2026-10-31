#!/usr/bin/env python3
"""Convert user-owned per-vertex keyframes into a portable DRA1 animation sidecar."""
import argparse
import json
import struct
from pathlib import Path

MAX_VERTICES = 2048
MAX_FRAMES = 8


def vertex_count(mesh: bytes) -> int:
    if len(mesh) < 8 or mesh[:4] != b"DRM1":
        raise ValueError("Expected an existing DRM1 mesh")
    vertices, triangles = struct.unpack_from("<HH", mesh, 4)
    if not 3 <= vertices <= MAX_VERTICES or not 1 <= triangles <= 2048:
        raise ValueError("DRA1 supports 3..2048 vertices and valid triangle counts")
    if len(mesh) != 8 + 6 * (vertices + triangles):
        raise ValueError("Truncated or oversized DRM1 mesh")
    return vertices


def idle_bob(vertices: int) -> list:
    """Four evenly timed, optional global translation poses in 1/256 units."""
    return [[[0, offset, 0] for _ in range(vertices)]
            for offset in (0, 64, 0, -64)]


def pack(mesh: bytes, frames: list, ticks: int) -> bytes:
    vertices = vertex_count(mesh)
    if type(ticks) is not int or not 1 <= ticks <= 60:
        raise ValueError("Each keyframe duration must be 1..60 game ticks")
    if not isinstance(frames, list) or not 2 <= len(frames) <= MAX_FRAMES:
        raise ValueError("DRA1 requires 2..8 keyframes")
    payload = bytearray()
    for frame in frames:
        if not isinstance(frame, list) or len(frame) != vertices:
            raise ValueError("Each frame needs exactly one XYZ delta per mesh vertex")
        for xyz in frame:
            if (not isinstance(xyz, list) or len(xyz) != 3 or
                    any(type(v) is not int or not -128 <= v <= 127 for v in xyz)):
                raise ValueError("Each XYZ delta must be 3 signed bytes (-128..127)")
            payload.extend(struct.pack("<bbb", *xyz))
    return b"DRA1" + struct.pack("<HBB", vertices, len(frames), ticks) + payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mesh", type=Path, required=True,
                        help="Existing converted DRM1 geometry")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--keyframes-json", type=Path,
                       help="JSON: frame list -> vertex list -> [dx,dy,dz]")
    group.add_argument("--idle-bob", action="store_true",
                       help="Generate a simple 4-pose vertical bob (not original animation)")
    parser.add_argument("--ticks", type=int, default=8,
                        help="Game ticks between keyframes (1..60; default 8)")
    parser.add_argument("--output", type=Path, required=True,
                        help="Private output, e.g. pokemon_00.dra")
    args = parser.parse_args()
    mesh = args.mesh.read_bytes()
    frames = idle_bob(vertex_count(mesh)) if args.idle_bob else json.loads(
        args.keyframes_json.read_text(encoding="utf-8"))
    packed = pack(mesh, frames, args.ticks)
    args.output.write_bytes(packed)
    print(f"Wrote {args.output}: {len(packed)} bytes; "
          f"{len(frames)} frames, {args.ticks} ticks/frame")


if __name__ == "__main__":
    main()
