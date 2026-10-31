#!/usr/bin/env python3
"""Bounded probe for Nintendo LZ40 (low-endian LZX) CARC payloads.

Diagnostic only: a 0x40 signature is insufficient to establish this format.
No archive bytes are exported or included in the report.
"""
import argparse
import json
import struct
from pathlib import Path
from inventory_ncch_romfs import audit

class DecodeError(ValueError):
    pass

def decode_lz40(data, max_output=16*1024*1024):
    if len(data)<4 or data[0]!=0x40:
        raise DecodeError("not an LZ40 header")
    size=int.from_bytes(data[1:4],"little")
    if size==0 or size>max_output:
        raise DecodeError("invalid unpacked size")
    out=bytearray()
    pos=4
    mask=0
    flags=0
    while len(out)<size:
        if mask==0:
            if pos>=len(data):raise DecodeError("truncated flag byte")
            flags=(-data[pos])&0xff
            pos+=1
            mask=0x80
        if flags&mask:
            if pos+2>len(data):raise DecodeError("truncated backreference")
            token=int.from_bytes(data[pos:pos+2],"little")
            pos+=2
            length=token&15
            distance=token>>4
            if length<2:
                if pos>=len(data):raise DecodeError("truncated extended length")
                length=data[pos]+16
                pos+=1
                if token&15:
                    if pos>=len(data):raise DecodeError("truncated long length")
                    length+=0x100+(data[pos]<<8)
                    pos+=1
            if not distance or distance>len(out):
                raise DecodeError("backreference before output start")
            if length>size-len(out):
                raise DecodeError("backreference exceeds unpacked size")
            for _ in range(length):
                out.append(out[-distance])
        else:
            if pos>=len(data):raise DecodeError("truncated literal")
            out.append(data[pos])
            pos+=1
        mask>>=1
    if len(data)-pos>4:
        raise DecodeError("unexpected trailing data")
    return bytes(out)

def probe_ncch(path):
    image=Path(path).read_bytes()
    rom_offset=struct.unpack_from("<I",image,0x1b0)[0]*512
    result={"format_probe":"standard low-endian LZ40 (not assumed)",
            "successes":[],"failures":[]}
    for item in audit(path)["files"]:
        if not item["path"].lower().endswith(".carc"):continue
        begin=rom_offset+item["romfs_offset"]
        data=image[begin:begin+item["size"]]
        try:
            unpacked=decode_lz40(data)
        except DecodeError as exc:
            result["failures"].append({"path":item["path"],"reason":str(exc)})
        else:
            result["successes"].append({"path":item["path"],
                                         "unpacked_bytes":len(unpacked),
                                         "first4_hex":unpacked[:4].hex()})
    result["tested"]=len(result["successes"])+len(result["failures"])
    return result

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("ncch",type=Path)
    p.add_argument("report",type=Path)
    args=p.parse_args()
    result=probe_ncch(args.ncch)
    args.report.parent.mkdir(parents=True,exist_ok=True)
    args.report.write_text(json.dumps(result,indent=2)+"\\n",encoding="utf-8")
    print(f"Probed {result['tested']} CARCs: "
          f"{len(result['successes'])} standard-LZ40 matches; "
          f"{len(result['failures'])} rejected")

if __name__=="__main__":main()
