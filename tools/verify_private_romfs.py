#!/usr/bin/env python3
"""Validate a private Dream Radar NCCH against a metadata-only RomFS manifest.

No resource contents are extracted, uploaded or written. The only optional
output is a metadata/digest report outside the Git working tree.
"""
import argparse
import hashlib
import json
import os
import tempfile
from collections import Counter
from pathlib import Path

from inventory_ncch_romfs import audit

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "docs" / "original_romfs_manifest.json"


def _safe_virtual_path(value):
    if not isinstance(value, str) or not value.startswith("/") or value.startswith("//"):
        raise ValueError("RomFS path must be an absolute virtual path")
    parts = value[1:].split("/")
    if not all(part and part not in (".", "..") and "\\" not in part and "\x00" not in part
               for part in parts):
        raise ValueError("Invalid RomFS virtual path")
    return value


def _index(entries):
    if not isinstance(entries, list):
        raise ValueError("RomFS files must be a list")
    result = {}
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError("Invalid RomFS entry")
        name = _safe_virtual_path(entry.get("path"))
        size = entry.get("size")
        if not isinstance(size, int) or isinstance(size, bool) or size < 0:
            raise ValueError("Invalid RomFS file size")
        if name in result:
            raise ValueError("Duplicate RomFS path")
        result[name] = size
    return result


def load_manifest(path=DEFAULT_MANIFEST):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        raise ValueError("Unsupported metadata manifest")
    index = _index(data.get("files"))
    if data.get("file_count") != len(index):
        raise ValueError("RomFS manifest count mismatch")
    if not isinstance(data.get("directory_count"), int) or data["directory_count"] < 1:
        raise ValueError("Invalid directory count")
    kinds = dict(sorted(Counter(k.rsplit(".", 1)[-1].lower()
                                for k in index).items()))
    if data.get("types") != kinds:
        raise ValueError("RomFS manifest extension census mismatch")
    return data


def compare_inventory(expected, observed):
    """Compare virtual filenames and exact sizes, ignoring private file offsets."""
    known = _index(expected)
    actual = _index(observed)
    missing = sorted(set(known) - set(actual))
    unexpected = sorted(set(actual) - set(known))
    changed = [
        {"path": path, "expected_size": known[path], "actual_size": actual[path]}
        for path in sorted(set(known) & set(actual))
        if known[path] != actual[path]
    ]
    return {
        "matches": not (missing or unexpected or changed),
        "expected_count": len(known),
        "actual_count": len(actual),
        "missing_paths": missing,
        "unexpected_paths": unexpected,
        "size_mismatches": changed,
    }


def _outside_repository(path):
    resolved = Path(path).resolve()
    if resolved == ROOT or ROOT in resolved.parents:
        raise ValueError("Private input/output must stay outside the public repository")
    return resolved


def _sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _write_private_report(destination, data):
    target = _outside_repository(destination)
    target.parent.mkdir(parents=True, exist_ok=True)
    temp_name = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=target.parent,
            prefix=".dream-radar-private-", suffix=".json", delete=False
        ) as stream:
            temp_name = stream.name
            json.dump(data, stream, indent=2, sort_keys=True)
            stream.write("\n")
        os.replace(temp_name, target)
    finally:
        if temp_name is not None and os.path.exists(temp_name):
            os.unlink(temp_name)


def check(ncch=None, report=None, manifest=DEFAULT_MANIFEST):
    source = load_manifest(manifest)
    if ncch is None:
        if report is not None:
            raise ValueError("--report requires a private NCCH input")
        return {"metadata_only": True, "expected_count": source["file_count"],
                "types": source["types"]}
    private_image = _outside_repository(ncch)
    if report is not None and _outside_repository(report) == private_image:
        raise ValueError("Report cannot overwrite the original NCCH")
    actual = audit(private_image)
    verdict = compare_inventory(source["files"], actual["files"])
    result = {
        "schema_version": 1,
        "source_sha256": _sha256(private_image),
        "source_verified_against_metadata": verdict["matches"],
        "file_counts": {"expected": verdict["expected_count"],
                        "actual": verdict["actual_count"]},
        "romfs_comparison": verdict,
        "actual_types": actual["types"],
    }
    if report is not None:
        _write_private_report(report, result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ncch", nargs="?", type=Path,
                        help="Path to privately stored, decrypted source NCCH")
    parser.add_argument("--report", type=Path,
                        help="Optional report path outside the public Git repository")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    args = parser.parse_args()
    try:
        result = check(args.ncch, args.report, args.manifest)
    except (ValueError, OSError, UnicodeError, json.JSONDecodeError) as error:
        parser.exit(2, "FAIL: private asset verification: " +
                    type(error).__name__ + "\n")
    if result.get("metadata_only"):
        print("PASS: metadata-only manifest is valid (" +
              str(result["expected_count"]) + " expected files); " +
              "source NCCH was not checked")
    else:
        verdict = result["romfs_comparison"]
        print(("PASS" if verdict["matches"] else "FAIL") +
              ": NCCH comparison: " + str(verdict["actual_count"]) +
              "/" + str(verdict["expected_count"]) +
              " files, " + str(len(verdict["missing_paths"])) + " missing, " +
              str(len(verdict["unexpected_paths"])) + " unexpected, " +
              str(len(verdict["size_mismatches"])) + " size mismatches")
        if not verdict["matches"]:
            parser.exit(1)


if __name__ == "__main__":
    main()
