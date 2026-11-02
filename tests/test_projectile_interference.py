#!/usr/bin/env python3
"""Regress screenshot-only projectile diagnostics; never authorize firing."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from detect_projectile_interference import describe_projectiles, locate_projectiles

WIDTH, HEIGHT = 256, 403
OFFSET = HEIGHT - 384


def fixture(center=(128, 96), *, core=True, body=True):
    rgb = bytearray([200, 210, 220] * (WIDTH * HEIGHT))
    x, y = center
    y += OFFSET
    def put(px, py, color):
        i = (py * WIDTH + px) * 3
        rgb[i:i+3] = bytes(color)
    if body:
        for dy in range(-4, 5):
            for dx in range(-4, 5):
                put(x + dx, y + dy, (251, 0, 0))
    if core:
        for dy in range(-2, 3):
            for dx in range(-2, 3):
                put(x + dx, y + dy, (251, 0, 251))
    return bytes(rgb)

assert describe_projectiles(fixture(), WIDTH, HEIGHT)["projectile_near_reticle"]
far = describe_projectiles(fixture((110, 138)), WIDTH, HEIGHT)
assert far["projectile_centers"] == [{"x": 110, "y": 138}]
assert far["projectile_near_reticle"] is False
assert far["nearest_projectile_distance_pixels"] > 40
assert locate_projectiles(fixture(core=False), WIDTH, HEIGHT) == []
assert locate_projectiles(fixture(body=False), WIDTH, HEIGHT) == []
# Place a valid projectile on the lower touchscreen; never count it.
frame = bytearray([200, 210, 220] * (WIDTH * HEIGHT))
for dy in range(-4, 5):
    for dx in range(-4, 5):
        i = ((250 + dy) * WIDTH + 128 + dx) * 3
        frame[i:i+3] = bytes((251, 0, 251) if abs(dx) <= 2 and abs(dy) <= 2
                             else (251, 0, 0))
assert locate_projectiles(bytes(frame), WIDTH, HEIGHT) == []
for w, h, pixels in ((255, 403, fixture()), (256, 383, fixture()),
                     (256, 403, fixture()[:-1])):
    try:
        locate_projectiles(pixels, w, h)
    except ValueError:
        pass
    else:
        raise AssertionError("Invalid screenshot dimensions accepted")
print("PASS: native fallback projectile diagnostics reject false positives and touchscreen pixels")
