#!/usr/bin/env python3
"""Pack user-authored parented, two-weight DRM1 animation into DRK1.

Only accepts *already converted, user-owned* mesh/rig/keyframe inputs.
Does not decode or redistribute Nintendo 3DS skeletal animation streams.
"""
import argparse
import json
import struct
from pathlib import Path

MAX_VERTICES = 2048
MAX_BONES = 16
MAX_FRAMES = 8


def mesh_vertices(mesh: bytes) -> int:
    if len(mesh) < 8 or mesh[:4] != b"DRM1":
        raise ValueError("Expected a DRM1 geometry file")
    vertices, triangles = struct.unpack_from("<HH", mesh, 4)
    if not 3 <= vertices <= MAX_VERTICES or not 1 <= triangles <= 2048:
        raise ValueError("Requires 3..2048 vertices and 1..2048 triangles")
    if len(mesh) != 8 + 6 * (vertices + triangles):
        raise ValueError("DRM1 mesh has an invalid exact byte length")
    return vertices


def integer(value, minimum, maximum):
    return type(value) is int and minimum <= value <= maximum


def demo_tail_wag(bones: int) -> list:
    """Four invented frames: oscillate bone one, others stay neutral."""
    if not 2 <= bones <= MAX_BONES:
        raise ValueError("Demo needs at least two correctly mapped bones")
    return [
        [[0, 0, 0, (phase if i == 1 else 0)] for i in range(bones)]
        for phase in (0, 32, 0, -32)
    ]


def pack(mesh: bytes, bones: list, influences: list,
         frames: list, ticks: int) -> bytes:
    vertices = mesh_vertices(mesh)
    if not isinstance(bones, list) or not 1 <= len(bones) <= MAX_BONES:
        raise ValueError("Define 1..16 bones")
    if not isinstance(influences, list) or len(influences) != vertices:
        raise ValueError("Provide one two-weight influence per original mesh vertex")
    if not integer(ticks, 1, 60):
        raise ValueError("Ticks per keyframe must be 1..60")
    if not isinstance(frames, list) or not 2 <= len(frames) <= MAX_FRAMES:
        raise ValueError("DRK1 needs 2..8 frames")
    for i, bone in enumerate(bones):
        if not isinstance(bone, dict):
            raise ValueError("Bone entry must be a dictionary")
        pivot, parent = bone.get("pivot"), bone.get("parent")
        if (not isinstance(pivot, list) or len(pivot) != 3 or
                any(not integer(v, -32768, 32767) for v in pivot)):
            raise ValueError("Bone pivots must contain three signed Q12 int16 values")
        if not integer(parent, -1, i - 1):
            raise ValueError("Parent must be -1/root or have smaller index")
    for influence in influences:
        if (not isinstance(influence, list) or len(influence) != 3 or
                not integer(influence[0], 0, len(bones) - 1) or
                not integer(influence[1], 0, len(bones) - 1) or
                not integer(influence[2], 0, 255)):
            raise ValueError("Influence needs valid [bone_a,bone_b,weight_a]")
    for frame in frames:
        if not isinstance(frame, list) or len(frame) != len(bones):
            raise ValueError("Each frame needs one pose per bone")
        for pose in frame:
            if (not isinstance(pose, list) or len(pose) != 4 or
                    any(not integer(v, -128, 127) for v in pose)):
                raise ValueError("Each [tx,ty,tz,yaw] pose must be signed int8")

    data = bytearray(b"DRK1")
    data.extend(struct.pack("<HBBBB", vertices, len(bones), len(frames), ticks, 0))
    for bone in bones:
        data.extend(struct.pack("<hhhBB", *bone["pivot"],
                                255 if bone["parent"] == -1 else bone["parent"], 0))
    for influence in influences:
        data.extend(struct.pack("<BBB", *influence))
    for frame in frames:
        for pose in frame:
            data.extend(struct.pack("<bbbb", *pose))
    assert len(data) == 10 + 8 * len(bones) + 3 * vertices + 4 * len(bones) * len(frames)
    return bytes(data)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mesh", type=Path, required=True)
    parser.add_argument("--skin-json", type=Path, required=True,
                        help="JSON with bones, influences and frames")
    parser.add_argument("--demo-tail-wag", action="store_true",
                        help="Override frames with invented oscillation of bone 1")
    parser.add_argument("--ticks", type=int, default=8)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    data = json.loads(args.skin_json.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Expected an object: bones, influences, frames")
    bones = data["bones"]
    frames = demo_tail_wag(len(bones)) if args.demo_tail_wag else data["frames"]
    result = pack(args.mesh.read_bytes(), bones, data["influences"], frames, args.ticks)
    args.output.write_bytes(result)
    print(f"Wrote {args.output}: {len(result)} bytes, "
          f"{len(bones)} bones, {len(frames)} frames")


if __name__ == "__main__":
    main()
