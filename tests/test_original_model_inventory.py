#!/usr/bin/env python3
"""Host regression tests for the local, non-distributing model inventory."""
import hashlib
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from inventory_original_models import inventory, compare_inventories

with tempfile.TemporaryDirectory() as temp:
    root = pathlib.Path(temp)
    (root / "Pokemon").mkdir()
    sample = b"not a validated model"
    (root / "Pokemon" / "candidate.BCMDL").write_bytes(sample)
    (root / "Pokemon" / "ignore.txt").write_text("text")
    (root / "zero.cmb").write_bytes(b"")
    (root / "link.bch").symlink_to(root / "Pokemon" / "candidate.BCMDL")
    report = inventory(root)
    assert report["model_candidates"] == 2
    assert report["models_converted"] == 0
    assert report["models_verified_on_ds"] == 0
    assert [row["path"] for row in report["files"]] == [
        "Pokemon/candidate.BCMDL", "zero.cmb"
    ]
    first = report["files"][0]
    assert first["bytes"] == len(sample)
    assert first["sha256"] == hashlib.sha256(sample).hexdigest()
    assert first["status"] == "candidate_only_not_decoded"
    assert report["files"][1]["bytes"] == 0
    assert len(inventory(root)["files"]) == 2
    assert compare_inventories(report, inventory(root)) == {
        "added": [], "removed": [], "changed": []
    }
    (root / "Pokemon" / "candidate.BCMDL").write_bytes(b"changed source")
    (root / "new.bch").write_bytes(b"new model candidate")
    (root / "zero.cmb").unlink()
    delta = compare_inventories(report, inventory(root))
    assert delta == {
        "added": ["new.bch"],
        "removed": ["zero.cmb"],
        "changed": ["Pokemon/candidate.BCMDL"]
    }
    # Malformed or duplicated prior manifests must not silently overwrite
    # entries and misreport which original model file changed.
    for bad in (
        {"files": [report["files"][0], report["files"][0]]},
        {"files": [{"path": "../escape.bch", "bytes": 1, "sha256": "0" * 64}]},
        {"files": [{"path": "wrong.bch", "bytes": -1, "sha256": "0" * 64}]},
        {"files": [{"path": "wrong.bch", "bytes": 1, "sha256": "not-a-hash"}]},
        {"models_converted": 0},
    ):
        try:
            compare_inventories(bad, inventory(root))
        except ValueError:
            pass
        else:
            raise AssertionError("Invalid inventory accepted")
    try:
        inventory(root / "missing")
    except ValueError:
        pass
    else:
        raise AssertionError("Missing model directory must not look like zero available models")
print("PASS: original model inventory is deterministic and never claims conversion")
