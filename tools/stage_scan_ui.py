#!/usr/bin/env python3
"""Stage recovered 3DS MnIf_S_ScanList BCLYT/CLPA for DS Extensions menu.

The public NitroFS scene contains ONLY owner-supplied metadata-derived pane
geometry. Optional proprietary BCLAN keyframes must remain outside checkout.
"""
import argparse
import json
from pathlib import Path
from stage_title_ui import stage

ROOT = Path(__file__).resolve().parents[1]
SCAN_LAYOUT = "MnIf_S_ScanList.bclyt"
SCAN_Y_OFFSET = 45

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshot",type=Path,help="original BCLYT metadata-only snapshot")
    parser.add_argument("output",type=Path,help="generated geometry or private scan.drui")
    group=parser.add_mutually_exclusive_group()
    group.add_argument("--clip",type=Path,help="private original ScanList .bclan")
    group.add_argument("--clip-json",type=Path,help="private decoded CLPA JSON")
    args=parser.parse_args()
    if args.snapshot.resolve()==args.output.resolve():
        parser.error("output must not overwrite its original snapshot")
    if args.clip or args.clip_json:
        if ROOT.resolve()==args.output.resolve() or ROOT.resolve() in args.output.resolve().parents:
            parser.error("private Nintendo animation data must stay outside public checkout")
    tracks=[]
    if args.clip:
        if args.clip.resolve()==args.output.resolve():parser.error("output overlaps private animation")
        from decode_bclan_panes import decode
        tracks.append(decode(args.clip.read_bytes()))
    if args.clip_json:
        if args.clip_json.resolve()==args.output.resolve():parser.error("output overlaps private animation")
        tracks.append(json.loads(args.clip_json.read_text(encoding="utf-8")))
    geometry=json.loads(args.snapshot.read_text(encoding="utf-8"))
    output=stage(geometry,tracks,offset_y=SCAN_Y_OFFSET,layout_name=SCAN_LAYOUT)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_bytes(output)
    print(f"ScanList: {len(output)} bytes; four original Touch00..03 rows, " +
          ("private animation" if tracks else "public geometry only"))

if __name__=="__main__":
    main()
