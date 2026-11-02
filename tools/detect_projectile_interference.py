#!/usr/bin/env python3
"""Conservatively identify DS fallback hostile projectiles in a native RGB frame.

The renderer paints a 5x5 magenta core inside a 9x9 red/cyan body. A
projectile at the reticle can intercept an A shot before the sphere does.
This is diagnostic only: it must not authorize or suppress live firing.
Original 3DS artwork and partially occluded sprites may be missed.
"""
from math import hypot

RETICLE = (128, 96)
PROJECTILE_INTERCEPT_RADIUS = 12


def locate_projectiles(pixels, width, height):
    if (width != 256 or not 384 <= height <= 480
            or len(pixels) != width * height * 3):
        raise ValueError("Expected an unscaled 256px-wide native DS RGB frame")
    offset = height - 384

    def color(x, y):
        i = (y * width + x) * 3
        return pixels[i], pixels[i + 1], pixels[i + 2]

    def magenta(x, y):
        r, g, b = color(x, y)
        return r >= 230 and g <= 25 and b >= 230

    def body(x, y):
        r, g, b = color(x, y)
        return ((r >= 220 and g <= 40 and b <= 50)
                or (r <= 90 and g >= 170 and b >= 170))

    found = []
    # Ignore HUD, viewport edges and lower touchscreen. Both a dense
    # magenta core and a distinct red/cyan ring are required.
    for y in range(offset + 8, offset + 184):
        for x in range(8, 248):
            if not magenta(x, y):
                continue
            core = sum(magenta(x + dx, y + dy)
                       for dy in range(-2, 3) for dx in range(-2, 3))
            if core < 24:
                continue
            ring = sum(body(x + dx, y + dy)
                       for dy in range(-4, 5) for dx in range(-4, 5)
                       if abs(dx) == 4 or abs(dy) == 4)
            if ring < 12:
                continue
            if not any(abs(x - px) <= 5 and abs(y - offset - py) <= 5
                       for px, py in found):
                found.append((x, y - offset))
    return found


def describe_projectiles(pixels, width, height):
    points = locate_projectiles(pixels, width, height)
    distances = [hypot(x - RETICLE[0], y - RETICLE[1]) for x, y in points]
    nearest = min(distances, default=None)
    return {
        "projectile_centers": [{"x": x, "y": y} for x, y in points],
        "nearest_projectile_distance_pixels": round(nearest, 2) if nearest is not None else None,
        "projectile_near_reticle": (nearest is not None and
                                    nearest <= PROJECTILE_INTERCEPT_RADIUS),
    }
