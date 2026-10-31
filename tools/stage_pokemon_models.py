#!/usr/bin/env python3
"""Batch-stage privately exported Pokémon OBJ files for Dream Radar DS/DSi.

Only input files named pokemon_00.obj..pokemon_25.obj are recognized. No
copyrighted assets are shipped or downloaded by this script.
"""
import argparse
import json
import re
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
    for name, blob, info in converted:
        target = output / (name + ".drm")
        target.write_bytes(blob)
        report["models"].append({"file": target.name,
                                 "vertices": info["vertices"],
                                 "triangles": info["triangles"]})
    (output / "model_manifest.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8")
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
