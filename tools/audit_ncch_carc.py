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

def inspect_size_header(header, compressed_size, limit=64*1024*1024):
    """Interpret the common Nintendo four-byte type/24-bit-size layout.

    A plausible size is evidence for an LZ40 *candidate*, not proof that
    the following bytes decode successfully. Never allocate based on it.
    """
    if len(header)<4 or compressed_size<4 or header[0]!=0x40:
        return None
    size=int.from_bytes(header[1:4],"little")
    if size==0 or size>limit:
        return None
    return size

def inspect_possible_table_header(header, archive_size):
    """Candidate byte-4 tree/table size; this is NOT a verified codec."""
    if len(header)<8 or header[0]!=0x40 or archive_size<8:
        return None
    count=header[4]
    # Nintendo Huffman-style tables often use two bytes per entry. Record a
    # bounded hypothesis only; archive payload format remains unidentified.
    table_bytes=2*(count+1)
    if 8+table_bytes>archive_size:
        return None
    return {"table_size_byte":count, "candidate_table_bytes":table_bytes,
            "reserved_bytes_hex":header[5:8].hex(),
            "payload_after_candidate_table":archive_size-8-table_bytes}

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
                        "compression":classify_header(header[0]),
                        "lz40_candidate_unpacked_size":inspect_size_header(header,length),
                        "possible_table_header":inspect_possible_table_header(header,length)})
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
