#!/usr/bin/env python3
"""Stage owner-extracted original 3DS title backgrounds as private DS RGB555.

The public repo cannot assert these images are original; the user must
provide the genuine source files. No external Python image packages required.
Accepts uncompressed 3DS BCLIM, noninterlaced RGB/RGBA PNG or uncompressed
Windows RGB BMP at native 400x240 top / 320x240 bottom sizes.
"""
import argparse
import binascii
import os
from pathlib import Path
import struct
import tempfile
import zlib
from convert_bclim_spr import decode_bclim

ROOT = Path(__file__).resolve().parents[1]
TARGET_W, TARGET_H = 256, 192
SOURCE_SIZE = {"top": (400, 240), "bottom": (320, 240)}
MAX_SOURCE_BYTES = 16 * 1024 * 1024

def _png(data):
    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError("invalid PNG header")
    offset = 8
    width = height = channels = 0
    idat = []
    seen_ihdr = seen_iend = False
    while offset + 12 <= len(data):
        size = struct.unpack_from(">I", data, offset)[0]
        if size > MAX_SOURCE_BYTES or offset + size + 12 > len(data):
            raise ValueError("truncated or oversized PNG chunk")
        tag = data[offset+4:offset+8]
        payload = data[offset+8:offset+8+size]
        crc = struct.unpack_from(">I", data, offset+8+size)[0]
        if (binascii.crc32(tag + payload) & 0xffffffff) != crc:
            raise ValueError("bad PNG chunk CRC")
        offset += 12 + size
        if tag == b"IHDR":
            if seen_ihdr or size != 13 or idat:
                raise ValueError("invalid PNG IHDR")
            seen_ihdr = True
            width, height, bit, color, compress, filtering, interlace = struct.unpack(">IIBBBBB",payload)
            if bit != 8 or color not in (2, 6) or compress or filtering or interlace:
                raise ValueError("unsupported PNG color format or interlace")
            if (width,height) not in SOURCE_SIZE.values():
                raise ValueError("PNG is not the original full-screen dimension")
            channels = 3 if color == 2 else 4
        elif tag == b"IDAT":
            if not seen_ihdr or seen_iend:
                raise ValueError("PNG IDAT out of order")
            idat.append(payload)
        elif tag == b"IEND":
            if not seen_ihdr or not idat or size != 0 or offset != len(data):
                raise ValueError("invalid PNG ending")
            seen_iend = True
            break
        elif tag in (b"PLTE",b"tRNS") or (tag[0] & 32) == 0:
            raise ValueError("unsupported critical PNG chunk")
    if not seen_ihdr or not seen_iend:
        raise ValueError("missing PNG chunks")
    rowlen = width * channels
    expected = (rowlen + 1) * height
    dec = zlib.decompressobj()
    raw = dec.decompress(b"".join(idat), expected+1)
    if len(raw) != expected or not dec.eof or dec.unused_data or dec.unconsumed_tail:
        raise ValueError("PNG decompressed data mismatch")
    rows, previous = bytearray(width * height * 4), bytearray(rowlen)
    for y in range(height):
        kind = raw[y*(rowlen+1)]
        if kind > 4:
            raise ValueError("unsupported PNG filter")
        row = bytearray(raw[y*(rowlen+1)+1:y*(rowlen+1)+1+rowlen])
        for x in range(rowlen):
            a = row[x-channels] if x >= channels else 0
            up = previous[x]
            c = previous[x-channels] if x >= channels else 0
            if kind == 1:
                predictor = a
            elif kind == 2:
                predictor = up
            elif kind == 3:
                predictor = (a+up)//2
            elif kind == 4:
                p=a+up-c
                da,db,dc=abs(p-a),abs(p-up),abs(p-c)
                predictor = a if da<=db and da<=dc else up if db<=dc else c
            else:
                predictor = 0
            row[x] = (row[x]+predictor)&255
        for x in range(width):
            src=x*channels
            dst=(y*width+x)*4
            rows[dst:dst+3]=row[src:src+3]
            rows[dst+3]=row[src+3] if channels==4 else 255
        previous=row
    return width,height,bytes(rows)

def _bmp(data):
    if len(data)<54 or data[:2]!=b"BM":
        raise ValueError("invalid BMP header")
    length=struct.unpack_from("<I",data,2)[0]
    pixels=struct.unpack_from("<I",data,10)[0]
    dib=struct.unpack_from("<I",data,14)[0]
    if dib<40 or dib>256 or length!=len(data) or pixels<14+dib:
        raise ValueError("invalid BMP length or DIB")
    width,height,planes,bits,compression=struct.unpack_from("<iiHHI",data,18)
    if (width,abs(height)) not in SOURCE_SIZE.values() or planes!=1 or bits not in (24,32) or compression!=0:
        raise ValueError("unsupported or wrong-size BMP")
    stride = ((width * bits + 31)//32)*4
    if pixels+stride*abs(height)!=len(data):
        raise ValueError("BMP data size mismatch")
    rgba=bytearray(width*abs(height)*4)
    for y in range(abs(height)):
        source_y = abs(height)-1-y if height>0 else y
        start=pixels+source_y*stride
        for x in range(width):
            at=start+x*(bits//8)
            b,g,r=data[at:at+3]
            a=data[at+3] if bits==32 else 255
            target=(y*width+x)*4
            rgba[target:target+4]=bytes((r,g,b,a))
    return width,abs(height),bytes(rgba)

def load_original(path, screen):
    path=Path(path)
    if not path.is_file() or path.stat().st_size>MAX_SOURCE_BYTES:
        raise ValueError(f"{screen}: missing or oversized source")
    raw=path.read_bytes()
    ext=path.suffix.lower()
    if ext==".bclim":
        width,height,rgba=decode_bclim(raw)
    elif ext==".png":
        width,height,rgba=_png(raw)
    elif ext==".bmp":
        width,height,rgba=_bmp(raw)
    else:
        raise ValueError("source must be original BCLIM, PNG, or BMP")
    if (width,height)!=SOURCE_SIZE[screen]:
        raise ValueError(f"{screen} screen size must be {SOURCE_SIZE[screen]}, got {(width,height)}")
    if len(rgba)!=width*height*4 or any(rgba[i]!=255 for i in range(3,len(rgba),4)):
        raise ValueError("transparent/partial textures need original BCLYT material compositing")
    return width,height,rgba

def encode_raw(image):
    width,height,rgba=image
    out=bytearray(TARGET_W*TARGET_H*2)
    for y in range(TARGET_H):
        sy=y*height//TARGET_H
        for x in range(TARGET_W):
            sx=x*width//TARGET_W
            p=(sy*width+sx)*4
            r,g,b=rgba[p:p+3]
            value=0x8000|(r>>3)|((g>>3)<<5)|((b>>3)<<10)
            struct.pack_into("<H",out,(y*TARGET_W+x)*2,value)
    return bytes(out)

def stage(top,bottom,root):
    root=Path(root).resolve()
    if root==ROOT.resolve() or ROOT.resolve() in root.parents:
        raise ValueError("do not write user-owned original Nintendo art into a public repo")
    paths=[Path(top).resolve(),Path(bottom).resolve()]
    if paths[0]==paths[1]:
        raise ValueError("top and bottom must be distinct original screens")
    payload=[encode_raw(load_original(paths[i],screen))
             for i,screen in enumerate(("top","bottom"))]
    out=root/"DreamRadarDSi"/"UI"
    out.mkdir(parents=True,exist_ok=True)
    staged=[]
    try:
        for filename,data in zip(("title_top.raw","title_bottom.raw"),payload):
            with tempfile.NamedTemporaryFile(prefix=".drtitle-",suffix=".tmp",
                                             dir=out,delete=False) as tmp:
                tmp.write(data)
                staged.append((Path(tmp.name),out/filename))
        for temp,final in staged:
            os.replace(temp,final)
    finally:
        for temp,_ in staged:
            temp.unlink(missing_ok=True)
    return out

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--top",type=Path,required=True)
    parser.add_argument("--bottom",type=Path,required=True)
    parser.add_argument("--output-root",type=Path,required=True)
    args=parser.parse_args()
    out=stage(args.top,args.bottom,args.output_root)
    print(f"Staged private title background pair in {out}; no original assets committed")

if __name__=="__main__":
    main()
