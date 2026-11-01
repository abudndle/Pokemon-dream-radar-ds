#!/usr/bin/env python3
"""Batch-stage privately exported Pokémon OBJ files for Dream Radar DS/DSi.

Only input files named pokemon_00.obj..pokemon_25.obj are recognized. No
copyrighted assets are shipped or downloaded by this script.
"""
import argparse
import hashlib
import json
import re
import tempfile
import os
from pathlib import Path
from convert_extracted_obj import convert

NAME = re.compile(r"pokemon_(0[0-9]|1[0-9]|2[0-5])\.obj\Z")

def stage(source: Path, output: Path):
    if not source.is_dir():
        raise ValueError("Input directory does not exist")
    candidates = sorted(p for p in source.iterdir() if p.is_file() and NAME.fullmatch(p.name))
    if not candidates:
        raise ValueError("No correctly named pokemon_00.obj..pokemon_25.obj files")
    # Convert *all* assets before publishing any; one invalid export must not
    # create a half-updated model collection.
    converted = []
    for p in candidates:
        blob, info = convert(p.read_text(encoding="utf-8"))
        converted.append((p.stem, blob, info))
    output.mkdir(parents=True, exist_ok=True)
    report = {"format": "DRM1", "source_provenance": "not_verified",
              "models": []}
    # Stage to a sibling directory; never publish a partially converted set.
    with tempfile.TemporaryDirectory(prefix=".dream-radar-models-", dir=output.parent) as temp:
        staged = Path(temp)
        for name, blob, info in converted:
            target = staged / (name + ".drm")
            target.write_bytes(blob)
            report["models"].append({"file": target.name,
                                     "sha256": hashlib.sha256(blob).hexdigest(),
                                     "bytes": len(blob),
                                     "vertices": info["vertices"],
                                     "triangles": info["triangles"]})
        (staged / "model_manifest.json").write_text(
            json.dumps(report, indent=2) + "\n", encoding="utf-8")
        # Replace each file atomically on the same filesystem. A failed
        # conversion above leaves the previously published set untouched.
        for item in sorted(staged.iterdir(), key=lambda x: x.name == "model_manifest.json"):
            os.replace(item, output / item.name)
    return report

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="folder of private pokemon_XX.obj files")
    parser.add_argument("output", type=Path, help="staging Models directory")
    args = parser.parse_args()
    result = stage(args.source, args.output)
    print(f"Staged {len(result['models'])} model(s) for DreamRadarDSi/Models/")

if __name__ == "__main__":
    main()
