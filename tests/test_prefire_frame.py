#!/usr/bin/env python3
"""Synthetic single-pass prefire checks; never substitutes for live melonDS."""
from pathlib import Path
import json
import sys
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from verify_sphere_prefire_frame import inspect_frame, write_evidence, EXIT_CODES

pixels = b'synthetic-rgb'
progress = {'filled_pixels': 7, 'bar_width': 177}
reward = {'reward_kind': 'item', 'reward_name': 'Dawn Stone'}
aim = {'candidate_spheres': 1, 'target_screen': {'x': 128, 'y': 96},
       'offset': {'x': 0, 'y': 0}}
with patch('verify_sphere_prefire_frame.read_capture_reward', side_effect=ValueError('not results')), \
     patch('verify_sphere_prefire_frame.read_capture_progress', return_value=progress) as meter, \
     patch('verify_sphere_prefire_frame.plan_sphere', return_value=aim) as target:
    result = inspect_frame(pixels, 256, 403, [])
    assert result[0] == 'aligned' and result[4]['fire_authorized']
    meter.assert_called_once_with(pixels, 256, 403, [])
    target.assert_called_once_with(pixels, 256, 403)

with patch('verify_sphere_prefire_frame.read_capture_reward', return_value=reward), \
     patch('verify_sphere_prefire_frame.read_capture_progress') as meter:
    result = inspect_frame(pixels, 256, 403, [])
    assert result[0] == 'reward' and result[1] == reward
    meter.assert_not_called()

with patch('verify_sphere_prefire_frame.read_capture_reward', side_effect=ValueError('not results')), \
     patch('verify_sphere_prefire_frame.read_capture_progress', side_effect=ValueError('not sphere')):
    assert inspect_frame(pixels, 256, 403, [])[0] == 'not_encounter'

with patch('verify_sphere_prefire_frame.read_capture_reward', side_effect=ValueError('not results')), \
     patch('verify_sphere_prefire_frame.read_capture_progress', return_value=progress), \
     patch('verify_sphere_prefire_frame.plan_sphere', side_effect=ValueError('ambiguous')):
    assert inspect_frame(pixels, 256, 403, [])[0] == 'ambiguous'

unaligned = {'candidate_spheres': 1, 'target_screen': {'x': 150, 'y': 96},
             'offset': {'x': 22, 'y': 0}}
with patch('verify_sphere_prefire_frame.read_capture_reward', side_effect=ValueError('not results')), \
     patch('verify_sphere_prefire_frame.read_capture_progress', return_value=progress), \
     patch('verify_sphere_prefire_frame.plan_sphere', return_value=unaligned):
    result = inspect_frame(pixels, 256, 403, [])
    assert result[0] == 'unaligned' and not result[4]['fire_authorized']

with tempfile.TemporaryDirectory() as tmp:
    paths = {key: Path(tmp) / (key + '.json') for key in ('reward','progress','aim','gate')}
    for path in paths.values():
        path.write_text('{"stale": true}')
    write_evidence(paths, result)
    assert not paths['reward'].exists()
    assert json.loads(paths['gate'].read_text())['fire_authorized'] is False
    write_evidence(paths, ('ambiguous', None, progress, None, None))
    assert not paths['gate'].exists() and not paths['aim'].exists()
    write_evidence(paths, ('reward', reward, None, None, None))
    assert json.loads(paths['reward'].read_text()) == reward
    assert not paths['gate'].exists()

assert EXIT_CODES == {'aligned':0,'unaligned':10,'ambiguous':11,'not_encounter':12,'reward':20}
print('PASS: one fresh frame classifies reward/encounter/target/gate without stale authorization')
