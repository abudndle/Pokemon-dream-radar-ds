#!/usr/bin/env python3
"""Curate optional Professor Burnet dialogue from the user's extracted English ROM text.

These are optional short talk exchanges, not a full reproduction of events/cutscenes.
The generated text is ASCII-normalized for the prototype's six-pixel font.
"""
import csv
import re
import unicodedata
from pathlib import Path

root=Path(__file__).resolve().parents[1]
src=root/'reference_original_dialogue.tsv'
dst=root/'source/burnet_tips_generated.h'
# Exclude texts with dynamic glyph placeholders; include 23 contextual exchanges.
ids=[3,4,5,7,8,12,13,15,16,17,18,24,25,28,29,30,32,35,38,39,40,41,42,43,45,46,47,48,51,52]
selected={}
with src.open(encoding='utf-8-sig',newline='') as fh:
    for r in csv.DictReader(fh,delimiter='\t'):
        if r.get('table')=='Event.msbt' and r.get('label','') in [f'TWEET_04_{i:03d}' for i in ids]:
            selected[int(r['label'][-3:])]=r['text']
assert sorted(selected)==sorted(ids),f'Missing tips: {set(ids)-set(selected)}'

def translate(s):
    s=' '.join(s.split())
    s=unicodedata.normalize('NFKD',s).encode('ascii','ignore').decode('ascii')
    s=re.sub(r'\s+',' ',s)
    s=re.sub(r'(?<=[.!?])(?=[A-Z])',' ',s)
    s=s.replace('Pokemon','Pokemon')
    assert s and len(s)<240 and all(32<=ord(ch)<=126 for ch in s)
    return s.replace('\\','\\\\').replace('"','\\"')
output=[
    '/* Original Burnet talk messages from the user-supplied Dream Radar Event.msbt.',
    ' * ASCII/whitespace normalized for 6-pixel DS homebrew font. */',
    '#ifndef DREAM_RADAR_BURNET_TIPS_GENERATED_H',
    '#define DREAM_RADAR_BURNET_TIPS_GENERATED_H',
    f'#define BURNET_TIP_COUNT {len(ids)}',
    'static const char *const burnet_tips[BURNET_TIP_COUNT] = {',
]
for i in ids:output.append(f'    "{translate(selected[i])}", /* TWEET_04_{i:03d} */')
output+=['};','#endif','']
dst.write_text('\n'.join(output),encoding='utf-8')
print(f'Generated {len(ids)} original Burnet tip dialogues')
