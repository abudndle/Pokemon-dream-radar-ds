import json
import pathlib
import sys
import tempfile
import struct
import subprocess

root=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/"tools"))
from audit_original_ui import audit

snapshot=root/"ui_mapping/original_pane_geometry.json"
sources=root/"ui_mapping/original_ui"
report=audit(snapshot,sources)
assert report["extracted_layouts"]==22
assert report["bundled_layout_sources"]==1
assert report["missing_layout_sources"]==21
assert report["bundled_animation_sources"]==0
assert report["invalid_layout_sources"]==[]
assert report["snapshot_mismatches"]==[]
assert report["verified_layout_sources"]==1
assert report["unmatched_layout_sources"]==[]

assert sum(x["source_bclyt"] for x in report["layouts"])==1
assert any(x["layout"]=="MnGm_S_Menu.bclyt" and x["source_bclyt"] for x in report["layouts"])
with tempfile.TemporaryDirectory() as d:
    empty=pathlib.Path(d)
    no_sources=audit(snapshot,empty)
    assert no_sources["missing_layout_sources"]==22
    assert no_sources["bundled_layout_sources"]==0
    fake=empty/"damaged.bclyt"
    fake.write_bytes(b"not a CLYT file")
    corrupt=audit(snapshot,empty)
    assert corrupt["invalid_layout_sources"]==["damaged.bclyt"]
    assert corrupt["unmatched_layout_sources"]==["damaged.bclyt"]
    # Magic and BOM alone do not establish a structurally valid source.
    fake.write_bytes(b"CLYT\xff\xfe\x14\x00")
    assert audit(snapshot,empty)["invalid_layout_sources"]==["damaged.bclyt"]
    source=next(sources.rglob("*.bclyt"))
    data=source.read_bytes()
    fake.unlink()
    fixture=empty/source.name
    fixture.write_bytes(data)
    assert audit(snapshot,empty)["verified_layout_sources"]==1
    from parse_original_bclyt import extract
    pane_offset=extract(source)["panes"][0]["section_offset"]
    # A structurally valid transform edit must be distinguished from corruption.
    changed=bytearray(data)
    struct.pack_into('<f',changed,pane_offset+36,1.0)
    fixture.write_bytes(changed)
    mismatch=audit(snapshot,empty)
    assert mismatch["invalid_layout_sources"]==[]
    assert mismatch["snapshot_mismatches"]==[source.name]
    assert mismatch["verified_layout_sources"]==0
    output=empty/"report.json"
    result=subprocess.run([sys.executable,str(root/"tools/audit_original_ui.py"),
                           str(snapshot),str(empty),str(output)],capture_output=True)
    assert result.returncode!=0
    assert json.loads(output.read_text())["snapshot_mismatches"]==[source.name]
    # Reject truncation, appended data, inconsistent counts and invalid panes.
    bad_cases=[data[:n] for n in (0,6,8,19,len(data)-1)]
    bad_cases.append(data+b'garbage')
    for offset,fmt,value in ((6,'H',0),(6,'H',65535),(12,'I',20),
                             (16,'H',0),(pane_offset+4,'I',72),
                             (pane_offset+36,'f',float('nan')),
                             (pane_offset+36,'f',float('inf'))):
        changed=bytearray(data)
        struct.pack_into('<'+fmt,changed,offset,value)
        bad_cases.append(changed)
    # A trailing partial section cannot hide behind a corrected file size.
    changed=bytearray(data+b'x')
    struct.pack_into('<I',changed,12,len(changed))
    bad_cases.append(changed)
    for bad in bad_cases:
        fixture.write_bytes(bad)
        invalid=audit(snapshot,empty)
        assert invalid["invalid_layout_sources"]==[source.name]
        assert invalid["verified_layout_sources"]==0
    fixture.write_bytes(data)
    result=subprocess.run([sys.executable,str(root/"tools/audit_original_ui.py"),
                           str(snapshot),str(empty),str(output)],capture_output=True)
    assert result.returncode==0, result.stderr
# The capture renderer must index the original extracted images by the
# shipped NitroFS manifest, not invent missing models or reorder species.
import re
main_source=(root/"source/main.c").read_text()
manifest=main_source.split("static const char *sprite_files[]={",1)[1].split("};",1)[0]
sprites=re.findall(r'"([^"]+\.spr)"',manifest)
assert len(sprites)==68
assert sprites[17:43]==[f"pokemon_{i:02d}.spr" for i in range(26)]
assert sprites[43:66]==[f"item_{i:02d}.spr" for i in range(23)]
assert sprites[66:]==["radar_cloud_white.spr","radar_cloud_pink.spr"]
# Cross-check every runtime sprite filename against the packaged verifier.
# This catches adding original graphics in source without shipping them in
# NitroFS, and prevents silent ordering/manifest drift.
from verify_assets import SPRITES, BITMAPS
assert len(sprites)==len(SPRITES)
assert len(set(sprites))==len(sprites)
assert set(sprites)==set(SPRITES)
background_manifest=main_source.split("static const char *const bg_files[] = {",1)[1].split("};",1)[0]
backgrounds=re.findall(r'"([^"]+\.raw)"',background_manifest)
assert len(backgrounds)==len(BITMAPS)
assert len(set(backgrounds))==len(backgrounds)
assert set(backgrounds)==set(BITMAPS)
assert "S_ORIGINAL_POKEMON_FIRST=17,S_ORIGINAL_ITEM_FIRST=43" in main_source
assert main_source.count("draw_original_encounter_art();")==2
# Optional DRM1 models must be the first attempt in both encounter views;
# absent or invalid models continue to show the extracted original sprites.
assert '#include "dr_mesh.h"' in main_source
assert 'nitro:/pokemon_%02d.drm' in main_source
assert 'dr_mesh_load_file(path,&encounter_mesh)' in main_source
assert 'DreamRadarDSi/Models/pokemon_%02d.drm' in main_source
assert 'if(!encounter_mesh.vertex && have_romfs)' in main_source
assert 'dr_mesh_wireframe_yaw(&encounter_mesh,top,SW,SH,x,y,24,CYAN,yaw_step)' in main_source
assert 'unsigned yaw_step=(unsigned)((game.save.frames_played/12u)&15u);' in main_source
assert 'if(game.session_type==0 && draw_encounter_mesh(game.session_species,px,py))' in main_source
assert 'else draw_sprite(top,S_ORB,px-29,py-29);' in main_source
assert "else draw_sprite(top,S_ORB,px-29,py-29);" in main_source
# Runtime sprite loading must reject truncated or appended NitroFS data.
assert "ftell(f)!=(long)(4u+payload)" in main_source
assert "fread(s->pixels,1,payload,f)!=payload" in main_source
assert "if(pixel & 0x8000u)visible=1;" in main_source
assert "else if(pixel!=0){valid=0;break;}" in main_source
assert "if(!visible || !valid)" in main_source
# NitroFS fullscreen backgrounds must have an exact byte count, not just a
# readable prefix followed by arbitrary appended data.
assert "ftell(f)==(long)(PIXELS*2u)" in main_source
assert "if(fclose(f)!=0)bg_valid[i]=0;" in main_source
assert "if(!(bg_cache[i][pixel]&0x8000u))" in main_source
assert "bg_valid[i]=0;" in main_source
print("PASS: original UI source inventory distinguishes 22 snapshots from bundled sources")
