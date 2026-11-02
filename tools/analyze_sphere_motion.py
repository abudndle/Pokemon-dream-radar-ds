#!/usr/bin/env python3
"""Correlate fired melonDS A pulses with later screenshot target motion.

The postfire screenshot is captured AFTER key release and may be many frames
later. Distances here diagnose motion/tracking, never prove a hit or capture.
"""
import argparse
import json
from math import hypot
from pathlib import Path
from statistics import median

from plan_melonds_aim import plan_sphere
from sphere_prefire_gate import evaluate
from verify_melonds_navigation import decode_native_capture

VARIANTS = ("", "corrected-", "stationary-")


def _read_object(path):
    data = json.loads(path.read_text())
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return data


def analyze(directory):
    directory = Path(directory)
    report = _read_object(directory / "sphere-attempt-report.json")
    if report.get("kind") != "melonDS-sphere-capture-progress":
        raise ValueError("Missing validated capture progress report")
    rows = report.get("postfire_meter_delta_samples")
    if not isinstance(rows, list):
        raise ValueError("Missing shot correlation rows")
    observations = []
    seen = set()
    for row in rows:
        if not isinstance(row, dict) or type(row.get("step")) is not int:
            raise ValueError("Malformed fired pulse row")
        step = row["step"]
        if step < 1 or step in seen:
            raise ValueError("Duplicate or invalid fired pulse step")
        seen.add(step)
        candidates = []
        for variant in VARIANTS:
            path = directory / f"sphere-prefire-{variant}inspection-{step}.json"
            if path.is_file() and _read_object(path).get("fire_executed") is True:
                candidates.append(variant)
        if len(candidates) != 1:
            raise ValueError(f"Fired step {step} lacks unique inspector evidence")
        gate = _read_object(directory / f"sphere-prefire-gate-{step}.json")
        point = gate.get("observed_target_screen")
        if not isinstance(point, dict):
            raise ValueError(f"Fired step {step} has no observed target")
        try:
            expected = evaluate({
                "candidate_spheres": 1, "target_screen": point,
                "offset": {"x": point["x"] - 128, "y": point["y"] - 96},
            })
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"Invalid fired gate at step {step}") from exc
        if gate != expected or gate["fire_authorized"] is not True:
            raise ValueError(f"Invalid firing authorization at step {step}")
        entry = {"step": step, "prefire_variant": candidates[0] or "initial",
                 "meter_delta": row.get("meter_delta"),
                 "prefire_target": point, "postfire_target": None,
                 "postfire_reticle_distance_pixels": None,
                 "postfire_target_displacement_pixels": None,
                 "postfire_status": "missing_frame"}
        screenshot = directory / f"05-sphere-sweep-{step}.png"
        if screenshot.is_file():
            pixels, width, height = decode_native_capture(screenshot)
            try:
                target = plan_sphere(pixels, width, height)["target_screen"]
            except ValueError:
                entry["postfire_status"] = "target_not_uniquely_recognized"
            else:
                entry.update({
                    "postfire_status": "unique_target",
                    "postfire_target": target,
                    "postfire_reticle_distance_pixels":
                        round(hypot(target["x"] - 128, target["y"] - 96), 2),
                    "postfire_target_displacement_pixels":
                        round(hypot(target["x"] - point["x"],
                                    target["y"] - point["y"]), 2),
                })
        observations.append(entry)
    recognized = [o for o in observations if o["postfire_status"] == "unique_target"]
    distances = [o["postfire_reticle_distance_pixels"] for o in recognized]
    return {
        "kind": "melonDS-postfire-target-motion-diagnostics",
        "inspector_reported_pulses": len(observations),
        "postfire_targets_recognized": len(recognized),
        "postfire_targets_unrecognized": sum(
            o["postfire_status"] == "target_not_uniquely_recognized" for o in observations),
        "postfire_frames_missing": sum(
            o["postfire_status"] == "missing_frame" for o in observations),
        "median_postfire_reticle_distance_pixels": median(distances) if distances else None,
        "postfire_near_reticle_observations": sum(d <= 15 for d in distances),
        "shots": observations,
        "limitations": ("Postfire screenshots occur after key release and possible target "
                        "motion. Alignment, movement and meter changes are diagnostics, "
                        "not proof of a hit, reward or saved restoration."),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        report = analyze(args.directory)
        content = json.dumps(report, indent=2) + "\n"
        if args.output:
            args.output.write_text(content)
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        parser.exit(1, f"Postfire motion diagnostic failed: {exc}\n")
    print(content, end="")


if __name__ == "__main__":
    main()
