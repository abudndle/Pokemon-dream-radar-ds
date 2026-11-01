#!/usr/bin/env python3
import hashlib
import json
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tools"))
from verify_staged_models import verify

with tempfile.TemporaryDirectory() as temporary:
    root = pathlib.Path(temporary)
    for filename, manifest, magic, extension in (
        ("pokemon_00.drm", "model_manifest.json", "DRM1", ".drm"),
        ("pokemon_25.drk", "gltf_animation_manifest.json", "DRK1", ".drk"),
    ):
        payload = magic.encode() + b"fixture"
        (root / filename).write_bytes(payload)
        report = {"format": magic, "models": [{"file": filename,
                  "bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}]}
        (root / manifest).write_text(json.dumps(report))
        assert verify(root, manifest, magic, extension) == 1
        (root / filename).write_bytes(payload + b"x")
        try:
            verify(root, manifest, magic, extension)
        except ValueError:
            pass
        else:
            raise AssertionError("Tampered staged asset accepted")
        (root / filename).write_bytes(payload)
        report["models"].append(report["models"][0])
        (root / manifest).write_text(json.dumps(report))
        try:
            verify(root, manifest, magic, extension)
        except ValueError:
            pass
        else:
            raise AssertionError("Duplicate staged asset accepted")
        (root / filename).unlink()
        (root / manifest).unlink()
print("PASS: staged model and animation integrity checks")
