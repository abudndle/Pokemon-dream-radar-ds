#!/usr/bin/env python3
"""Audit source-backed original UI layouts and missing animation resources.

The extracted JSON is not proof that every source BClyt is available.
This tool reports exact coverage without fabricating missing source files.
"""
import argparse
import json
from pathlib import Path
from parse_original_bclyt import extract

def audit(snapshot, source_dir):
    layouts=json.loads(snapshot.read_text())["layouts"]
    source_files=list(source_dir.rglob("*.bclyt"))
    present={p.name for p in source_files}
    if len(present)!=len(source_files):
        raise ValueError("ambiguous duplicate bundled BClyt filenames")
    invalid_sources=[]
    decoded={}
    for path in source_files:
        try:
            decoded[path.name]=extract(path)
        except ValueError:
            invalid_sources.append(path.relative_to(source_dir).as_posix())
    names=[Path(entry["file"]).name for entry in layouts]
    if len(names)!=len(set(names)):
        raise ValueError("ambiguous duplicate source layout basenames")
    records=[{"layout":name,"source_bclyt":name in present}
             for name in names]
    mismatches=sorted(Path(entry["file"]).name for entry in layouts
                      if Path(entry["file"]).name in decoded and
                      any(decoded[Path(entry["file"]).name][key]!=entry[key]
                          for key in ("sections","panes")))
    animations=sorted(p.relative_to(source_dir).as_posix()
                      for p in source_dir.rglob("*.bclan"))
    return {
        "extracted_layouts":len(records),
        "bundled_layout_sources":sum(r["source_bclyt"] for r in records),
        "missing_layout_sources":sum(not r["source_bclyt"] for r in records),
        "bundled_animation_sources":len(animations),
        "invalid_layout_sources":sorted(invalid_sources),
        "snapshot_mismatches":mismatches,
        "verified_layout_sources":sum(name in decoded and name not in mismatches
                                      for name in names),
        "unmatched_layout_sources":sorted(present-set(names)),
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
    if report["invalid_layout_sources"] or report["snapshot_mismatches"]:
        raise SystemExit("Original UI audit failed: malformed source or snapshot mismatch; see report")

if __name__=="__main__":
    main()
