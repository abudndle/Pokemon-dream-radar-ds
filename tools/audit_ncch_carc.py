#!/usr/bin/env python3
"""Read-only CARC header census from a privately held decrypted NCCH image.

Does not extract archive payloads or presume that 0x40 means LZ10/LZ11.
"""
import argparse
import json
import struct
from collections import Counter
from pathlib import Path
from inventory_ncch_romfs import audit

def inspect(path):
    image=Path(path).read_bytes()
    romfs_start=struct.unpack_from("<I",image,0x1b0)[0]*512
    listing=audit(path)
    results=[]
    for entry in listing["files"]:
        if not entry["path"].lower().endswith(".carc"):
            continue
        offset=romfs_start+entry["romfs_offset"]
        length=entry["size"]
        if length<4 or offset<0 or offset+length>len(image):
            raise ValueError("CARC entry outside NCCH image")
        header=image[offset:offset+min(length,16)]
        results.append({"path":entry["path"],"size":length,
                        "header16_hex":header.hex(),
                        "header_byte":header[0],
                        "compression":"lz10" if header[0]==0x10 else
                                      "lz11" if header[0]==0x11 else "unverified"})
    return {"archive_count":len(results),
            "first_byte_counts":dict(sorted(Counter(f"0x{r['header_byte']:02x}" for r in results).items())),
            "archives":results}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("ncch",type=Path)
    p.add_argument("report",type=Path)
    args=p.parse_args()
    report=inspect(args.ncch)
    args.report.parent.mkdir(parents=True,exist_ok=True)
    args.report.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print(f"Audited {report['archive_count']} CARC headers without extracting assets")

if __name__=="__main__":
    main()
