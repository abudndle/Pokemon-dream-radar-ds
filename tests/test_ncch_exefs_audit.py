#!/usr/bin/env python3
"""Synthetic NCCH, CBMD, CGFX, CWAV and logo DARC only; no original assets."""
import struct
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from audit_ncch_exefs import (
    ExefsAuditError, decompress_lz11, check_cgfx, inspect_cbmd,
    inspect_logo, inspect_exefs, inspect_romfs_types
)


def reject(fn, contains=None):
    try:fn()
    except (ValueError, ExefsAuditError) as error:
        if contains:
            assert contains in str(error),(contains,str(error))
    else:
        raise AssertionError("Malformed NCCH/asset stream passed validation")


def lz_literals(data):
    if len(data)>0xffffff:
        raise ValueError('Fixture too large')
    result=bytearray(b'\x11'+len(data).to_bytes(3,'little'))
    for i in range(0,len(data),8):
        result.append(0)
        result.extend(data[i:i+8])
    return bytes(result)


def cgfx():
    body=b'DATA'+struct.pack('<I',12)+b'CMDL'
    return struct.pack('<4sHHIII',b'CGFX',0xfeff,20,0,20+len(body),1)+body


def banner():
    graphics=lz_literals(cgfx())
    padding=b'\0'*9
    wav=bytearray(b'CWAV\xff\xfe\x40\x00'+b'\0'*56)
    struct.pack_into('<I',wav,12,len(wav))
    output=bytearray(b'\0'*0x88)
    output[:4]=b'CBMD'
    struct.pack_into('<I',output,8,0x88)
    struct.pack_into('<I',output,0x84,0x88+len(graphics)+len(padding))
    output.extend(graphics+padding+wav)
    return bytes(output)


def darc_with_ui():
    payload=b'CLAN\xff\xfe\x14\x00'+b'\0'*12
    names=b'\0\0'
    dot_off=len(names)
    names+='.'.encode('utf-16le')+b'\0\0'
    filename_off=len(names)
    names+='sample.bclan'.encode('utf-16le')+b'\0\0'
    count=3
    table_size=12*count+len(names)
    data_off=(28+table_size+3)//4*4
    nodes=(struct.pack('<III',0x01000000,0,count)+
           struct.pack('<III',0x01000000|dot_off,0,count)+
           struct.pack('<III',filename_off,data_off,len(payload)))
    header=struct.pack('<4sHHIIIII',b'darc',0xfeff,28,0x01000000,
                       data_off+len(payload),28,table_size,data_off)
    return header+nodes+names+b'\0'*(data_off-28-table_size)+payload


def logo():
    return lz_literals(darc_with_ui())+b'\0'*16


def fake_ncch():
    parts=[('.code',b'\x00'*32),('banner',banner()),
           ('icon',b'SMDH'+b'\0'*508),('logo',logo())]
    offsets=[]
    position=0
    for name,data in parts:
        position=(position+15)//16*16
        offsets.append((name,position,data))
        position+=len(data)
    size=512+((position+511)//512)*512
    image=bytearray(b'\0'*(512+size))
    image[0x100:0x104]=b'NCCH'
    struct.pack_into('<I',image,0x104,len(image)//512)
    struct.pack_into('<I',image,0x1a0,1)
    struct.pack_into('<I',image,0x1a4,size//512)
    for i,(name,relative,data) in enumerate(offsets):
        struct.pack_into('<8sII',image,512+i*16,
                         name.encode().ljust(8,b'\0'),relative,len(data))
        start=512+512+relative
        image[start:start+len(data)]=data
    return bytes(image)


def test():
    payload=b'ABABAB'
    assert decompress_lz11(lz_literals(payload))[0]==payload
    # LZ11 short 2-byte token, 4 copies at distance 2.
    assert decompress_lz11(bytes.fromhex('110600002041423001'))[0]==payload
    # Medium token: 17 copies at distance 1.
    assert decompress_lz11(bytes.fromhex('111200004041000000'))[0]==b'A'*18
    # Long token: 273 copies at distance 1.
    assert decompress_lz11(bytes.fromhex('11120100404110000000'))[0]==b'A'*274
    reject(lambda:decompress_lz11(b'\x11\x01\0\0'), 'Truncated')
    reject(lambda:decompress_lz11(b'\x11\x00\0\0'), 'Truncated')
    reject(lambda:decompress_lz11(bytes.fromhex('11060000802000')), 'Invalid')
    reject(lambda:decompress_lz11(bytes.fromhex('110100004041'),max_output=0),
           'budget')
    accepted=check_cgfx(cgfx())
    assert accepted['cmdl_signature_count']==1
    assert accepted['section_count']==1
    broken=bytearray(cgfx())
    broken[0]=ord('X')
    reject(lambda:check_cgfx(broken),'Expected')
    broken=bytearray(cgfx())
    struct.pack_into('<I',broken,12,len(broken)+1)
    reject(lambda:check_cgfx(broken),'Invalid')
    cbmd=inspect_cbmd(banner())
    assert cbmd['cgfx_container_count']==1
    assert cbmd['cgfx_containers'][0]['slot']==0
    assert cbmd['cgfx_containers'][0]['padding_bytes']==9
    assert cbmd['cmdl_markers_total']==1
    invalid=bytearray(banner())
    struct.pack_into('<I',invalid,8,0x87)
    reject(lambda:inspect_cbmd(invalid),'offset')
    invalid=bytearray(banner())
    invalid[-64]=ord('X')
    reject(lambda:inspect_cbmd(invalid),'CWAV')
    invalid=bytearray(banner())
    invalid[0x88]=0x10
    reject(lambda:inspect_cbmd(invalid),'LZ11')
    sub=inspect_logo(logo())
    assert sub['file_count']==1
    assert sub['categories']=={'ui_animation':1}
    reject(lambda:inspect_logo(logo()+b'\x01'),'Nonzero')
    invalid=bytearray(logo())
    invalid[0]=0x10
    reject(lambda:inspect_logo(invalid),'LZ11')
    image=bytearray(fake_ncch())
    report=inspect_exefs(bytes(image))
    assert report['section_count']==4
    assert report['banner']['cgfx_container_count']==1
    assert report['logo']['file_count']==1
    assert report['code_status']=='opaque_executable_not_a_model_decode'
    image[0x100]=0
    reject(lambda:inspect_exefs(bytes(image)),'NCCH')
    image=bytearray(fake_ncch())
    struct.pack_into('<I',image,0x104,1)
    reject(lambda:inspect_exefs(bytes(image)),'size')
    image=bytearray(fake_ncch())
    # Malformed overlap: move icon into the banner section.
    struct.pack_into('<I',image,512+2*16+8,32)
    reject(lambda:inspect_exefs(bytes(image)),'Overlapping')
    # Corrupted ExeFS second entry name.
    image=bytearray(fake_ncch())
    image[512+16:512+24]=b'.code\0\0\0'
    reject(lambda:inspect_exefs(bytes(image)),'Duplicate')
    print('PASS: ExeFS CBMD LZ11/CGFX, logo DARC, checks and malformed inputs')


if __name__=='__main__':test()
