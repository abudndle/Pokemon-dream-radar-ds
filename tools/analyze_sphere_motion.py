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
from detect_projectile_interference import describe_projectiles
from sphere_prefire_gate import evaluate
from verify_melonds_navigation import decode_native_capture

VARIANTS = ("", "corrected-", "recorrected-", "stationary-")


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
        before, after, delta = (row.get("prefire_meter"),
                                row.get("postfire_meter"), row.get("meter_delta"))
        if (type(before) is not int or not 0 <= before <= 177
                or (after is not None and (type(after) is not int or not 0 <= after <= 177))
                or (delta is not None and type(delta) is not int)
                or delta != (after - before if after is not None else None)):
            raise ValueError(f"Contradictory pre/postfire meter row at step {step}")
        candidates = []
        for variant in VARIANTS:
            path = directory / f"sphere-prefire-{variant}inspection-{step}.json"
            if path.is_file():
                inspector = _read_object(path)
                if inspector.get("fire_executed") is True:
                    if (inspector.get("status") != "aligned"
                            or inspector.get("fire_authorized") is not True):
                        raise ValueError(f"Contradictory firing inspector at step {step}")
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
                 "postfire_status": "missing_frame",
                 "prefire_projectile_status": "missing_frame",
                 "prefire_projectile_centers": None,
                 "prefire_projectile_near_reticle": None,
                 "prefire_projectile_distance_pixels": None}
        # A fresh prefire PNG may show a hostile ball close enough to
        # intercept the shot. This is diagnostic, not a firing veto: the
        # ball can move before the emulator handles A, and defensive shots
        # against projectiles are legitimate gameplay.
        prefire = directory / f"05-sphere-prefire-{candidates[0]}{step}.png"
        if prefire.is_file():
            pixels, width, height = decode_native_capture(prefire)
            projectile = describe_projectiles(pixels, width, height)
            entry.update({
                "prefire_projectile_status": "inspected",
                "prefire_projectile_centers": projectile["projectile_centers"],
                "prefire_projectile_near_reticle": projectile["projectile_near_reticle"],
                "prefire_projectile_distance_pixels":
                    projectile["nearest_projectile_distance_pixels"],
            })
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
    if ("inspector_reported_fire_pulses" in report
            and report["inspector_reported_fire_pulses"] != len(observations)):
        raise ValueError("Capture summary pulse count disagrees with fired rows")
    recognized = [o for o in observations if o["postfire_status"] == "unique_target"]
    distances = [o["postfire_reticle_distance_pixels"] for o in recognized]
    inspected = [o for o in observations if o["prefire_projectile_status"] == "inspected"]
    # Stratify measured meter changes by observed projectile proximity.
    # This is correlation, not a causal claim about projectile interception.
    # Missing prefire screenshots are UNKNOWN, never counted as clear.
    by_projectile = {}
    for label, selected in (
        ("near_reticle", [o for o in observations if o["prefire_projectile_near_reticle"] is True]),
        ("not_near_reticle", [o for o in observations if o["prefire_projectile_near_reticle"] is False]),
        ("unknown", [o for o in observations if o["prefire_projectile_near_reticle"] is None]),
    ):
        paired = [o for o in selected if o["meter_delta"] is not None]
        tracked = [o for o in selected if o["postfire_status"] == "unique_target"]
        by_projectile[label] = {
            "reported_pulses": len(selected),
            "paired_meter_observations": len(paired),
            "positive_meter_changes": sum(o["meter_delta"] > 0 for o in paired),
            "zero_meter_changes": sum(o["meter_delta"] == 0 for o in paired),
            "negative_meter_changes": sum(o["meter_delta"] < 0 for o in paired),
            "unpaired_pulses": len(selected) - len(paired),
            "postfire_targets_recognized": len(tracked),
            "median_postfire_displacement_pixels": (
                median(o["postfire_target_displacement_pixels"] for o in tracked)
                if tracked else None),
        }
    return {
        "kind": "melonDS-postfire-target-motion-diagnostics",
        "inspector_reported_pulses": len(observations),
        "postfire_targets_recognized": len(recognized),
        "postfire_targets_unrecognized": sum(
            o["postfire_status"] == "target_not_uniquely_recognized" for o in observations),
        "postfire_frames_missing": sum(
            o["postfire_status"] == "missing_frame" for o in observations),
        "prefire_projectile_frames_inspected": len(inspected),
        "prefire_projectile_frames_missing": len(observations) - len(inspected),
        "prefire_frames_with_projectiles": sum(
            bool(o["prefire_projectile_centers"]) for o in inspected),
        "prefire_projectiles_near_reticle": sum(
            o["prefire_projectile_near_reticle"] is True for o in inspected),
        "meter_response_by_projectile_proximity": by_projectile,
        "median_postfire_reticle_distance_pixels": median(distances) if distances else None,
        "postfire_near_reticle_observations": sum(d <= 15 for d in distances),
        "shots": observations,
        "limitations": ("Postfire screenshots occur after key release and possible target "
                        "motion. Hostile projectile recognition is fallback-only and may miss "
                        "occluded balls; proximity cannot establish an actual interception. "
                        "Alignment, movement and meter changes are diagnostics, "
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
