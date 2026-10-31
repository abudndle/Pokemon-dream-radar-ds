#!/usr/bin/env python3
import pathlib
import sys
import tempfile
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tools"))
from stage_pokemon_models import stage

OBJ = "v 0 0 0\nv 1 0 0\nv 0 1 0\nf 1 2 3\n"
with tempfile.TemporaryDirectory() as d:
    root=pathlib.Path(d)
    source=root/"exports"; source.mkdir()
    target=root/"Models"
    (source/"pokemon_00.obj").write_text(OBJ)
    (source/"pokemon_25.obj").write_text(OBJ)
    (source/"pokemon_26.obj").write_text(OBJ)
    (source/"pokemon_xx.obj").write_text(OBJ)
    report=stage(source,target)
    assert [m["file"] for m in report["models"]]==["pokemon_00.drm","pokemon_25.drm"]
    assert (target/"pokemon_00.drm").read_bytes()[:4]==b"DRM1"
    assert not (target/"pokemon_26.drm").exists()
    assert (target/"model_manifest.json").exists()
    original=(target/"pokemon_00.drm").read_bytes()
    (source/"pokemon_25.obj").write_text("invalid model\n")
    try:
        stage(source,target)
    except ValueError:
        pass
    else:
        raise AssertionError("Invalid model unexpectedly accepted")
    assert (target/"pokemon_00.drm").read_bytes()==original
    (source/"pokemon_00.obj").unlink()
    (source/"pokemon_25.obj").unlink()
    try:
        stage(source,target)
    except ValueError:
        pass
    else:
        raise AssertionError("Empty model batch accepted")
print("PASS: private model batch staging, naming, DRM1 output, and reject-before-write")
