"""Synthetic regression tests for screenshot-guided DS fallback aiming."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from plan_melonds_aim import (locate_clouds, locate_orbs, locate_spheres,
                              plan, plan_orb, plan_sphere)

WIDTH, HEIGHT = 256, 403
OFFSET = HEIGHT - 384


def frame(clouds):
    pixels = bytearray(WIDTH * HEIGHT * 3)
    for cx, cy in clouds:
        for y in range(cy + OFFSET - 3, cy + OFFSET + 4):
            for x in range(cx - 6, cx + 7):
                at = (y * WIDTH + x) * 3
                pixels[at:at + 3] = bytes((230, 90, 220))
    return pixels


near = frame([(107, 83), (30, 40), (220, 155)])
targets = locate_clouds(near, WIDTH, HEIGHT)
assert len(targets) == 3
p = plan(near, WIDTH, HEIGHT)
assert p["target_screen"] == {"x": 107, "y": 83}
assert p["offset"] == {"x": -21, "y": -13}
assert p["horizontal_key"] == "Left" and p["vertical_key"] == "Up"
assert p["candidate_clouds"] == 3
assert p["horizontal_seconds"] > 0 and p["vertical_seconds"] > 0

right = plan(frame([(155, 110)]), WIDTH, HEIGHT)
assert right["horizontal_key"] == "Right" and right["vertical_key"] == "Down"

for pixels, width, height in (
    (bytes(WIDTH * HEIGHT * 3), WIDTH, HEIGHT),
    (bytes(512 * HEIGHT * 3), 512, HEIGHT),
    (near[:-1], WIDTH, HEIGHT),
):
    try:
        plan(pixels, width, height)
    except ValueError:
        pass
    else:
        raise AssertionError("Invalid or empty screenshot accepted as a cloud target")

def orb_frame(coords):
    pixels = bytearray(WIDTH * HEIGHT * 3)
    for cx, cy in coords:
        for y in range(cy + OFFSET - 3, cy + OFFSET + 4):
            for x in range(cx - 3, cx + 4):
                at = (y * WIDTH + x) * 3
                pixels[at:at + 3] = bytes((251, 113, 130))
    return pixels


orbs = orb_frame([(65, 54), (213, 37), (43, 145)])
assert len(locate_orbs(orbs, WIDTH, HEIGHT)) == 3
orb = plan_orb(orbs, WIDTH, HEIGHT)
assert orb["target_screen"] == {"x": 65, "y": 54}
assert orb["candidate_orbs"] == 3
assert orb["horizontal_key"] == "Left" and orb["vertical_key"] == "Up"
assert not orb["within_safe_fire_radius"]
assert orb["reticle_distance_squared"] > 64
aligned = plan_orb(orb_frame([(128, 96)]), WIDTH, HEIGHT)
assert aligned["within_safe_fire_radius"] and aligned["reticle_distance_squared"] == 0
near_edge = plan_orb(orb_frame([(136, 96)]), WIDTH, HEIGHT)
assert near_edge["within_safe_fire_radius"]
outside = plan_orb(orb_frame([(137, 96)]), WIDTH, HEIGHT)
assert not outside["within_safe_fire_radius"]
try:
    plan_orb(frame([(107, 83)]), WIDTH, HEIGHT)
except ValueError:
    pass
else:
    raise AssertionError("Cloud pixels accepted as Dream Orbs")


# Only the known flat-background, near-white DS encounter fallback can be
# tracked. Never interpret an arbitrary textured frame as a capture target.
def sphere_frame(with_target=True):
    pixels = bytearray(bytes((203, 211, 219)) * (WIDTH * HEIGHT))
    if with_target:
        for y in range(70 + OFFSET, 130 + OFFSET):
            for x in range(70, 170):
                at = (y * WIDTH + x) * 3
                pixels[at:at + 3] = bytes((243, 243, 243))
        # A small near-white reticle must not become another sphere.
        for y in range(78 + OFFSET, 96 + OFFSET):
            for x in range(215, 233):
                at = (y * WIDTH + x) * 3
                pixels[at:at + 3] = bytes((255, 255, 255))
    return pixels

spheres = locate_spheres(sphere_frame(), WIDTH, HEIGHT)
assert len(spheres) == 1
assert spheres[0][:2] == (120, 99)
guided = plan_sphere(sphere_frame(), WIDTH, HEIGHT)
assert guided["target_screen"] == {"x": 120, "y": 99}
assert guided["horizontal_key"] == "Left" and guided["vertical_key"] == "Down"
assert guided["candidate_spheres"] == 1
for invalid in (
    sphere_frame(False),
    bytes(WIDTH * HEIGHT * 3),
    sphere_frame()[:-3],
):
    try:
        plan_sphere(invalid, WIDTH, HEIGHT)
    except ValueError:
        pass
    else:
        raise AssertionError("Unverified encounter backdrop or blank frame accepted")
print("PASS: conservative sphere silhouette planner ignores reticle and unknown scenes")

print("PASS: screenshot-driven cloud/Orb aim planner handles nearest target and invalid frames")
