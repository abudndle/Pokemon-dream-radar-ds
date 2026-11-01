#!/usr/bin/env python3
"""Validate original 3DS title conversion using synthetic PNG/BMP fixtures."""
import binascii
import struct
import sys
from pathlib import Path
import tempfile
import zlib

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tools"))
from stage_original_title_art import stage,load_original,encode_raw

def chunk(tag,data):
    return struct.pack(">I",len(data))+tag+data+struct.pack(">I",binascii.crc32(tag+data)&0xffffffff)

def png(path,width,height,rgb,alpha=None):
    color=2 if alpha is None else 6
    pixel=bytes(rgb if alpha is None else rgb+(alpha,))
    lines=b"".join(b"\0"+pixel*width for _ in range(height))
    hdr=struct.pack(">IIBBBBB",width,height,8,color,0,0,0)
    path.write_bytes(b"\x89PNG\r\n\x1a\n"+chunk(b"IHDR",hdr)+chunk(b"IDAT",zlib.compress(lines))+chunk(b"IEND",b""))

def bmp(path,width,height,rgb):
    stride=((width*3+3)//4)*4
    row=bytes((rgb[2],rgb[1],rgb[0]))*width + b"\0"*(stride-width*3)
    size=54+stride*height
    header=struct.pack("<2sIHHI",b"BM",size,0,0,54)
    dib=struct.pack("<IiiHHIIiiII",40,width,height,1,24,0,stride*height,0,0,0,0)
    path.write_bytes(header+dib+row*height)

with tempfile.TemporaryDirectory() as temp:
    tmp=Path(temp)
    top=tmp/"top.png";bottom=tmp/"bottom.bmp";out=tmp/"mounted-sd"
    png(top,400,240,(20,40,60))
    bmp(bottom,320,240,(12,34,56))
    folder=stage(top,bottom,out)
    assert folder==out/"DreamRadarDSi"/"UI"
    t=(folder/"title_top.raw").read_bytes()
    b=(folder/"title_bottom.raw").read_bytes()
    assert len(t)==len(b)==256*192*2
    assert t[:2]==bytes([0xA2,0x9C])
    assert b[:2]==struct.pack("<H",0x8000|(12>>3)|((34>>3)<<5)|((56>>3)<<10))
    assert all(b[i]&0x80 for i in range(1,len(b),2))
    old=t,b
    try:stage(top,top,out)
    except ValueError:pass
    else:raise AssertionError("same image accepted for both screens")
    assert (folder/"title_top.raw").read_bytes()==old[0]
    png(bottom,320,240,(0,0,0),127)
    try:stage(top,bottom,out)
    except ValueError as exc:assert "transparent" in str(exc)
    else:raise AssertionError("transparent texture treated as opaque background")
    assert (folder/"title_bottom.raw").read_bytes()==old[1]
    png(bottom,400,240,(1,2,3))
    try:stage(top,bottom,out)
    except ValueError as exc:assert "screen size" in str(exc)
    else:raise AssertionError("wrong original source dimensions accepted")
    png(bottom,320,240,(12,34,56))
    try:stage(top,bottom,ROOT/"nitrofs")
    except ValueError as exc:assert "public repo" in str(exc)
    else:raise AssertionError("allowed proprietary art into public checkout")
    corrupted=bytearray(top.read_bytes())
    corrupted[-1]^=0x80
    top.write_bytes(corrupted)
    try:load_original(top,"top")
    except ValueError as exc:assert "CRC" in str(exc)
    else:raise AssertionError("bad PNG checksum accepted")
    assert (folder/"title_top.raw").read_bytes()==old[0]
    assert (folder/"title_bottom.raw").read_bytes()==old[1]
print("PASS: original 3DS BCLIM/PNG/BMP staging, strict sizes and private-only path")
