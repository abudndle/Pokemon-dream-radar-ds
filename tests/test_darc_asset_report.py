#!/usr/bin/env python3
"""Validate public aggregate claims without shipping private DARC files in CI."""
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
report = json.loads((root/'docs/ORIGINAL_DARC_ASSET_KIND_AUDIT.json').read_text())
assert report['format'] == 'DARC_ASSET_KIND_AUDIT_V1'
assert report['archive_count'] == 177
assert report['file_count'] == 1462
assert report['categories'] == {
    'image': 875, 'message': 35, 'ui_animation': 417, 'ui_layout': 135
}
assert report['extensions'] == {
    '.bclan': 417, '.bclim': 875, '.bclyt': 135, '.msbt': 35
}
assert report['validated_signatures'] == {
    'CLAN': 417, 'CLIM_footer': 875, 'CLYT': 135, 'MsgS': 35
}
assert sum(report['categories'].values()) == report['file_count']
assert sum(report['extensions'].values()) == report['file_count']
assert sum(row['archives'] for row in report['archive_groups'].values()) == 177
assert sum(row['files'] for row in report['archive_groups'].values()) == 1462
for group in report['archive_groups'].values():
    assert sum(group['categories'].values()) == group['files']
assert report['3d_candidate_count'] == len(report['3d_candidates']) == 0
assert report['private_asset_bytes_exported'] == 0
assert 'does not prove' in report['caveat']
assert not any('payload' in key or 'base64' in key for key in report)
print('PASS: private archive aggregate report matches 177 DARC / 1462 file inventory')
