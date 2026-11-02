#!/usr/bin/env python3
"""Synthetic single-pass prefire checks; never substitutes for live melonDS."""
from pathlib import Path
import json
import subprocess
import sys
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from verify_sphere_prefire_frame import inspect_frame, write_evidence, pulse_if_aligned, correct_if_unaligned, main, EXIT_CODES

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

# The default inspector is observation-only. The explicit low-latency
# pulse cannot fire for reward, ambiguity, unaligned or ended encounters.
with patch('verify_sphere_prefire_frame.subprocess.run') as run, \
     patch('verify_sphere_prefire_frame.time.sleep') as sleep:
    for status in ('reward', 'not_encounter', 'ambiguous', 'unaligned'):
        assert pulse_if_aligned(status) is False
    run.assert_not_called()
    sleep.assert_not_called()
    assert pulse_if_aligned('aligned') is True
    assert run.call_count == 2
    assert run.call_args_list[0].args[0] == [
        'xdotool', 'keydown', '--clearmodifiers', 'z']
    assert run.call_args_list[1].args[0] == ['xdotool', 'keyup', 'z']
    sleep.assert_called_once_with(0.10)

# Even if a pulse fails midway, A is released. This is a host regression,
# not evidence that a moving sphere was hit in a real emulator.
with patch('verify_sphere_prefire_frame.subprocess.run') as run, \
     patch('verify_sphere_prefire_frame.time.sleep',
           side_effect=RuntimeError('interrupted')):
    try:
        pulse_if_aligned('aligned')
    except RuntimeError:
        pass
    else:
        raise AssertionError('Interrupted pulse should propagate failure')
    assert run.call_args_list[-1].args[0] == ['xdotool', 'keyup', 'z']

with patch('verify_sphere_prefire_frame.subprocess.run',
           side_effect=[subprocess.CalledProcessError(1, 'xdotool'), None]) as run:
    try:
        pulse_if_aligned('aligned')
    except subprocess.CalledProcessError:
        pass
    else:
        raise AssertionError('Failed keydown must not report a pulse')
    assert run.call_count == 2
    assert run.call_args_list[-1].args[0] == ['xdotool', 'keyup', 'z']

# A fresh-frame authorization must pulse before writing JSON sidecars.
# Mock every external operation; this checks ordering, not emulator hits.
with tempfile.TemporaryDirectory() as tmp:
    paths = [str(Path(tmp) / (name + ".json"))
             for name in ("reward", "progress", "aim", "gate")]
    args = ["verify_sphere_prefire_frame.py", str(Path(tmp) / "frame.png"),
            "--reward", paths[0], "--progress", paths[1],
            "--aim", paths[2], "--gate", paths[3], "--fire-aligned"]
    events = []
    with patch("sys.argv", args), \
         patch("verify_sphere_prefire_frame.decode_native_capture",
               return_value=(pixels, 256, 403)), \
         patch("verify_sphere_prefire_frame.font_rows", return_value=[]), \
         patch("verify_sphere_prefire_frame.inspect_frame",
               side_effect=lambda *a: (events.append("inspect") or
                                       ("aligned", None, progress, aim, {}))), \
         patch("verify_sphere_prefire_frame.pulse_if_aligned",
               side_effect=lambda status: (events.append("pulse") or True)), \
         patch("verify_sphere_prefire_frame.write_evidence",
               side_effect=lambda *a: (events.append("write") or "aligned")):
        assert main() == 0
    assert events == ["inspect", "pulse", "write"], events


# A first unaligned screenshot can move the camera without firing A. Only
# an independent second screenshot can authorize the eventual pulse.
with patch('verify_sphere_prefire_frame.subprocess.run') as run, \
     patch('verify_sphere_prefire_frame.time.sleep') as sleep:
    for status in ('aligned', 'reward', 'not_encounter', 'ambiguous'):
        assert correct_if_unaligned(status, unaligned) is False
    run.assert_not_called()
    assert correct_if_unaligned('unaligned', unaligned) is True
    assert [c.args[0] for c in run.call_args_list] == [
        ['xdotool', 'keyup', 'z'],
        ['xdotool', 'keydown', '--clearmodifiers', 'Right'],
        ['xdotool', 'keyup', 'Right']]
    sleep.assert_called_once_with(0.061)

# Both camera axes move concurrently; the shorter key releases first.
diagonal = {'candidate_spheres': 1, 'target_screen': {'x': 164, 'y': 114},
            'offset': {'x': 36, 'y': 18}}
with patch('verify_sphere_prefire_frame.subprocess.run') as run, \
     patch('verify_sphere_prefire_frame.time.sleep') as sleep:
    assert correct_if_unaligned('unaligned', diagonal) is True
    assert [c.args[0] for c in run.call_args_list] == [
        ['xdotool', 'keyup', 'z'],
        ['xdotool', 'keydown', '--clearmodifiers', 'Right'],
        ['xdotool', 'keydown', '--clearmodifiers', 'Down'],
        ['xdotool', 'keyup', 'Down'], ['xdotool', 'keyup', 'Right']]
    assert [round(c.args[0], 3) for c in sleep.call_args_list] == [0.05, 0.05]

# Live prefire residuals frequently exceed 43 pixels. A single fresh
# observation can now command up to 0.20 seconds of CAMERA movement only.
# Both axes are independently capped and released; this never fires A.
far = {'candidate_spheres': 1, 'target_screen': {'x': 238, 'y': 180},
       'offset': {'x': 110, 'y': 84}}
with patch('verify_sphere_prefire_frame.subprocess.run') as run, \
     patch('verify_sphere_prefire_frame.time.sleep') as sleep:
    assert correct_if_unaligned('unaligned', far) is True
    assert [c.args[0] for c in run.call_args_list] == [
        ['xdotool', 'keyup', 'z'],
        ['xdotool', 'keydown', '--clearmodifiers', 'Right'],
        ['xdotool', 'keydown', '--clearmodifiers', 'Down'],
        ['xdotool', 'keyup', 'Right'], ['xdotool', 'keyup', 'Down']]
    assert [round(c.args[0], 3) for c in sleep.call_args_list] == [0.20, 0.0]

# A moderate residual is no longer truncated at the old 0.12-second cap.
moderate = {'candidate_spheres': 1, 'target_screen': {'x': 182, 'y': 96},
            'offset': {'x': 54, 'y': 0}}
with patch('verify_sphere_prefire_frame.subprocess.run') as run, \
     patch('verify_sphere_prefire_frame.time.sleep') as sleep:
    assert correct_if_unaligned('unaligned', moderate) is True
    sleep.assert_called_once_with(0.15)
    assert run.call_args_list[-1].args[0] == ['xdotool', 'keyup', 'Right']

# A second camera correction must NOT chase an observed near miss:
# keep the reticle stationary and independently re-sample the sphere.
# This threshold is checked only after the same-frame unique-target gate.
with patch('verify_sphere_prefire_frame.subprocess.run') as run, \
     patch('verify_sphere_prefire_frame.time.sleep') as sleep:
    assert correct_if_unaligned('unaligned', unaligned, 26) is False
    edge = {'candidate_spheres': 1, 'target_screen': {'x': 154, 'y': 96},
            'offset': {'x': 26, 'y': 0}}
    assert correct_if_unaligned('unaligned', edge, 26) is False
    run.assert_not_called()
    sleep.assert_not_called()

beyond = {'candidate_spheres': 1, 'target_screen': {'x': 155, 'y': 96},
          'offset': {'x': 27, 'y': 0}}
with patch('verify_sphere_prefire_frame.subprocess.run') as run, \
     patch('verify_sphere_prefire_frame.time.sleep') as sleep:
    assert correct_if_unaligned('unaligned', beyond, 26) is True
    assert [c.args[0] for c in run.call_args_list] == [
        ['xdotool', 'keyup', 'z'],
        ['xdotool', 'keydown', '--clearmodifiers', 'Right'],
        ['xdotool', 'keyup', 'Right']]
    sleep.assert_called_once_with(0.075)

with patch('verify_sphere_prefire_frame.subprocess.run') as run:
    for invalid_threshold in (-1, 257, True, 26.0):
        try:
            correct_if_unaligned('unaligned', beyond, invalid_threshold)
        except ValueError:
            pass
        else:
            raise AssertionError('Invalid correction threshold accepted')
    for invalid_target in ({**beyond, 'motion_prediction': 'bounded'},
                           {**beyond, 'candidate_spheres': 2}):
        try:
            correct_if_unaligned('unaligned', invalid_target, 26)
        except ValueError:
            pass
        else:
            raise AssertionError('Unverified target bypassed distance threshold')
    run.assert_not_called()

# Predicted, ambiguous, aligned or forged offsets can never request a
# camera correction; no input is sent on any validation failure.
with patch('verify_sphere_prefire_frame.subprocess.run') as run:
    for bad in (aim, {**unaligned, 'motion_prediction': 'bounded'},
                {**unaligned, 'candidate_spheres': 2},
                {**unaligned, 'offset': {'x': 21, 'y': 0}},
                {**unaligned, 'target_screen': {'x': True, 'y': 96}}):
        try:
            correct_if_unaligned('unaligned', bad)
        except ValueError:
            pass
        else:
            raise AssertionError('Invalid correction gate accepted')
    run.assert_not_called()

# A failed keydown might still reach the emulator; release that axis.
with patch('verify_sphere_prefire_frame.subprocess.run',
           side_effect=[None, subprocess.CalledProcessError(1, 'xdotool'), None]) as run:
    try:
        correct_if_unaligned('unaligned', unaligned)
    except subprocess.CalledProcessError:
        pass
    else:
        raise AssertionError('Failed correction must propagate')
    assert run.call_args_list[-1].args[0] == ['xdotool', 'keyup', 'Right']

# The initial inspector corrects before serializing its evidence. Its
# unaligned status remains a no-fire decision despite camera movement.
with tempfile.TemporaryDirectory() as tmp:
    paths = [str(Path(tmp) / (name + ".json"))
             for name in ("reward", "progress", "aim", "gate")]
    args = ["verify_sphere_prefire_frame.py", str(Path(tmp) / "frame.png"),
            "--reward", paths[0], "--progress", paths[1],
            "--aim", paths[2], "--gate", paths[3],
            "--fire-aligned", "--correct-unaligned"]
    events = []
    with patch("sys.argv", args), \
         patch("verify_sphere_prefire_frame.decode_native_capture",
               return_value=(pixels, 256, 403)), \
         patch("verify_sphere_prefire_frame.font_rows", return_value=[]), \
         patch("verify_sphere_prefire_frame.inspect_frame",
               side_effect=lambda *a: (events.append("inspect") or
                                       ("unaligned", None, progress, unaligned, {}))), \
         patch("verify_sphere_prefire_frame.pulse_if_aligned",
               side_effect=lambda status: (events.append("no-fire") or False)), \
         patch("verify_sphere_prefire_frame.correct_if_unaligned",
               side_effect=lambda *a: (events.append("correct") or True)), \
         patch("verify_sphere_prefire_frame.write_evidence",
               side_effect=lambda *a: (events.append("write") or "unaligned")):
        assert main() == 10
    assert events == ["inspect", "no-fire", "correct", "write"], events

assert EXIT_CODES == {'aligned':0,'unaligned':10,'ambiguous':11,'not_encounter':12,'reward':20}
print('PASS: one fresh frame classifies reward/encounter/target/gate without stale authorization')
