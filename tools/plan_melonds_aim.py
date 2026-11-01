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
            "limitations": "Approximate screenshot aim; Orb collection must be confirmed by counters."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("screenshot", type=Path)
    parser.add_argument("--target", choices=("cloud", "orb"), default="cloud")
    args = parser.parse_args()
    size = subprocess.run(["identify", "-format", "%w %h", str(args.screenshot)],
                          capture_output=True, text=True, check=True, timeout=12)
    width, height = map(int, size.stdout.split())
    raw = subprocess.run(["convert", str(args.screenshot), "-depth", "8", "rgb:-"],
                         capture_output=True, check=True, timeout=12)
    result = (plan_orb if args.target == "orb" else plan)(raw.stdout, width, height)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
