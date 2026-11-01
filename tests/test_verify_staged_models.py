#!/usr/bin/env python3
import hashlib
import json
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tools"))
from verify_staged_models import verify, verify_pairs

def fixture(magic, vertices=3):
    if magic == "DRM1":
        coords = b"".join((i * 4096).to_bytes(2, "little", signed=True)
                          + (4096 if i == 2 else 0).to_bytes(2, "little", signed=True)
                          + bytes(2) for i in range(vertices))
        return (b"DRM1" + vertices.to_bytes(2, "little") + bytes([1, 0])
                + coords + bytes([0, 0, 1, 0, 2, 0]))
    return (b"DRK1" + vertices.to_bytes(2, "little") + bytes([1, 2, 4, 0])
            + bytes(6) + bytes([255, 0])
            + bytes([0, 0, 255]) * vertices + bytes(8))

with tempfile.TemporaryDirectory() as temporary:
    root = pathlib.Path(temporary)
    for filename, manifest, magic, extension in (
        ("pokemon_00.drm", "model_manifest.json", "DRM1", ".drm"),
        ("pokemon_25.drk", "gltf_animation_manifest.json", "DRK1", ".drk"),
    ):
        payload = fixture(magic)
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

with tempfile.TemporaryDirectory() as temporary:
    root = pathlib.Path(temporary)
    meshes, skins = root / "meshes", root / "skins"
    meshes.mkdir()
    skins.mkdir()
    for folder, filename, magic in ((meshes, "pokemon_00.drm", "DRM1"),
                                    (skins, "pokemon_00.drk", "DRK1")):
        payload = fixture(magic)
        (folder / filename).write_bytes(payload)
        manifest = "model_manifest.json" if magic == "DRM1" else "gltf_animation_manifest.json"
        (folder / manifest).write_text(json.dumps({"format": magic, "models": [
            {"file": filename, "bytes": len(payload),
             "sha256": hashlib.sha256(payload).hexdigest()}]}))
    assert verify_pairs(skins, meshes) == 1
    payload = fixture("DRM1", 4)
    (meshes / "pokemon_00.drm").write_bytes(payload)
    report = json.loads((meshes / "model_manifest.json").read_text())
    report["models"][0].update(bytes=len(payload), sha256=hashlib.sha256(payload).hexdigest())
    (meshes / "model_manifest.json").write_text(json.dumps(report))
    try:
        verify_pairs(skins, meshes)
    except ValueError as exc:
        assert "Vertex count mismatch" in str(exc)
    else:
        raise AssertionError("Incompatible mesh and skeleton accepted")
print("PASS: matching mesh/skeleton pair validation")

with tempfile.TemporaryDirectory() as temporary:
    root = pathlib.Path(temporary)
    name = "pokemon_00.drk"
    manifest = "gltf_animation_manifest.json"
    valid = fixture("DRK1")
    for mutation, error in ((lambda p: p.__setitem__(16, 0), "bone hierarchy"),
                            (lambda p: p.__setitem__(18, 1), "skin influence")):
        payload = bytearray(valid)
        mutation(payload)
        (root / name).write_bytes(payload)
        (root / manifest).write_text(json.dumps({"format": "DRK1", "models": [
            {"file": name, "bytes": len(payload),
             "sha256": hashlib.sha256(payload).hexdigest()}]}))
        try:
            verify(root, manifest, "DRK1", ".drk")
        except ValueError as exc:
            assert error in str(exc), str(exc)
        else:
            raise AssertionError("Invalid DRK1 " + error + " accepted")
print("PASS: malformed skeletal hierarchy and influence rejection")

with tempfile.TemporaryDirectory() as temporary:
    root = pathlib.Path(temporary)
    name = "pokemon_00.drm"
    manifest = "model_manifest.json"
    payload = bytearray(fixture("DRM1"))
    payload[8 + 6 * 2 + 2:8 + 6 * 2 + 4] = bytes(2)
    (root / name).write_bytes(payload)
    (root / manifest).write_text(json.dumps({"format": "DRM1", "models": [
        {"file": name, "bytes": len(payload),
         "sha256": hashlib.sha256(payload).hexdigest()}]}))
    try:
        verify(root, manifest, "DRM1", ".drm")
    except ValueError as exc:
        assert "Degenerate" in str(exc), str(exc)
    else:
        raise AssertionError("Zero-area DRM1 triangle accepted")
print("PASS: degenerate mesh triangle rejection")

with tempfile.TemporaryDirectory() as temporary:
    root = pathlib.Path(temporary)
    name = "pokemon_00.drm"
    manifest = "model_manifest.json"
    payload = bytearray(fixture("DRM1"))
    payload[6:8] = bytes([2, 0])
    payload.extend(bytes([2, 0, 0, 0, 1, 0]))
    (root / name).write_bytes(payload)
    (root / manifest).write_text(json.dumps({"format": "DRM1", "models": [
        {"file": name, "bytes": len(payload),
         "sha256": hashlib.sha256(payload).hexdigest()}]}))
    try:
        verify(root, manifest, "DRM1", ".drm")
    except ValueError as exc:
        assert "Duplicate" in str(exc), str(exc)
    else:
        raise AssertionError("Repeated DRM1 face accepted")
print("PASS: duplicate mesh face rejection")

with tempfile.TemporaryDirectory() as temporary:
    root = pathlib.Path(temporary)
    name = "pokemon_00.drk"
    manifest = "gltf_animation_manifest.json"
    payload = bytearray(fixture("DRK1"))
    payload[18:21] = bytes([0, 0, 0])
    (root / name).write_bytes(payload)
    (root / manifest).write_text(json.dumps({"format": "DRK1", "models": [
        {"file": name, "bytes": len(payload),
         "sha256": hashlib.sha256(payload).hexdigest()}]}))
    try:
        verify(root, manifest, "DRK1", ".drk")
    except ValueError as exc:
        assert "zero-weight" in str(exc), str(exc)
    else:
        raise AssertionError("Redundant zero-weight influence accepted")
print("PASS: redundant zero-weight influence rejection")

with tempfile.TemporaryDirectory() as temporary:
    root = pathlib.Path(temporary)
    name = "pokemon_00.drk"
    manifest = "gltf_animation_manifest.json"
    payload = bytearray(fixture("DRK1"))
    payload[17] = 1  # Reserved byte of the first bone must remain zero.
    (root / name).write_bytes(payload)
    (root / manifest).write_text(json.dumps({"format": "DRK1", "models": [
        {"file": name, "bytes": len(payload),
         "sha256": hashlib.sha256(payload).hexdigest()}]}))
    try:
        verify(root, manifest, "DRK1", ".drk")
    except ValueError as exc:
        assert "bone hierarchy" in str(exc), str(exc)
    else:
        raise AssertionError("Nonzero DRK1 bone reserved byte accepted")
print("PASS: reserved skeleton bytes rejected")

with tempfile.TemporaryDirectory() as temporary:
    root = pathlib.Path(temporary)
    payload = fixture("DRM1")
    name = "pokemon_00.drm"
    (root / name).write_bytes(payload)
    manifest = root / "model_manifest.json"
    real_manifest = root / "original_manifest.json"
    real_manifest.write_text(json.dumps({"format": "DRM1", "models": [
        {"file": name, "bytes": len(payload),
         "sha256": hashlib.sha256(payload).hexdigest()}]}))
    manifest.symlink_to(real_manifest)
    try:
        verify(root, manifest.name, "DRM1", ".drm")
    except ValueError as exc:
        assert "symlinked staged manifest" in str(exc), str(exc)
    else:
        raise AssertionError("Symlinked staged manifest accepted")
print("PASS: symlinked manifest rejection")

with tempfile.TemporaryDirectory() as temporary:
    root = pathlib.Path(temporary)
    for invalid in ([], None, 7, "DRM1"):
        (root / "model_manifest.json").write_text(json.dumps(invalid))
        try:
            verify(root, "model_manifest.json", "DRM1", ".drm")
        except ValueError as exc:
            assert "manifest format" in str(exc), str(exc)
        else:
            raise AssertionError("Non-object staged manifest accepted")
print("PASS: non-object manifest roots rejected")

with tempfile.TemporaryDirectory() as temporary:
    root = pathlib.Path(temporary)
    (root / "model_manifest.json").write_text(
        '{"format":"DRM1","format":"DRK1","models":[]}')
    try:
        verify(root, "model_manifest.json", "DRM1", ".drm")
    except ValueError as exc:
        assert "Duplicate staged manifest JSON key" in str(exc), str(exc)
    else:
        raise AssertionError("Duplicate manifest JSON keys accepted")
print("PASS: duplicate manifest JSON keys rejected")

with tempfile.TemporaryDirectory() as temporary:
    root = pathlib.Path(temporary)
    (root / "model_manifest.json").write_bytes(b" " * (1024 * 1024 + 1))
    try:
        verify(root, "model_manifest.json", "DRM1", ".drm")
    except ValueError as exc:
        assert "size limit" in str(exc), str(exc)
    else:
        raise AssertionError("Oversized manifest accepted")
print("PASS: oversized staged manifests rejected")
