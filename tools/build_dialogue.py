#!/usr/bin/env python3
"""Regenerate the DSi event-script pages from the user's extracted English MSBT TSV.
Run this inside the project root; no copyrighted input is fetched remotely.
"""
import csv, json, re
from pathlib import Path
root=Path(__file__).resolve().parents[1]
rows={(r['table'],r['label']):r['text'] for r in csv.DictReader((root/'reference_original_dialogue.tsv').open(encoding='utf-8'),delimiter='\t')}
keys=['EVENT_10_010','EVENT_12_010','EVENT_14_010']
output=['/* Generated from the user-provided Dream Radar English event messages. */','#ifndef DREAM_RADAR_STORY_DIALOGUE_H','#define DREAM_RADAR_STORY_DIALOGUE_H']
for stage,key in enumerate(keys,1):
    raw=rows['Event.msbt',key].replace('Pokémon','Pokemon').replace('–','-').replace('—','--').replace('…','...').replace('’',"'")
    raw=re.sub(r'\s+',' ',raw).strip()
    raw=re.sub(r'([.!?])(?=[A-Z])',r'\1 ',raw)  # restore spacing lost at MSBT control boundaries
    pages=[]
    while raw:
        if len(raw)<=170:pages.append(raw);break
        cut=raw.rfind(' ',100,170)
        if cut<100:cut=170
        pages.append(raw[:cut].strip());raw=raw[cut:].strip()
    output.append(f'static const char *const story_stage_{stage}[] = {{')
    output += ['    '+json.dumps(page,ensure_ascii=True)+',' for page in pages]
    output.append('};')
output.append('static const char *const *const story_stages[4] = {NULL, story_stage_1, story_stage_2, story_stage_3};')
output.append('static const unsigned char story_page_counts[4] = {0, (sizeof story_stage_1 / sizeof *story_stage_1), (sizeof story_stage_2 / sizeof *story_stage_2), (sizeof story_stage_3 / sizeof *story_stage_3)};')
output.append('#endif')
(root/'source/story_dialogue.h').write_text('\n'.join(output)+'\n')
