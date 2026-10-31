import json
import pathlib
import sys
import tempfile

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
    # A valid CLYT magic + little-endian BOM must not be flagged as corrupt.
    fake.write_bytes(b"CLYT\xff\xfe\x14\x00")
    valid=audit(snapshot,empty)
    assert valid["invalid_layout_sources"]==[]
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
assert "S_ORIGINAL_POKEMON_FIRST=17,S_ORIGINAL_ITEM_FIRST=43" in main_source
assert main_source.count("draw_original_encounter_art();")==2
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
print("PASS: original UI source inventory distinguishes 22 snapshots from bundled sources")
