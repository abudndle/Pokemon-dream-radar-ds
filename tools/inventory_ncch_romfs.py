#!/usr/bin/env python3
"""List filenames and sizes from an *unmodified, decrypted* 3DS NCCH RomFS.

Read-only metadata inventory; never extract/distribute original asset bytes.
Only supports the standard little-endian level-3 IVFC RomFS layout.
"""
import argparse
import json
import struct
from collections import Counter
from pathlib import Path

def u32(b, off):
    return struct.unpack_from("<I", b, off)[0]

def audit(path):
    data = Path(path).read_bytes()
    if len(data)<0x200 or data[0x100:0x104]!=b"NCCH":
        raise ValueError("Not an NCCH image")
    rom_off = u32(data,0x1b0)*0x200
    rom_size = u32(data,0x1b4)*0x200
    if not rom_off or rom_off+rom_size>len(data) or data[rom_off:rom_off+4]!=b"IVFC":
        raise ValueError("Decrypted IVFC RomFS not found")
    # Level-3 begins at the 4096-byte alignment of the RomFS master block.
    lvl3=rom_off+0x1000
    if lvl3+40>len(data):
        raise ValueError("Truncated RomFS")
    h=struct.unpack_from("<10I",data,lvl3)
    if h[0]!=40:
        raise ValueError("Unsupported RomFS level-3 header")
    def block(off,size):
        if off<40 or size>rom_size or off+size>rom_size-(lvl3-rom_off):
            raise ValueError("Invalid RomFS metadata bounds")
        return data[lvl3+off:lvl3+off+size]
    dirs=block(h[3],h[4]); files=block(h[7],h[8])
    file_data_base=h[9]
    def item(buf,offset,is_file):
        header=32 if is_file else 24
        if offset==0xffffffff:return None
        if offset+header>len(buf):raise ValueError("RomFS entry out of bounds")
        if is_file:
            parent,sibling,position,length,hash_next,nlen=struct.unpack_from("<IIQQII",buf,offset)
            if position+length>rom_size:raise ValueError("File payload out of bounds")
        else:
            parent,sibling,child,first_file,hash_next,nlen=struct.unpack_from("<6I",buf,offset)
        if nlen%2 or offset+header+nlen>len(buf):raise ValueError("Bad RomFS filename")
        name=buf[offset+header:offset+header+nlen].decode("utf-16le")
        if "/" in name or "\\" in name:raise ValueError("Invalid file name")
        if is_file:return sibling,position,length,name
        return sibling,child,first_file,name
    results=[]; seen_dirs=set();seen_files=set()
    def walk(off,prefix):
        if off in seen_dirs:raise ValueError("Cyclic directory entries")
        seen_dirs.add(off)
        _,child,first,name=item(dirs,off,False)
        folder=prefix+("/"+name if name else "")
        while first!=0xffffffff:
            if first in seen_files:raise ValueError("Cyclic file entries")
            seen_files.add(first)
            sibling,position,length,fname=item(files,first,True)
            if file_data_base+position+length>rom_size:
                raise ValueError("File extends beyond RomFS")
            results.append({"path":folder+"/"+fname,"size":length,
                            "romfs_offset":(lvl3-rom_off)+file_data_base+position})
            first=sibling
        while child!=0xffffffff:
            sibling,_,_,_=item(dirs,child,False)
            walk(child,folder)
            child=sibling
    walk(0,"")
    types=Counter(x["path"].rsplit(".",1)[-1].lower() for x in results)
    return {"file_count":len(results),"types":dict(sorted(types.items())),
            "files":sorted(results,key=lambda x:x["path"])}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("ncch",type=Path)
    p.add_argument("output",type=Path)
    args=p.parse_args()
    report=audit(args.ncch)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print(f"Inventoried {report['file_count']} RomFS files (metadata only)")

if __name__=="__main__":main()
