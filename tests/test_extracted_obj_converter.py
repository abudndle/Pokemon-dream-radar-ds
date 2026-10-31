#!/usr/bin/env python3
import pathlib
import struct
import sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tools"))
from convert_extracted_obj import convert, MAGIC

triangle = "v 0 0 0\nv 1 0 0\nv 0 1 0\nf 1 2 3\n"
data, info = convert(triangle)
assert struct.unpack_from("<4sHH", data) == (MAGIC, 3, 1)
assert struct.unpack_from("<hhh", data, 8) == (0, 0, 0)
assert struct.unpack_from("<hhh", data, 14) == (4096, 0, 0)
assert struct.unpack_from("<HHH", data, 26) == (0, 1, 2)
assert len(data) == 8 + 3 * 6 + 6
assert info["source_provenance"] == "not_verified"
assert info["gpu_compatibility"] == "not_verified"
quad = "v 0 0 0\nv 1 0 0\nv 1 1 0\nv 0 1 0\nf -4 -3 -2 -1\n"
data, info = convert(quad)
assert info["triangles"] == 2
assert struct.unpack_from("<HHHHHH", data, 8 + 4 * 6) == (0, 1, 2, 0, 2, 3)
for bad in ("f 1 2 3", "v nan 0 0\nf 1 1 1",
            "v 8 0 0\nv 0 0 0\nv 0 1 0\nf 1 2 3",
            "v 0 0 0\nv 1 0 0\nv 0 1 0\nf 1 2 2",
            "v 0 0 0\nv 1 0 0\nv 0 1 0\nf 0 2 3"):
    try:
        convert(bad)
    except ValueError:
        pass
    else:
        raise AssertionError("Invalid OBJ mesh accepted")
try:
    convert(quad, max_triangles=1)
except ValueError:
    pass
else:
    raise AssertionError("Triangle budget was not enforced")
print("PASS: bounded Q12 mesh conversion, triangulation and invalid input rejection")
