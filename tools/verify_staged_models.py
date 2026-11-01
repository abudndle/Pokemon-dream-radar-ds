#!/usr/bin/env python3
"""Verify private staged DRM1/DRK1 assets before copying them to SD storage.

A manifest proves conversion integrity only; it does not prove Nintendo
ownership, original 3DS provenance, or visual fidelity.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path

NAME = re.compile(r"pokemon_(0[0-9]|1[0-9]|2[0-5])\.(drm|drk)\Z")


def verify(directory: Path, manifest: str, expected_format: str, extension: str):
    report = json.loads((directory / manifest).read_text(encoding="utf-8"))
    if report.get("format") != expected_format or not isinstance(report.get("models"), list):
        raise ValueError("Invalid staged asset manifest format")
    seen = set()
    for entry in report["models"]:
        if not isinstance(entry, dict):
            raise ValueError("Invalid staged asset entry")
        name = entry.get("file")
        if (not isinstance(name, str) or not NAME.fullmatch(name)
                or not name.endswith(extension) or name in seen):
            raise ValueError("Invalid or duplicate staged filename")
        seen.add(name)
        path = directory / name
        if path.is_symlink() or not path.is_file():
            raise ValueError("Missing or symlinked staged asset: " + name)
        payload = path.read_bytes()
        if payload[:4] != expected_format.encode("ascii"):
            raise ValueError("Invalid asset magic: " + name)
        digest = entry.get("sha256")
        size = entry.get("bytes")
        if (type(size) is not int or size != len(payload)
                or not isinstance(digest, str) or len(digest) != 64
                or digest != hashlib.sha256(payload).hexdigest()):
            raise ValueError("Staged asset checksum mismatch: " + name)
    if not seen:
        raise ValueError("Empty staged asset manifest")
    return len(seen)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--kind", choices=("mesh", "skin"), required=True)
    args = parser.parse_args()
    kind = {"mesh": ("model_manifest.json", "DRM1", ".drm"),
            "skin": ("gltf_animation_manifest.json", "DRK1", ".drk")}
    count = verify(args.directory, *kind[args.kind])
    print(f"PASS: verified {count} staged {args.kind} assets")


if __name__ == "__main__":
    main()
