#!/usr/bin/env python3
"""Synthetic regression of camera plan versus fresh prefire screenshot drift."""
import json
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from analyze_prefire_drift import analyze, distance_bands
from sphere_prefire_gate import evaluate


def write(path, value):
    path.write_text(json.dumps(value))


with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    empty = analyze(root)
    assert empty['prefire_gate_count'] == 0
    assert empty['median_prefire_reticle_distance_pixels'] is None
    assert empty['median_initial_to_prefire_displacement_pixels'] is None
    def frame(step, x, y, planned_x, planned_y, observed=None):
        write(root / f'sphere-prefire-gate-{step}.json', evaluate({
            'candidate_spheres': 1, 'target_screen': {'x': x, 'y': y},
            'offset': {'x': x - 128, 'y': y - 96}}))
        plan = {'target_screen': {'x': planned_x, 'y': planned_y}}
        if observed is not None:
            plan['observed_target_screen'] = observed
        write(root / f'sphere-aim-{step}.json', plan)
    frame(1, 128, 96, 125, 96, {'x': 110, 'y': 96})
    frame(2, 160, 96, 140, 96)
    write(root / 'sphere-prefire-gate-3.json', evaluate({
        'candidate_spheres': 1, 'target_screen': {'x': 135, 'y': 96},
        'offset': {'x': 7, 'y': 0}}))
    result = analyze(root)
    assert result['prefire_gate_count'] == 3
    assert result['paired_camera_plan_samples'] == 2
    assert result['missing_camera_plans'] == 1
    assert result['observed_initial_target_samples'] == 1
    assert result['median_initial_to_prefire_displacement_pixels'] == 18
    assert result['median_planned_to_prefire_residual_pixels'] == 11.5
    assert result['median_prefire_reticle_distance_pixels'] == 16
    assert result['prefire_within_15_pixels'] == 1
    assert result['prefire_fire_authorized'] == 1
    assert result['prefire_distance_bands'] == {
        'aligned_0_to_15': 2, 'old_correction_16_to_43': 1,
        'expanded_correction_44_to_72': 0,
        'beyond_single_correction_over_72': 0}
    assert result['camera_plan_residual_bands'] == {
        'aligned_0_to_15': 1, 'old_correction_16_to_43': 1,
        'expanded_correction_44_to_72': 0,
        'beyond_single_correction_over_72': 0}
    assert distance_bands([0, 15, 16, 43, 44, 72, 73, 200]) == {
        'aligned_0_to_15': 2, 'old_correction_16_to_43': 2,
        'expanded_correction_44_to_72': 2,
        'beyond_single_correction_over_72': 2}
    # Noncanonical zero-padded names could count the same screenshot step
    # twice and inflate apparent tracking effectiveness. Fail closed.
    duplicate = root / 'sphere-prefire-gate-01.json'
    write(duplicate, json.loads((root / 'sphere-prefire-gate-1.json').read_text()))
    try:
        analyze(root)
    except ValueError as exc:
        assert 'filename' in str(exc)
    else:
        raise AssertionError('Noncanonical duplicate gate step accepted')
    duplicate.unlink()
    assert result['rows'][1]['initial_to_prefire_displacement_pixels'] is None
    original = json.loads((root / 'sphere-prefire-gate-1.json').read_text())
    write(root / 'sphere-prefire-gate-1.json', {**original, 'fire_authorized': False})
    try:
        analyze(root)
    except ValueError as exc:
        assert 'disagrees' in str(exc)
    else:
        raise AssertionError('Forged gate accepted')
    write(root / 'sphere-prefire-gate-1.json', original)
    plan_path = root / 'sphere-aim-1.json'
    original_plan = json.loads(plan_path.read_text())
    write(plan_path, {'target_screen': {'x': True, 'y': 96}})
    try:
        analyze(root)
    except ValueError as exc:
        assert 'coordinates' in str(exc)
    else:
        raise AssertionError('Boolean plan coordinate accepted')
    write(plan_path, original_plan)
    assert analyze(root)['prefire_fire_authorized'] == 1
print('PASS: camera drift diagnostics distinguish observed motion from predictions and invalid gates')
