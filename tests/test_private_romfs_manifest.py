#!/usr/bin/env python3
"""Original RomFS metadata parity tests; uses no copyrighted game payloads."""
import json
import pathlib
import sys
import tempfile
import zipfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tools"))
from verify_private_romfs import (
    ROOT, _index, _outside_repository, _write_private_report,
    check, compare_inventory, load_manifest, verify_private_archives,
)


def rejects(action):
    try:
        action()
    except ValueError:
        return
    raise AssertionError("Malformed inventory or unsafe path was accepted")


original = load_manifest()
assert original["file_count"] == 208
assert original["directory_count"] == 15
assert original["types"] == {"carc": 177, "shbin": 10, "bcstm": 20, "bcsar": 1}
assert len(original["files"]) == 208
assert check()["metadata_only"] is True
assert len(set(e["path"] for e in original["files"])) == 208
assert compare_inventory(original["files"], original["files"])["matches"] is True

expected = [{"path": "/Ui/A.carc", "size": 8},
            {"path": "/Audio/B.bcstm", "size": 20}]
actual = [{"path": "/Ui/A.carc", "size": 9, "romfs_offset": 0x100},
          {"path": "/Audio/C.bcstm", "size": 20}]
result = compare_inventory(expected, actual)
assert result["matches"] is False
assert result["expected_count"] == 2 and result["actual_count"] == 2
assert result["missing_paths"] == ["/Audio/B.bcstm"]
assert result["unexpected_paths"] == ["/Audio/C.bcstm"]
assert result["size_mismatches"] == [
    {"path": "/Ui/A.carc", "expected_size": 8, "actual_size": 9}
]
assert compare_inventory(expected, expected)["matches"] is True

for name in ("Ui/A.carc", "//Ui/A.carc", "/Ui//A.carc", "/Ui/../A.carc",
             "/Ui/./A.carc", "/Ui\\A.carc", "/Ui/"):
    rejects(lambda name=name: _index([{"path": name, "size": 1}]))
for invalid in (-1, 1.5, True, "10", None):
    rejects(lambda invalid=invalid: _index([{"path": "/Ui/A.carc", "size": invalid}]))
rejects(lambda: _index([{"path": "/Ui/A.carc", "size": 1},
                        {"path": "/Ui/A.carc", "size": 2}]))
rejects(lambda: _index(None))
rejects(lambda: _outside_repository(ROOT / "private" / "game.ncch"))

with tempfile.TemporaryDirectory() as temporary:
    tmp = pathlib.Path(temporary)
    report = tmp / "reports" / "metadata.json"
    _write_private_report(report, {"matches": False, "missing_paths": ["/a"]})
    assert json.loads(report.read_text())["missing_paths"] == ["/a"]
    assert report.stat().st_mode & 0o077 == 0
    rejects(lambda: check(report=report))
    rejects(lambda: check(tmp / "source.ncch", tmp / "source.ncch"))

    # Synthetic source-derived DARCs and UI archive; no Nintendo payloads.
    darc_file = tmp / "synthetic_darc.zip"
    with zipfile.ZipFile(darc_file, "w", zipfile.ZIP_DEFLATED) as out:
        for entry in original["files"]:
            if entry["path"].endswith(".carc"):
                out.writestr(entry["path"][1:-5] + ".darc", b"darc synthetic")
        out.writestr("inventory.json", "{}")
    ui_file = tmp / "synthetic_ui.zip"
    with zipfile.ZipFile(ui_file, "w", zipfile.ZIP_DEFLATED) as out:
        for ext, amount in ((".bclim", 875), (".bclan", 417),
                            (".bclyt", 135), (".msbt", 35)):
            for i in range(amount):
                out.writestr("Ui/synthetic_%04d%s" % (i, ext), b"x")
    verified = verify_private_archives(original, darc_file, ui_file)
    assert verified["darc"]["member_count"] == 178
    assert verified["ui"]["member_count"] == 1462
    assert all(x["integrity_verified"] for x in verified.values())
    with zipfile.ZipFile(darc_file, "w") as out:
        out.writestr("Ui/invalid.darc", b"darc")
    rejects(lambda: verify_private_archives(original, darc_file))
    with zipfile.ZipFile(ui_file, "w") as out:
        out.writestr("Ui/one.bclim", b"x")
    rejects(lambda: verify_private_archives(original, ui_zip=ui_file))

    bad = json.loads(json.dumps(original))
    bad["files"][0]["size"] += 1
    bad["types"]["carc"] -= 1
    file = tmp / "bad.json"
    file.write_text(json.dumps(bad))
    rejects(lambda: load_manifest(file))
    bad["types"]["carc"] += 1
    bad["file_count"] = 207
    file.write_text(json.dumps(bad))
    rejects(lambda: load_manifest(file))
    bad["file_count"] = 208
    bad["files"][0]["path"] = "/../escape"
    file.write_text(json.dumps(bad))
    rejects(lambda: load_manifest(file))

print("PASS: 208-source RomFS inventory, mismatch detection and private report isolation")
