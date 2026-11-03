#!/usr/bin/env python3
"""Classify one fresh melonDS prefire PNG with one pixel decode.

This combines reward, encounter, unique-target and observed-only gate checks.
No result authorizes firing from a previous screenshot or a motion prediction.
Exit statuses: 0 aligned, 10 unaligned, 11 ambiguous target,
12 not an encounter, 20 catalog-backed reward, 13 invalid input.
"""
import argparse
import json
from pathlib import Path
import subprocess
import time

from plan_melonds_aim import plan_sphere
from sphere_prefire_gate import evaluate
from verify_melonds_navigation import (decode_native_capture, font_rows,
                                       read_capture_progress, read_capture_reward)

EXIT_CODES = {"aligned": 0, "unaligned": 10, "ambiguous": 11,
              "not_encounter": 12, "reward": 20}


def inspect_frame(pixels, width, height, font):
    """Classify one screenshot, never trusting sidecar JSON or old aim plans."""
    try:
        reward = read_capture_reward(pixels, width, height, font)
    except ValueError:
        pass
    else:
        return "reward", reward, None, None, None
    try:
        progress = read_capture_progress(pixels, width, height, font)
    except ValueError:
        return "not_encounter", None, None, None, None
    try:
        aim = plan_sphere(pixels, width, height)
    except ValueError:
        return "ambiguous", None, progress, None, None
    gate = evaluate(aim)
    return ("aligned" if gate["fire_authorized"] else "unaligned",
            None, progress, aim, gate)


def write_evidence(paths, result):
    """Delete stale output first; only write observations from this frame."""
    status, reward, progress, aim, gate = result
    for path in paths.values():
        path.unlink(missing_ok=True)
    for key, value in (("reward", reward), ("progress", progress),
                       ("aim", aim), ("gate", gate)):
        if value is not None:
            paths[key].write_text(json.dumps(value, indent=2) + "\n")
    return status


def pulse_if_aligned(status):
    """Fire inside the fresh-frame inspector, minimizing post-gate delay.

    The only permitted pulse follows the same-frame unique-target gate.
    Always release A even if keydown, sleeping, or the emulator fails.
    The return value records an input pulse, NOT a verified hit.
    """
    if status != "aligned":
        return False
    try:
        subprocess.run(["xdotool", "keydown", "--clearmodifiers", "z"],
                       check=True, timeout=3)
        time.sleep(0.10)
    finally:
        subprocess.run(["xdotool", "keyup", "z"], check=True, timeout=3)
    return True



def correct_if_unaligned(status, aim, min_distance=0):
    """Move the camera immediately from a unique fresh *unaligned* frame.

    This is a bounded, no-fire correction. A second independent screenshot
    must authorize any subsequent shot. Derive keys from validated observed
    offsets, never from an earlier prediction or untrusted key strings.
    """
    if status != "unaligned":
        return False
    gate = evaluate(aim)
    if gate["fire_authorized"]:
        raise ValueError("Aligned gate cannot request camera correction")
    dx, dy = aim["offset"]["x"], aim["offset"]["y"]
    if type(min_distance) is not int or not 0 <= min_distance <= 256:
        raise ValueError("Invalid minimum camera correction distance")
    # Do not chase a near miss with another camera pulse. A stationary
    # independently decoded screenshot is safer for a moving sphere.
    if dx * dx + dy * dy <= min_distance * min_distance:
        return False
    # The earlier 0.12 s cap moved at most ~43 pixels. Actual melonDS
    # prefire diagnostics recorded many residuals above 50 pixels, leaving
    # the next independently checked frame predictably out of alignment.
    # Allow one larger bounded no-fire correction (<=72 px at 60 FPS).
    # A fresh screenshot still gates every subsequent A pulse.
    # Archived live melonDS pairs frequently reversed horizontal reticle
    # side after full-strength movement. Dampen horizontal camera travel,
    # including this inline correction path, while leaving the fresh-frame
    # authorization gate and observed coordinates completely unchanged.
    # Do not pulse an axis already within the 15px alignment tolerance.
    axes = []
    for displacement, negative, positive, gain in (
            (dx, "Left", "Right", 0.70),
            (dy, "Up", "Down", 1.0)):
        if abs(displacement) > 15:
            axes.append((negative if displacement < 0 else positive,
                         round(min(0.20, abs(displacement) * gain / 360), 3)))
    if not axes:
        # An unaligned Euclidean distance can have both individual axes
        # within 15px; waiting for another screenshot is safer than
        # injecting sub-frame camera pulses or pretending a shot is safe.
        return False
    held = []
    try:
        # No stale held A is allowed during camera motion.
        subprocess.run(["xdotool", "keyup", "z"], check=True, timeout=3)
        for key, seconds in axes:
            # Register before keydown: even a failing xdotool invocation
            # might have delivered the key and must be cleaned up.
            held.append(key)
            subprocess.run(["xdotool", "keydown", "--clearmodifiers", key],
                           check=True, timeout=3)
        elapsed = 0.0
        for key, seconds in sorted(axes, key=lambda axis: axis[1]):
            time.sleep(max(0.0, seconds - elapsed))
            elapsed = seconds
            subprocess.run(["xdotool", "keyup", key], check=True, timeout=3)
            held.remove(key)
    finally:
        for key in reversed(held):
            subprocess.run(["xdotool", "keyup", key], check=True, timeout=3)
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("screenshot", type=Path)
    for name in ("reward", "progress", "aim", "gate"):
        parser.add_argument("--" + name, required=True, type=Path)
    parser.add_argument("--fire-aligned", action="store_true",
                        help="Pulse DS A immediately after a fresh aligned observation; never on other statuses")
    parser.add_argument("--correct-unaligned", action="store_true",
                        help="Move camera from fresh unaligned target; require another screenshot before firing")
    parser.add_argument("--correct-min-distance", type=int, default=0,
                        help="Skip no-fire correction when the observed reticle distance is at or below this pixel threshold")
    args = parser.parse_args()
    paths = {name: getattr(args, name) for name in ("reward", "progress", "aim", "gate")}
    # A failed decode must not leave stale gate JSON that looks authorized.
    for path in paths.values():
        path.unlink(missing_ok=True)
    try:
        pixels, width, height = decode_native_capture(args.screenshot)
        result = inspect_frame(pixels, width, height, font_rows())
        status = result[0]
        # The unique-target gate has already been evaluated from this fresh
        # decoded frame. Pulse immediately: serializing three JSON sidecars
        # before keydown previously added avoidable moving-target latency.
        # Evidence is written only after the bounded pulse has released A;
        # any pulse/write failure is still a hard error, never a claimed hit.
        fired = pulse_if_aligned(status) if args.fire_aligned else False
        corrected = (correct_if_unaligned(status, result[3], args.correct_min_distance)
                     if args.correct_unaligned else False)
        write_evidence(paths, result)
    except (OSError, ValueError, subprocess.CalledProcessError,
            subprocess.TimeoutExpired) as exc:
        # A failed key pulse must never leave an authorized gate sidecar.
        paths["gate"].unlink(missing_ok=True)
        parser.exit(13, f"Prefire frame inspection failed: {exc}\n")
    print(json.dumps({"status": status, "fire_authorized": status == "aligned",
                      "fire_executed": fired, "camera_correction_executed": corrected,
                      "limitations": "Fresh fallback screenshot only; not proof of hit, capture, save or restart."}))
    return EXIT_CODES[status]


if __name__ == "__main__":
    raise SystemExit(main())
