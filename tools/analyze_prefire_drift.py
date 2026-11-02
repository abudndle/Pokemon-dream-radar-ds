#!/usr/bin/env python3
"""Measure observed sphere drift between camera planning and fresh prefire gates.

These are time-separated screenshot observations, not proof of hit or reward.
The initial target may be a motion prediction; never treat it as observed.
"""
import argparse
import json
from math import hypot
from pathlib import Path
from statistics import median

from sphere_prefire_gate import evaluate


def _point(value, label):
    if (not isinstance(value, dict) or type(value.get('x')) is not int
            or type(value.get('y')) is not int
            or not 0 <= value['x'] < 256 or not 0 <= value['y'] < 192):
        raise ValueError(f'Invalid {label} coordinates')
    return value


def _object(path):
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ValueError(f'Invalid JSON object: {path}')
    return value


def analyze(directory):
    directory = Path(directory)
    rows = []
    missing_plans = 0
    for gate_path in sorted(directory.glob('sphere-prefire-gate-*.json')):
        step_text = gate_path.stem.removeprefix('sphere-prefire-gate-')
        if not step_text.isdecimal() or int(step_text) < 1:
            raise ValueError(f'Invalid prefire gate filename: {gate_path}')
        gate = _object(gate_path)
        actual = _point(gate.get('observed_target_screen'), 'prefire gate')
        expected = evaluate({'candidate_spheres': 1, 'target_screen': actual,
                             'offset': {'x': actual['x'] - 128, 'y': actual['y'] - 96}})
        if gate != expected:
            raise ValueError(f'Prefire gate disagrees with screenshot target: {gate_path}')
        plan_path = directory / f'sphere-aim-{step_text}.json'
        if not plan_path.is_file():
            missing_plans += 1
            continue
        plan = _object(plan_path)
        planned = _point(plan.get('target_screen'), 'planned camera target')
        observed = plan.get('observed_target_screen')
        if observed is not None:
            observed = _point(observed, 'original observed target')
        rows.append({
            'step': int(step_text),
            'initial_observed_target': observed,
            'planned_camera_target': planned,
            'fresh_prefire_target': actual,
            'planned_to_prefire_residual_pixels': round(hypot(planned['x'] - actual['x'], planned['y'] - actual['y']), 2),
            'initial_to_prefire_displacement_pixels': (round(hypot(observed['x'] - actual['x'], observed['y'] - actual['y']), 2) if observed is not None else None),
            'prefire_reticle_distance_pixels': round(hypot(actual['x'] - 128, actual['y'] - 96), 2),
            'prefire_fire_authorized': gate['fire_authorized'],
        })
    residuals = [row['planned_to_prefire_residual_pixels'] for row in rows]
    movements = [row['initial_to_prefire_displacement_pixels'] for row in rows
                 if row['initial_to_prefire_displacement_pixels'] is not None]
    distances = [row['prefire_reticle_distance_pixels'] for row in rows]
    return {
        'kind': 'melonDS-sphere-prefire-drift-diagnostics',
        'prefire_gate_count': len(rows) + missing_plans,
        'paired_camera_plan_samples': len(rows),
        'missing_camera_plans': missing_plans,
        'observed_initial_target_samples': len(movements),
        'median_initial_to_prefire_displacement_pixels': median(movements) if movements else None,
        'median_planned_to_prefire_residual_pixels': median(residuals) if residuals else None,
        'median_prefire_reticle_distance_pixels': median(distances) if distances else None,
        'prefire_within_15_pixels': sum(distance <= 15 for distance in distances),
        'prefire_fire_authorized': sum(row['prefire_fire_authorized'] for row in rows),
        'rows': rows,
        'limitations': ('Camera plans may contain predictions, never firing authorization. '
                        'Initial-to-prefire motion uses only explicitly observed target positions. '
                        'Reticle distance and displacement do not prove hits or persistent rewards.'),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    try:
        result = json.dumps(analyze(args.directory), indent=2) + '\n'
        if args.output:
            args.output.write_text(result)
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        parser.exit(1, f'Prefire drift audit failed: {exc}\n')
    print(result, end='')


if __name__ == '__main__':
    main()
