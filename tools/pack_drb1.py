#!/usr/bin/env python3
"""Pack user-authored rigid part animations for existing DRM1 Pokémon meshes.

This does not decode 3DS skeletal files or distribute proprietary assets.
"""
import argparse
import json
import struct
from pathlib import Path

MAX_VERTICES = 2048
MAX_GROUPS = 16
MAX_FRAMES = 8


def mesh_vertices(mesh: bytes) -> int:
    if len(mesh) < 8 or mesh[:4] != b"DRM1":
        raise ValueError("Expected a converted DRM1 geometry file")
    n, triangles = struct.unpack_from("<HH", mesh, 4)
    if not 3 <= n <= MAX_VERTICES or not 1 <= triangles <= 2048:
        raise ValueError("DRB1 requires 3..2048 vertices and valid triangle count")
    if len(mesh) != 8 + 6 * (n + triangles):
        raise ValueError("DRM1 input must have exact geometry length")
    return n


def valid_int(value, low, high):
    return type(value) is int and low <= value <= high


def demo_wag(group_count: int):
    """Placeholder motion: rotate part #1 slightly, all other parts still."""
    if not 2 <= group_count <= MAX_GROUPS:
        raise ValueError("Demo wag needs at least two body parts")
    return [
        [[0, 0, 0, (phase if i == 1 else 0)]
         for i in range(group_count)]
        for phase in (0, 24, 0, -24)
    ]


def pack(mesh: bytes, pivots: list, owners: list, frames: list, ticks: int) -> bytes:
    vertices = mesh_vertices(mesh)
    if not isinstance(pivots, list) or not 1 <= len(pivots) <= MAX_GROUPS:
        raise ValueError("Define 1..16 part pivots")
    if not isinstance(owners, list) or len(owners) != vertices:
        raise ValueError("Every DRM1 vertex needs exactly one part ID")
    if type(ticks) is not int or not 1 <= ticks <= 60:
        raise ValueError("Ticks per keyframe must be 1..60")
    if not isinstance(frames, list) or not 2 <= len(frames) <= MAX_FRAMES:
        raise ValueError("DRB1 requires 2..8 poses")
    for pivot in pivots:
        if (not isinstance(pivot, list) or len(pivot) != 3 or
                any(not valid_int(v, -32768, 32767) for v in pivot)):
            raise ValueError("Each pivot must be three signed Q12 int16 coordinates")
    if any(not valid_int(v, 0, len(pivots) - 1) for v in owners):
        raise ValueError("Group IDs must be valid zero-based integers")
    for frame in frames:
        if not isinstance(frame, list) or len(frame) != len(pivots):
            raise ValueError("Each frame needs one [tx,ty,tz,yaw] pose per group")
        for pose in frame:
            if (not isinstance(pose, list) or len(pose) != 4 or
                    any(not valid_int(v, -128, 127) for v in pose)):
                raise ValueError("Each pose must contain four signed byte integers")
    out = bytearray(b"DRB1")
    out += struct.pack("<HBBBB", vertices, len(pivots), len(frames), ticks, 0)
    for pivot in pivots:
        out += struct.pack("<hhh", *pivot)
    out += bytes(owners)
    for frame in frames:
        for pose in frame:
            out += struct.pack("<bbbb", *pose)
    assert len(out) == 10 + 6 * len(pivots) + vertices + 4 * len(frames) * len(pivots)
    return bytes(out)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mesh", type=Path, required=True, help="Private DRM1 mesh")
    parser.add_argument("--parts-json", type=Path, required=True,
                        help="JSON with pivots, owners and frames (unless --demo-wag)")
    parser.add_argument("--demo-wag", action="store_true",
                        help="Generate placeholder oscillation of part 1; still needs part mapping")
    parser.add_argument("--ticks", type=int, default=8)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    data = json.loads(args.parts_json.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Expected JSON object with pivots, owners, frames")
    pivots, owners = data["pivots"], data["owners"]
    frames = demo_wag(len(pivots)) if args.demo_wag else data["frames"]
    output = pack(args.mesh.read_bytes(), pivots, owners, frames, args.ticks)
    args.output.write_bytes(output)
    print(f"Wrote {args.output} ({len(output)} bytes, "
          f"{len(pivots)} groups, {len(frames)} keyframes)")


if __name__ == "__main__":
    main()
