#!/usr/bin/env python3
"""Inventory locally supplied original Dream Radar model candidates.

This tool does not extract copyrighted models, decode geometry, or claim DS
compatibility. It makes an auditable list of model source files available to
the porter, with content hashes and deterministic relative paths.
"""
import argparse
import hashlib
import json
from pathlib import Path

MODEL_SUFFIXES = frozenset({".bcmdl", ".bcres", ".bch", ".cmb", ".cgfx"})

def inventory(root: Path):
    if not root.is_dir():
        raise ValueError(f"Model source directory is missing: {root}")
    entries = []
    for path in sorted(root.rglob("*")):
        if path.is_symlink() or not path.is_file() or path.suffix.lower() not in MODEL_SUFFIXES:
            continue
        h = hashlib.sha256()
        size = 0
        with path.open("rb") as stream:
            for part in iter(lambda: stream.read(1024 * 1024), b""):
                size += len(part)
                h.update(part)
        entries.append({"path": path.relative_to(root).as_posix(),
                        "bytes": size, "sha256": h.hexdigest(),
                        "extension": path.suffix.lower(),
                        "status": "candidate_only_not_decoded"})
    return {"model_candidates": len(entries), "models_converted": 0,
            "models_verified_on_ds": 0, "files": entries,
            "warning": "Filename extensions are not proof of valid original 3D models."}

def compare_inventories(expected, actual):
    """Compare only input model identities; never mistake them for decoded art."""
    before = {entry["path"]: (entry["bytes"], entry["sha256"])
              for entry in expected["files"]}
    after = {entry["path"]: (entry["bytes"], entry["sha256"])
             for entry in actual["files"]}
    return {"added": sorted(after.keys() - before.keys()),
            "removed": sorted(before.keys() - after.keys()),
            "changed": sorted(path for path in before.keys() & after.keys()
                              if before[path] != after[path])}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("source_dir", type=Path, help="Private extracted model directory")
    parser.add_argument("output_json", type=Path, help="Output manifest; avoid committing private model files")
    parser.add_argument("--compare", type=Path, help="Compare against a previous inventory JSON")
    args = parser.parse_args()
    result = inventory(args.source_dir)
    if args.compare is not None:
        previous = json.loads(args.compare.read_text(encoding="utf-8"))
        changes = compare_inventories(previous, result)
        result["changes_since_previous"] = changes
        print("Model source changes:", changes)
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"Indexed {result['model_candidates']} model candidates; zero converted or verified.")

if __name__ == "__main__":
    main()
