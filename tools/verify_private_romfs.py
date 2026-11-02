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
import zipfile
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


UI_EXPECTED = {".bclim": 875, ".bclan": 417, ".bclyt": 135, ".msbt": 35}


def verify_private_archives(source, darc_zip=None, ui_zip=None,
                            ui_expected=UI_EXPECTED):
    """Validate private extraction ZIPs without writing any original asset bytes."""
    results = {}
    for kind, path in (("darc", darc_zip), ("ui", ui_zip)):
        if path is None:
            continue
        path = _outside_repository(path)
        with zipfile.ZipFile(path) as archive:
            members = [entry for entry in archive.infolist() if not entry.is_dir()]
            if len(members) != len({item.filename for item in members}):
                raise ValueError("Duplicate extraction ZIP member")
            if sum(entry.file_size for entry in members) > 256 * 1024 * 1024:
                raise ValueError("Extraction ZIP exceeds safe audit limit")
            for item in members:
                _safe_virtual_path("/" + item.filename)
            if archive.testzip() is not None:
                raise ValueError("Extraction ZIP failed CRC validation")
            suffix_counts = dict(sorted(Counter(
                Path(item.filename).suffix.lower() for item in members
            ).items()))
            if kind == "darc":
                actual = {item.filename for item in members
                          if item.filename.lower().endswith(".darc")}
                expected = {name[1:-5] + ".darc"
                            for name in _index(source["files"])
                            if name.lower().endswith(".carc")}
                if actual != expected or any(
                    not item.filename.lower().endswith(".darc") and
                    not item.filename.lower().endswith(".json")
                    for item in members
                ) or len(members) > len(actual) + 1:
                    raise ValueError("DARC archive coverage does not match NCCH")
                for name in sorted(actual):
                    with archive.open(name) as handle:
                        if handle.read(4) != b"darc":
                            raise ValueError("Bad DARC magic")
            elif suffix_counts != ui_expected:
                raise ValueError("Original UI extraction is incomplete")
        results[kind] = {
            "member_count": len(members),
            "types": suffix_counts,
            "source_sha256": _sha256(path),
            "integrity_verified": True,
        }
    return results


def check(ncch=None, report=None, manifest=DEFAULT_MANIFEST,
          darc_zip=None, ui_zip=None):
    source = load_manifest(manifest)
    if ncch is None:
        if darc_zip is not None or ui_zip is not None:
            raise ValueError("Archive checks require the original NCCH")
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
    result["private_archives"] = verify_private_archives(
        source, darc_zip, ui_zip
    )
    if report is not None:
        _write_private_report(report, result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ncch", nargs="?", type=Path,
                        help="Path to privately stored, decrypted source NCCH")
    parser.add_argument("--report", type=Path,
                        help="Optional report path outside the public Git repository")
    parser.add_argument("--darc-zip", type=Path,
                        help="Privately held archive of the 177 extracted DARCs")
    parser.add_argument("--ui-zip", type=Path,
                        help="Privately held archive of 1462 extracted UI members")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    args = parser.parse_args()
    try:
        result = check(args.ncch, args.report, args.manifest,
                       args.darc_zip, args.ui_zip)
    except (ValueError, OSError, UnicodeError, json.JSONDecodeError,
            zipfile.BadZipFile, RuntimeError) as error:
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
        if result["private_archives"]:
            print("PASS: private archive CRC and coverage (" +
                  ", ".join(kind + "=" + str(info["member_count"])
                            for kind, info in sorted(result["private_archives"].items())) +
                  ")")
        if not verdict["matches"]:
            parser.exit(1)


if __name__ == "__main__":
    main()
