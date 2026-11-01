#!/usr/bin/env python3
"""Source-free synthetic fixtures for real 3DS TitleList RGBA4444 tile stage."""
import binascii
from pathlib import Path
import struct
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tools"))
from stage_original_title_tiles import NAMES,stage

def make_bclim(color):
    payload=struct.pack("<H",color)*64
    footer=struct.pack("<4sHHIII4sIHHII",b"CLIM",0xfeff,20,
                       0x02020000,len(payload)+40,1,b"imag",16,8,8,8,len(payload))
    return payload+footer

with tempfile.TemporaryDirectory() as name:
    root=Path(name)
    source=root/"original-bclim"
    source.mkdir()
    for filename in NAMES:
        color=0x555f if filename.startswith("ListBg") else 0x0f0f
        (source/filename).write_bytes(make_bclim(color))
    good_root=root/"private-sd"
    result=stage(source,good_root)
    content=result.read_bytes()
    assert len(content)==1292
    assert content[:4]==b"DTT1"
    assert struct.unpack_from("<HHI",content,4)==(
        1,10,binascii.crc32(content[12:])&0xffffffff)
    bad_root=root/"bad-sd"
    bad_file=bad_root/"DreamRadarDSi"/"UI"/"title_tiles.drtt"
    bad_file.parent.mkdir(parents=True)
    broken=bytearray(content)
    broken[-1]^=0x10
    bad_file.write_bytes(broken)
    subprocess.run([str(ROOT/"build/test_dr_title_tiles"),str(good_root),str(bad_root)],check=True)
    try:stage(source,ROOT/"nitrofs")
    except ValueError as e:assert "public checkout" in str(e)
    else:raise AssertionError("private game textures allowed into public repo")
    # Never overwrite valid private packs on a missing/invalid original tile.
    (source/"ListBg03.bclim").unlink()
    try:stage(source,good_root)
    except ValueError:pass
    else:raise AssertionError("missing original tile silently accepted")
    assert result.read_bytes()==content
print("PASS: private original 3DS title tiles, CRC, format, rendering and public-repo rejection")
