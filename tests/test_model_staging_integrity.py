#!/usr/bin/env python3
"""Regression checks for private model staging provenance and failed conversion."""
import hashlib
import json
import sys
import tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from stage_pokemon_models import stage

def main():
    with tempfile.TemporaryDirectory() as d:
        root=Path(d);src=root/"source";out=root/"models"
        src.mkdir()
        (src/"pokemon_00.obj").write_text(
            "v 0 0 0\nv 1 0 0\nv 0 1 0\nf 1 2 3\n",encoding="utf-8")
        report=stage(src,out)
        assert len(report["models"])==1
        entry=report["models"][0]
        blob=(out/entry["file"]).read_bytes()
        assert entry["sha256"]==hashlib.sha256(blob).hexdigest()
        assert entry["bytes"]==len(blob)
        assert json.loads((out/"model_manifest.json").read_text())==report
        before={p.name:p.read_bytes() for p in out.iterdir()}
        (src/"pokemon_01.obj").write_text("this is not a valid OBJ\n")
        try:
            stage(src,out)
        except (ValueError,IndexError,KeyError):
            pass
        else:
            raise AssertionError("invalid OBJ unexpectedly converted")
        assert {p.name:p.read_bytes() for p in out.iterdir()}==before
    print("PASS: model staging hashes and failed conversion preserves published files")
if __name__=="__main__":
    main()
