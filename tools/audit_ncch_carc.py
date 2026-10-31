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

def classify_header(first_byte):
    if first_byte==0x10:return "lz10"
    if first_byte==0x11:return "lz11"
    return "unverified"

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
                        "compression":classify_header(header[0])})
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
