#!/usr/bin/env python3
"""Aggregate audit guard: no proprietary bytes or Pokémon-model overclaim."""
import json
from pathlib import Path
root=Path(__file__).resolve().parents[1]
report=json.loads((root/'docs/ORIGINAL_NCCH_EXEFS_AUDIT.json').read_text())
assert report['format']=='NCCH_EXEFS_MODEL_SOURCE_AUDIT_V1'
assert report['image_bytes']==24944640
exefs=report['exefs']
assert exefs['section_count']==4
assert {e['name']:e['bytes'] for e in exefs['sections']}=={
    '.code':572840,'banner':866072,'icon':14016,'logo':8192}
assert exefs['icon_format']=='SMDH'
banner=exefs['banner']
assert banner['graphics_format']=='CBMD'
assert banner['cgfx_container_count']==len(banner['cgfx_containers'])==14
assert {x['slot'] for x in banner['cgfx_containers']}=={
    0,1,2,3,4,5,6,7,8,10,11,12,13,15}
assert all(x['section_count']==2 and x['cmdl_signature_count']==1
           for x in banner['cgfx_containers'])
assert sum(x['compressed_bytes'] for x in banner['cgfx_containers'])==759535
assert sum(x['decoded_bytes'] for x in banner['cgfx_containers'])==2483968
assert sum(x['padding_bytes'] for x in banner['cgfx_containers'])==9
assert banner['cmdl_markers_total']==14
assert banner['banner_audio']=={'format':'CWAV','bytes':106392}
assert 'HOME MENU' in banner['scope']
logo=exefs['logo']
assert logo['compression']=='LZ11' and logo['container']=='DARC'
assert logo['decoded_bytes']==25928 and logo['compressed_bytes']==6504
assert logo['file_count']==16
assert logo['categories']=={'image':8,'ui_animation':6,'ui_layout':2}
romfs=report['romfs']
assert romfs['file_count']==208
assert romfs['types']=={'CARC_LZH8_header':177,
                       'CSAR_audio':1,'CSTM_audio':20,
                       'DVLB_shader':10}
assert sum(romfs['types'].values())==romfs['file_count']
assert romfs['classified_3d_gameplay_meshes']==0
assert report['verified_3ds_pokemon_skeletal_animation'] is False
assert report['private_asset_bytes_exported']==0
assert 'DOES NOT' in report['caveat']
print('PASS: 14 original ExeFS CGFX banner resources, 16 logo UI files, '
      '208 RomFS entries, and provenance caveats')
