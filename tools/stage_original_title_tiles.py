#!/usr/bin/env python3
"""Stage the 10 actual private 3DS TitleList 8x8 windows/cursor BCLIMs.

No Nintendo image pixels are committed. Read the owner's original
Ui/MnIf_S_TitleList.carc -> DARC -> timg/*.bclim resources privately;
then place the output at sd:/DreamRadarDSi/UI/title_tiles.drtt (or fat:/).
"""
import argparse
import os
from pathlib import Path
import struct
import tempfile
import zlib
from convert_bclim_spr import decode_bclim,parse_header

ROOT=Path(__file__).resolve().parents[1]
NAMES=[f"ListBg{i:02d}.bclim" for i in range(5)]+[
       f"ListCursor{i:02d}.bclim" for i in range(5)]
COUNT=10
WIDTH=HEIGHT=8

def stage(source_dir,output_root):
    source_dir=Path(source_dir).resolve()
    output_root=Path(output_root).resolve()
    if output_root==ROOT.resolve() or ROOT.resolve() in output_root.parents:
        raise ValueError("original Nintendo title pixels must not enter public checkout")
    pixels=bytearray()
    for name in NAMES:
        path=source_dir/name
        if not path.is_file() or path.stat().st_size>256*1024:
            raise ValueError(f"missing or oversized original TitleList tile: {name}")
        blob=path.read_bytes()
        w,h,fmt,_=parse_header(blob)
        if (w,h,fmt)!=(WIDTH,HEIGHT,8):
            raise ValueError(f"expected original 8x8 RGBA4444 title tile: {name}")
        ww,hh,rgba=decode_bclim(blob)
        if (ww,hh)!=(WIDTH,HEIGHT) or len(rgba)!=WIDTH*HEIGHT*4:
            raise ValueError(f"invalid title tile payload: {name}")
        if not any(rgba[i] for i in range(3,len(rgba),4)):
            raise ValueError(f"fully transparent title tile: {name}")
        for i in range(0,len(rgba),4):
            r,g,b,a=rgba[i:i+4]
            pixels.extend(struct.pack("<H",(r>>4)<<12|(g>>4)<<8|
                                      (b>>4)<<4|(a>>4)))
    header=struct.pack("<4sHHI",b"DTT1",1,COUNT,zlib.crc32(pixels)&0xffffffff)
    result=header+pixels
    assert len(result)==12+COUNT*64*2
    out=output_root/"DreamRadarDSi"/"UI"
    out.mkdir(parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile(prefix=".drtitle-tiles-",suffix=".tmp",
                                     dir=out,delete=False) as tmp:
        tmp.write(result);temp=Path(tmp.name)
    try:os.replace(temp,out/"title_tiles.drtt")
    finally:temp.unlink(missing_ok=True)
    return out/"title_tiles.drtt"

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source-dir",type=Path,required=True,
                   help="owner-extracted Ui/MnIf_S_TitleList/timg")
    p.add_argument("--output-root",type=Path,required=True,
                   help="private mounted SD/FAT root, not the public source repo")
    args=p.parse_args()
    output=stage(args.source_dir,args.output_root)
    print(f"Staged original title windows privately: {output}, {output.stat().st_size} bytes")

if __name__=="__main__":
    main()
