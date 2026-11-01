#!/usr/bin/env python3
"""Validate conversion of private original-size 3DS title backdrops."""
import sys
from pathlib import Path
from PIL import Image
import tempfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tools"))
from stage_original_title_art import stage,load_original,encode_raw

with tempfile.TemporaryDirectory() as tmp:
    tmp=Path(tmp)
    top=tmp/"top.png";bottom=tmp/"bottom.png";out=tmp/"mounted-sd"
    Image.new("RGB",(400,240),(20,40,60)).save(top)
    Image.new("RGB",(320,240),(12,34,56)).save(bottom)
    folder=stage(top,bottom,out)
    assert folder==out/"DreamRadarDSi"/"UI"
    t=(folder/"title_top.raw").read_bytes()
    b=(folder/"title_bottom.raw").read_bytes()
    assert len(t)==len(b)==256*192*2
    assert t[:2] == bytes([0xA2,0x9C])
    assert all(b[i]&0x80 for i in range(1,len(b),2))
    old=t,b
    try:stage(top,top,out)
    except ValueError:pass
    else:raise AssertionError("same image accepted for both screens")
    assert (folder/"title_top.raw").read_bytes()==old[0]
    Image.new("RGBA",(320,240),(0,0,0,127)).save(bottom)
    try:stage(top,bottom,out)
    except ValueError as exc:assert "transparent" in str(exc)
    else:raise AssertionError("transparent original pane accepted as opaque background")
    assert (folder/"title_bottom.raw").read_bytes()==old[1]
    Image.new("RGB",(400,240),(1,2,3)).save(bottom)
    try:stage(top,bottom,out)
    except ValueError as exc:assert "screen size" in str(exc)
    else:raise AssertionError("wrong 3DS source dimensions accepted")
    Image.new("RGB",(320,240),(12,34,56)).save(bottom)
    try:stage(top,bottom,ROOT/"nitrofs")
    except ValueError as exc:assert "public repo" in str(exc)
    else:raise AssertionError("allowed private Nintendo assets inside public checkout")
    assert (folder/"title_top.raw").read_bytes()==old[0]
print("PASS: original-size 3DS title art staging, opaque pair and private-only path")
