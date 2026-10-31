#!/usr/bin/env python3
"""Generate the original 23 item labels from the user's extracted English MSBT text.

This is intentionally just the localized UI labels, not proprietary game logic:
encounter probabilities and transfer payload are independent, incomplete work.
"""
import csv
from pathlib import Path

root = Path(__file__).resolve().parents[1]
source = root / 'reference_original_dialogue.tsv'
target = root / 'source' / 'item_catalog_generated.h'
items = {}
with source.open(encoding='utf-8-sig', newline='') as fh:
    for row in csv.DictReader(fh, delimiter='\t'):
        if row.get('table') != 'Item.msbt':
            continue
        label = row.get('label','')
        if label.startswith('ITEM_') and len(label)==7 and label[-2:].isdigit():
            items[int(label[-2:])] = row['text'].strip()
assert sorted(items) == list(range(23)), 'Expected ITEM_00 through ITEM_22'
assert all(v and '\n' not in v and '"' not in v and '\\' not in v for v in items.values())
header = [
    '/* Generated from the user-supplied Pokemon Dream Radar English Item.msbt. */',
    '#ifndef DREAM_RADAR_ITEM_CATALOG_GENERATED_H',
    '#define DREAM_RADAR_ITEM_CATALOG_GENERATED_H',
    'static const char *const original_item_names[23] = {',
]
header += [f'    "{items[i]}", /* ITEM_{i:02d} */' for i in range(23)]
header += ['};','#endif','']
target.write_text('\n'.join(header),encoding='utf-8')
print(f'Generated {len(items)} original English item labels in {target.relative_to(root)}')
