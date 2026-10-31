#!/usr/bin/env python3
"""Audit source-backed original UI layouts and missing animation resources.

The extracted JSON is not proof that every source BClyt is available.
This tool reports exact coverage without fabricating missing source files.
"""
import argparse
import json
from pathlib import Path

def audit(snapshot, source_dir):
    layouts=json.loads(snapshot.read_text())["layouts"]
    present={p.name for p in source_dir.rglob("*.bclyt")}
    names=[Path(entry["file"]).name for entry in layouts]
    if len(names)!=len(set(names)):
        raise ValueError("ambiguous duplicate source layout basenames")
    records=[{"layout":name,"source_bclyt":name in present}
             for name in names]
    animations=sorted(p.relative_to(source_dir).as_posix()
                      for p in source_dir.rglob("*.bclan"))
    return {
        "extracted_layouts":len(records),
        "bundled_layout_sources":sum(r["source_bclyt"] for r in records),
        "missing_layout_sources":sum(not r["source_bclyt"] for r in records),
        "bundled_animation_sources":len(animations),
        "animations":animations,
        "layouts":records,
        "note":"Snapshots alone do not establish source availability or playable UI fidelity."
    }

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("snapshot",type=Path)
    parser.add_argument("source_dir",type=Path)
    parser.add_argument("output",type=Path)
    args=parser.parse_args()
    report=audit(args.snapshot,args.source_dir)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2)+"\n")
    print("Original layouts:",report["extracted_layouts"],
          "bundled sources:",report["bundled_layout_sources"],
          "missing:",report["missing_layout_sources"],
          "animations:",report["bundled_animation_sources"])

if __name__=="__main__":
    main()
