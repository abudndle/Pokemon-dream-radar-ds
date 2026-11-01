#!/usr/bin/env python3
"""Find a visible pink-shadow cloud in an actual unscaled melonDS DS screenshot.

This is a provisional DS fallback targeting aid for emulator testing. It does
not recognize original proprietary sprites or prove that firing hits a cloud.
"""
import argparse
import json
from pathlib import Path
import subprocess


def locate_clouds(pixels, width, height):
    if width != 256 or not 384 <= height <= 480 or len(pixels) != width * height * 3:
        raise ValueError("Expected an unscaled 256px-wide DS screenshot")
    offset = height - 384
    marked = set()
    for y in range(offset + 24, offset + 174):
        for x in range(12, 244):
            at = (y * width + x) * 3
            r, g, b = pixels[at:at + 3]
            if r >= 160 and b >= 150 and r >= g + 25 and b >= g + 25:
                marked.add((x, y))
    found = []
    while marked:
        first = marked.pop()
        stack = [first]
        component = [first]
        while stack:
            x, y = stack.pop()
            for ny in (y - 1, y, y + 1):
                for nx in (x - 1, x, x + 1):
                    p = (nx, ny)
                    if p in marked:
                        marked.remove(p)
                        stack.append(p)
                        component.append(p)
        if not 20 <= len(component) <= 500:
            continue
        xs, ys = zip(*component)
        if not 5 <= max(xs) - min(xs) <= 38 or not 3 <= max(ys) - min(ys) <= 32:
            continue
        cx = round(sum(xs) / len(xs))
        cy = round(sum(ys) / len(ys)) - offset
        found.append((cx, cy, len(component)))
    return sorted(found, key=lambda c: ((c[0] - 128) ** 2 + (c[1] - 96) ** 2, -c[2]))


def plan(pixels, width, height):
    targets = locate_clouds(pixels, width, height)
    if not targets:
        raise ValueError("No pink-shadow cloud found; aim is unverified")
    x, y, count = targets[0]
    dx, dy = x - 128, y - 96
    return {"target_screen": {"x": x, "y": y},
            "offset": {"x": dx, "y": dy},
            "horizontal_key": "Right" if dx > 0 else "Left" if dx < 0 else "none",
            "vertical_key": "Down" if dy > 0 else "Up" if dy < 0 else "none",
            "horizontal_seconds": round(min(0.25, abs(dx) / 360), 3),
            "vertical_seconds": round(min(0.25, abs(dy) / 360), 3),
            "candidate_clouds": len(targets),
            "limitations": "Approximate aiming based on public DS fallback sprite colors; hit not verified."}



def locate_orbs(pixels, width, height):
    """Locate red/pink 9px Dream Orb interiors, excluding UI and clouds."""
    if width != 256 or not 384 <= height <= 480 or len(pixels) != width * height * 3:
        raise ValueError("Expected an unscaled 256px-wide DS screenshot")
    offset = height - 384
    marked = set()
    for y in range(offset + 24, offset + 174):
        for x in range(12, 244):
            at = (y * width + x) * 3
            r, g, b = pixels[at:at + 3]
            if r >= 235 and 75 <= g <= 155 and 90 <= b <= 180 and r >= g + 80:
                marked.add((x, y))
    found = []
    while marked:
        first = marked.pop()
        stack = [first]
        component = [first]
        while stack:
            x, y = stack.pop()
            for ny in (y - 1, y, y + 1):
                for nx in (x - 1, x, x + 1):
                    p = (nx, ny)
                    if p in marked:
                        marked.remove(p)
                        stack.append(p)
                        component.append(p)
        if not 20 <= len(component) <= 150:
            continue
        xs, ys = zip(*component)
        if not 4 <= max(xs) - min(xs) <= 16 or not 4 <= max(ys) - min(ys) <= 16:
            continue
        found.append((round(sum(xs) / len(xs)),
                      round(sum(ys) / len(ys)) - offset, len(component)))
    return sorted(found, key=lambda c: ((c[0] - 128) ** 2 + (c[1] - 96) ** 2, -c[2]))


def plan_orb(pixels, width, height):
    targets = locate_orbs(pixels, width, height)
    if not targets:
        raise ValueError("No pink Dream Orb found; orb collection unverified")
    x, y, count = targets[0]
    dx, dy = x - 128, y - 96
    return {"target_screen": {"x": x, "y": y},
            "offset": {"x": dx, "y": dy},
            "horizontal_key": "Right" if dx > 0 else "Left" if dx < 0 else "none",
            "vertical_key": "Down" if dy > 0 else "Up" if dy < 0 else "none",
            "horizontal_seconds": round(min(0.5, abs(dx) / 360), 3),
            "vertical_seconds": round(min(0.5, abs(dy) / 360), 3),
            "candidate_orbs": len(targets),
            "reticle_distance_squared": dx * dx + dy * dy,
            "within_safe_fire_radius": dx * dx + dy * dy <= 8 * 8,
            "limitations": "Approximate screenshot aim; Orb collection must be confirmed by counters."}



def locate_spheres(pixels, width, height):
    """Find large near-white encounter art on the known flat DS fallback scene.

    This is deliberately conservative: non-flat or original 3DS backgrounds
    are not supported, and a matching silhouette is not proof of a hit.
    """
    if width != 256 or not 384 <= height <= 480 or len(pixels) != width * height * 3:
        raise ValueError("Expected an unscaled 256px-wide DS screenshot")
    offset = height - 384
    def pixel(x, y):
        at = (y * width + x) * 3
        return pixels[at:at + 3]
    left = pixel(4, offset + 100)
    right = pixel(250, offset + 100)
    if max(abs(a - b) for a, b in zip(left, right)) > 12 or not (
            150 <= left[0] <= 225 and 150 <= left[1] <= 235 and
            150 <= left[2] <= 240):
        raise ValueError("Unknown or non-flat encounter backdrop; cannot safely track sphere")
    marked = set()
    for y in range(offset + 42, offset + 169):
        for x in range(12, 244):
            r, g, b = pixel(x, y)
            if r >= 230 and g >= 225 and b >= 225 and max(
                    abs(r - left[0]), abs(g - left[1]), abs(b - left[2])) >= 20:
                marked.add((x, y))
    candidates = []
    while marked:
        stack = [marked.pop()]
        xs, ys = [], []
        while stack:
            x, y = stack.pop()
            xs.append(x)
            ys.append(y)
            for nx, ny in ((x - 1, y), (x + 1, y),
                           (x, y - 1), (x, y + 1)):
                if (nx, ny) in marked:
                    marked.remove((nx, ny))
                    stack.append((nx, ny))
        # Exclude the small fixed reticle and individual HUD glyphs.
        if len(xs) >= 350 and max(xs) - min(xs) >= 35 and max(ys) - min(ys) >= 20:
            candidates.append((round(sum(xs) / len(xs)),
                               round(sum(ys) / len(ys)) - offset, len(xs)))
    return sorted(candidates, key=lambda p: -p[2])


def plan_sphere(pixels, width, height):
    targets = locate_spheres(pixels, width, height)
    if len(targets) != 1:
        raise ValueError("No unique white encounter silhouette; guided aim unverified")
    x, y, count = targets[0]
    dx, dy = x - 128, y - 96
    return {"target_screen": {"x": x, "y": y},
            "offset": {"x": dx, "y": dy},
            "horizontal_key": "Right" if dx > 0 else "Left" if dx < 0 else "none",
            "vertical_key": "Down" if dy > 0 else "Up" if dy < 0 else "none",
            "horizontal_seconds": round(min(0.22, abs(dx) / 360), 3),
            "vertical_seconds": round(min(0.22, abs(dy) / 360), 3),
            "candidate_spheres": len(targets),
            "limitations": "White-silhouette DS fallback tracking only; moving target and capture are unverified."}


def plan_sphere_motion(previous_pixels, pixels, width, height):
    """Lead a moving DS fallback encounter silhouette using two real frames.

    The gap between screenshots is not a known number of DS frames. A small,
    bounded fraction of observed displacement is therefore only a heuristic,
    not an assertion of a hit or an original 3DS tracking algorithm.
    """
    current = plan_sphere(pixels, width, height)
    observed = current["target_screen"].copy()
    current["observed_target_screen"] = observed
    current["motion_prediction"] = "unavailable"
    try:
        previous = plan_sphere(previous_pixels, width, height)
    except ValueError:
        current["motion_prediction"] = "previous_frame_unrecognized"
        return current
    dx = observed["x"] - previous["target_screen"]["x"]
    dy = observed["y"] - previous["target_screen"]["y"]
    # Scene changes, teleports and erratic turns cannot be extrapolated safely.
    if abs(dx) > 60 or abs(dy) > 60:
        current["motion_prediction"] = "discontinuity"
        return current
    lead_x = max(-18, min(18, round(dx * 0.5)))
    lead_y = max(-18, min(18, round(dy * 0.5)))
    x = max(20, min(236, observed["x"] + lead_x))
    y = max(30, min(164, observed["y"] + lead_y))
    offset_x, offset_y = x - 128, y - 96
    current.update({
        "target_screen": {"x": x, "y": y},
        "offset": {"x": offset_x, "y": offset_y},
        "horizontal_key": "Right" if offset_x > 0 else "Left" if offset_x < 0 else "none",
        "vertical_key": "Down" if offset_y > 0 else "Up" if offset_y < 0 else "none",
        "horizontal_seconds": round(min(0.22, abs(offset_x) / 360), 3),
        "vertical_seconds": round(min(0.22, abs(offset_y) / 360), 3),
        "motion_prediction": "bounded",
        "observed_displacement": {"x": dx, "y": dy},
    })
    return current


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("screenshot", type=Path)
    parser.add_argument("--target", choices=("cloud", "orb", "sphere"), default="cloud")
    parser.add_argument("--previous-screenshot", type=Path,
                        help="Earlier sphere frame for bounded motion lead")
    args = parser.parse_args()
    size = subprocess.run(["identify", "-format", "%w %h", str(args.screenshot)],
                          capture_output=True, text=True, check=True, timeout=12)
    width, height = map(int, size.stdout.split())
    raw = subprocess.run(["convert", str(args.screenshot), "-depth", "8", "rgb:-"],
                         capture_output=True, check=True, timeout=12)
    planner = {"cloud": plan, "orb": plan_orb, "sphere": plan_sphere}[args.target]
    if args.previous_screenshot:
        if args.target != "sphere":
            parser.error("--previous-screenshot is only valid with --target sphere")
        previous_size = subprocess.run(
            ["identify", "-format", "%w %h", str(args.previous_screenshot)],
            capture_output=True, text=True, check=True, timeout=12)
        if tuple(map(int, previous_size.stdout.split())) != (width, height):
            raise ValueError("Sphere frames have different dimensions")
        previous_raw = subprocess.run(
            ["convert", str(args.previous_screenshot), "-depth", "8", "rgb:-"],
            capture_output=True, check=True, timeout=12)
        result = plan_sphere_motion(previous_raw.stdout, raw.stdout, width, height)
    else:
        result = planner(raw.stdout, width, height)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
