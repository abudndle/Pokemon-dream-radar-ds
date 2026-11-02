"""Synthetic regression tests for screenshot-guided DS fallback aiming."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from plan_melonds_aim import (locate_clouds, locate_cloud_edge_markers,
                              locate_orbs, locate_spheres, plan, plan_orb,
                              plan_sphere, plan_sphere_motion, plan_orb_motion)

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
assert p["target_type"] == "cloud"
assert p["candidate_edge_markers"] == 0
assert not p["within_safe_fire_radius"]
assert plan(frame([(128, 96)]), WIDTH, HEIGHT)["within_safe_fire_radius"]
assert plan(frame([(142, 96)]), WIDTH, HEIGHT)["within_safe_fire_radius"]
assert not plan(frame([(143, 96)]), WIDTH, HEIGHT)["within_safe_fire_radius"]
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


# A gold 11x11 cloud direction cue is not a cloud: it can guide movement,
# but must NEVER authorize A firing. The HUD and 7x7 Orb edge cue are excluded.
def edge_frame(x, y, size=11):
    pixels = bytearray(WIDTH * HEIGHT * 3)
    for py in range(y + OFFSET, y + OFFSET + size):
        for px in range(x, x + size):
            if py in (y + OFFSET, y + OFFSET + size - 1) or px in (x, x + size - 1):
                at = (py * WIDTH + px) * 3
                pixels[at:at + 3] = bytes((251, 251, 0))
    return pixels


for x, y in ((234, 11), (234, 45), (11, 65), (95, 170)):
    edge = edge_frame(x, y)
    assert len(locate_cloud_edge_markers(edge, WIDTH, HEIGHT)) == 1
    guided_edge = plan(edge, WIDTH, HEIGHT)
    assert guided_edge["target_type"] == "edge_marker"
    assert guided_edge["candidate_clouds"] == 0
    assert guided_edge["candidate_edge_markers"] == 1
    assert not guided_edge["within_safe_fire_radius"]
    assert guided_edge["horizontal_key"] != "none" or guided_edge["vertical_key"] != "none"

for invalid in (edge_frame(90, 80), edge_frame(234, 45, 7)):
    assert locate_cloud_edge_markers(invalid, WIDTH, HEIGHT) == []
    try:
        plan(invalid, WIDTH, HEIGHT)
    except ValueError:
        pass
    else:
        raise AssertionError("HUD gold or small Orb edge cue accepted as a cloud")

# A real visible cloud takes priority over edge cues.
combined = bytearray(edge_frame(234, 45))
for y in range(96 + OFFSET - 3, 96 + OFFSET + 4):
    for x in range(128 - 6, 128 + 7):
        at = (y * WIDTH + x) * 3
        combined[at:at + 3] = bytes((230, 90, 220))
assert plan(combined, WIDTH, HEIGHT)["target_type"] == "cloud"
assert plan(combined, WIDTH, HEIGHT)["within_safe_fire_radius"]
print("PASS: cloud edge acquisition guides movement but never authorizes unsafe fire")


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
def sphere_frame(with_target=True, dx=0, dy=0):
    pixels = bytearray(bytes((203, 211, 219)) * (WIDTH * HEIGHT))
    # Large static white cloud belongs to the background, not the target.
    for y in range(70 + OFFSET, 130 + OFFSET):
        for x in range(70, 170):
            at = (y * WIDTH + x) * 3
            pixels[at:at + 3] = bytes((243, 243, 243))
    if with_target:
        # Connected dark-and-orange DS fallback sprite, centered at 120,99.
        for y in range(89 + OFFSET + dy, 110 + OFFSET + dy):
            for x in range(110 + dx, 131 + dx):
                at = (y * WIDTH + x) * 3
                pixels[at:at + 3] = bytes((24, 24, 32)) if x % 3 else bytes((251, 178, 24))
    # Red hostile projectile is only 13px across and must not be tracked.
    for y in range(80 + OFFSET, 93 + OFFSET):
        for x in range(215, 228):
            at = (y * WIDTH + x) * 3
            pixels[at:at + 3] = bytes((251, 40, 40))
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

# A fresh screenshot and an earlier one permit only bounded motion lead.
# The planner must never claim a hit or predict from a missing/unknown frame.
def shifted_sphere_frame(dx=0, dy=0):
    return sphere_frame(dx=dx, dy=dy)

previous = shifted_sphere_frame()
current = shifted_sphere_frame(20, -10)
predicted = plan_sphere_motion(previous, current, WIDTH, HEIGHT)
assert predicted["observed_target_screen"] == {"x": 140, "y": 89}
assert predicted["target_screen"] == {"x": 150, "y": 84}
assert predicted["observed_displacement"] == {"x": 20, "y": -10}
assert predicted["motion_prediction"] == "bounded"
assert predicted["horizontal_key"] == "Right"
assert predicted["vertical_key"] == "Up"
assert predicted["candidate_spheres"] == 1

stationary = plan_sphere_motion(previous, previous, WIDTH, HEIGHT)
assert stationary["target_screen"] == stationary["observed_target_screen"]
assert stationary["motion_prediction"] == "bounded"

unknown_previous = plan_sphere_motion(bytes(WIDTH * HEIGHT * 3),
                                      current, WIDTH, HEIGHT)
assert unknown_previous["motion_prediction"] == "previous_frame_unrecognized"
assert unknown_previous["target_screen"] == {"x": 140, "y": 89}

# A discontinuity is not a trustworthy velocity estimate.
teleport = plan_sphere_motion(shifted_sphere_frame(-60),
                              shifted_sphere_frame(30), WIDTH, HEIGHT)
assert teleport["motion_prediction"] == "discontinuity"
assert teleport["target_screen"] == teleport["observed_target_screen"]

try:
    plan_sphere_motion(previous, bytes(WIDTH * HEIGHT * 3), WIDTH, HEIGHT)
except ValueError:
    pass
else:
    raise AssertionError("Blank current sphere frame accepted as a target")
# During live shooting, a second large foreground sprite can appear.
# Preserve continuity with the previously unique encounter target, but never
# choose between two equally plausible objects or accept an unknown backdrop.
def paint_encounter(frame_pixels, cx, cy):
    for y in range(cy - 10 + OFFSET, cy + 11 + OFFSET):
        for x in range(cx - 10, cx + 11):
            at = (y * WIDTH + x) * 3
            frame_pixels[at:at + 3] = bytes((24, 24, 32))


with_distractor = bytearray(shifted_sphere_frame(10, 10))
paint_encounter(with_distractor, 205, 145)
assert len(locate_spheres(with_distractor, WIDTH, HEIGHT)) == 2
try:
    plan_sphere(with_distractor, WIDTH, HEIGHT)
except ValueError:
    pass
else:
    raise AssertionError("Unassociated multi-object frame accepted as unique")

tracked = plan_sphere_motion(previous, with_distractor, WIDTH, HEIGHT)
assert tracked["motion_match"] == "previous_unique_target"
assert tracked["candidate_spheres"] == 2
assert tracked["observed_target_screen"] == {"x": 130, "y": 109}
assert tracked["target_screen"] == {"x": 135, "y": 114}
assert tracked["motion_prediction"] == "bounded"

ambiguous = bytearray(sphere_frame(False))
paint_encounter(ambiguous, 95, 99)
paint_encounter(ambiguous, 145, 99)
assert len(locate_spheres(ambiguous, WIDTH, HEIGHT)) == 2
for old_frame, new_frame in (
    (previous, ambiguous),
    (bytes(WIDTH * HEIGHT * 3), with_distractor),
):
    try:
        plan_sphere_motion(old_frame, new_frame, WIDTH, HEIGHT)
    except ValueError:
        pass
    else:
        raise AssertionError("Ambiguous or untracked multiple sphere objects accepted")

print("PASS: temporal sphere association tracks only an unambiguous known target")

print("PASS: two-frame sphere motion lead is bounded and fails closed")

print("PASS: encounter art planner rejects static white cloud, small projectile and unknown scenes")

print("PASS: screenshot-driven cloud/Orb aim planner handles nearest target and invalid frames")


# Moving Orbs live for only 210 frames. Two stationary samples permit a
# bounded lead; predicted alignment alone must NEVER authorize a shot.
orb_previous = orb_frame([(100, 96)])
orb_current = orb_frame([(110, 96)])
orb_lead = plan_orb_motion(orb_previous, orb_current, WIDTH, HEIGHT)
assert orb_lead["observed_target_screen"] == {"x": 110, "y": 96}
assert orb_lead["target_screen"] == {"x": 115, "y": 96}
assert orb_lead["observed_displacement"] == {"x": 10, "y": 0}
assert orb_lead["motion_prediction"] == "bounded"
assert not orb_lead["within_safe_fire_radius"]
assert orb_lead["horizontal_key"] == "Left"
assert plan_orb_motion(orb_frame([(124, 96)]),
                       orb_frame([(128, 96)]), WIDTH, HEIGHT)["within_safe_fire_radius"]
assert plan_orb_motion(bytes(WIDTH * HEIGHT * 3),
                       orb_current, WIDTH, HEIGHT)["motion_prediction"] == "previous_frame_unrecognized"
assert plan_orb_motion(orb_frame([(60, 96)]),
                       orb_current, WIDTH, HEIGHT)["motion_prediction"] == "discontinuity"
ambiguous_orb = plan_orb_motion(orb_frame([(80, 96), (100, 96)]),
                                orb_frame([(90, 96)]), WIDTH, HEIGHT)
assert ambiguous_orb["motion_prediction"] == "ambiguous_previous_target"
assert ambiguous_orb["target_screen"] == {"x": 90, "y": 96}
for previous_frame, current_frame in (
    (orb_previous[:-3], orb_current),
    (orb_previous, orb_current[:-3]),
    (orb_previous, frame([(128, 96)])),
):
    try:
        plan_orb_motion(previous_frame, current_frame, WIDTH, HEIGHT)
    except ValueError:
        pass
    else:
        raise AssertionError("Invalid Orb motion frame accepted")
print("PASS: moving-Orb lead is bounded, ambiguity fails closed and fire uses observed alignment")


# Actual melonDS DRIFTING art is a pale pink ~22x18 sprite. The earlier
# dark-only tracker missed every frame of a real 160-shot emulator sweep.
# Test this fallback independently of the old synthetic dark sprite.
def pink_sphere_frame(cx=120, cy=99):
    pixels = bytearray(sphere_frame(False))
    for y in range(cy - 9 + OFFSET, cy + 9 + OFFSET):
        for x in range(cx - 11, cx + 11):
            at = (y * WIDTH + x) * 3
            pixels[at:at + 3] = bytes((251, 219, 243))
    return pixels


pink_targets = locate_spheres(pink_sphere_frame(), WIDTH, HEIGHT)
assert len(pink_targets) == 1
assert abs(pink_targets[0][0] - 120) <= 1
assert abs(pink_targets[0][1] - 99) <= 1
pink_motion = plan_sphere_motion(pink_sphere_frame(110, 99),
                                 pink_sphere_frame(120, 99), WIDTH, HEIGHT)
assert pink_motion["motion_prediction"] == "bounded"
assert pink_motion["target_screen"]["x"] >= 120
# The sphere can approach the lower boundary of the top DS viewport.
assert len(locate_spheres(pink_sphere_frame(120, 174), WIDTH, HEIGHT)) == 1
assert locate_spheres(sphere_frame(False), WIDTH, HEIGHT) == []
print("PASS: pale-pink live sphere silhouette is tracked without static-cloud false positives")


# A real encounter thumbnail may combine a dark outline and pale-pink
# interior. Both color passes see the SAME artwork; it must not be mistaken
# for two separate moving spheres, or the aim planner refuses to track it.
def mixed_palette_frame(centers):
    pixels = bytearray(sphere_frame(False))
    for cx, cy in centers:
        for y in range(cy - 12, cy + 13):
            for x in range(cx - 12, cx + 13):
                at = ((y + OFFSET) * WIDTH + x) * 3
                border = (abs(x - cx) == 12 or abs(y - cy) == 12)
                pixels[at:at + 3] = (bytes((24, 24, 32)) if border
                                     else bytes((251, 219, 243)))
    return pixels


mixed = mixed_palette_frame([(120, 99)])
assert len(locate_spheres(mixed, WIDTH, HEIGHT)) == 1
assert plan_sphere(mixed, WIDTH, HEIGHT)["target_screen"] == {"x": 120, "y": 99}
moving_mixed = plan_sphere_motion(mixed, mixed_palette_frame([(132, 105)]),
                                  WIDTH, HEIGHT)
assert moving_mixed["motion_prediction"] == "bounded"
assert moving_mixed["observed_target_screen"] == {"x": 132, "y": 105}

# Two distinct mixed-palette sprites must remain two candidates; a nearby
# distractor is not evidence that the actual capture target is unique.
separate = mixed_palette_frame([(80, 99), (185, 99)])
assert len(locate_spheres(separate, WIDTH, HEIGHT)) == 2
try:
    plan_sphere(separate, WIDTH, HEIGHT)
except ValueError:
    pass
else:
    raise AssertionError("Two distinct encounter sprites were deduplicated")
print("PASS: overlapping palette components collapse, separate spheres stay ambiguous")

# Actual melonDS DRIFTING encounter screenshots show a blue upper sprite
# and dark/orange lower sprite separated by a few background-colored rows.
# Both individually fail the original 14px-height test; together they form
# one visible capture target. No original sprite data is included here.
def split_color_sphere_frame(centers):
    pixels = bytearray(sphere_frame(False))
    for cx, cy in centers:
        for y in range(cy - 11, cy + 2):
            for x in range(cx - 8, cx + 9):
                at = ((y + OFFSET) * WIDTH + x) * 3
                pixels[at:at + 3] = bytes((81, 170, 219))
        for y in range(cy + 6, cy + 14):
            for x in range(cx - 11, cx + 12):
                at = ((y + OFFSET) * WIDTH + x) * 3
                pixels[at:at + 3] = bytes((24, 24, 32))
    return pixels


split = split_color_sphere_frame([(96, 107)])
split_targets = locate_spheres(split, WIDTH, HEIGHT)
assert len(split_targets) == 1
assert split_targets[0][0] == 96
assert 100 <= split_targets[0][1] <= 114
assert plan_sphere(split, WIDTH, HEIGHT)["candidate_spheres"] == 1
split_motion = plan_sphere_motion(split,
                                  split_color_sphere_frame([(105, 110)]),
                                  WIDTH, HEIGHT)
assert split_motion["motion_prediction"] == "bounded"
assert split_motion["observed_target_screen"]["x"] == 105

# Two separated blue/orange sprites must NOT be joined into one target.
separate_split = split_color_sphere_frame([(65, 107), (185, 107)])
assert len(locate_spheres(separate_split, WIDTH, HEIGHT)) == 2
try:
    plan_sphere(separate_split, WIDTH, HEIGHT)
except ValueError:
    pass
else:
    raise AssertionError("Distinct fragmented encounter targets merged")
print("PASS: real-style split blue/orange artwork is tracked, distinct sprites remain ambiguous")


# The DS renderer draws 9x9 Dream Orbs in four RGB555 fills:
# 0xC1DF pink, 0x83E0 green, 0x829F orange, 0xFC00 blue.
# Live screenshots may span several 45-frame color cycles while aiming.
ORB_RGB = {
    "pink": (255, 115, 132),
    "green": (0, 255, 0),
    "orange": (255, 165, 0),
    "blue": (0, 0, 255),
}


def colored_orb_frame(orbs, size=9):
    pixels = bytearray(WIDTH * HEIGHT * 3)
    radius = size // 2
    for cx, cy, color in orbs:
        for y in range(cy + OFFSET - radius, cy + OFFSET + radius + 1):
            for x in range(cx - radius, cx + radius + 1):
                at = (y * WIDTH + x) * 3
                pixels[at:at + 3] = bytes(ORB_RGB[color])
    return pixels


four_colors = colored_orb_frame([
    (70, 70, "pink"), (120, 95, "green"),
    (190, 60, "orange"), (160, 140, "blue"),
])
detected = locate_orbs(four_colors, WIDTH, HEIGHT)
assert len(detected) == 4, detected
assert {(x, y) for x, y, _ in detected} == {
    (70, 70), (120, 95), (190, 60), (160, 140),
}
assert plan_orb(four_colors, WIDTH, HEIGHT)["target_screen"] == {"x": 120, "y": 95}

# A palette change must not break stationary two-frame association or let
# predicted alignment alone authorize firing.
for old_color, new_color in (
    ("pink", "green"), ("green", "orange"),
    ("orange", "blue"), ("blue", "pink"),
):
    old = colored_orb_frame([(100, 96, old_color)])
    new = colored_orb_frame([(110, 96, new_color)])
    motion = plan_orb_motion(old, new, WIDTH, HEIGHT)
    assert motion["motion_prediction"] == "bounded"
    assert motion["observed_target_screen"] == {"x": 110, "y": 96}
    assert motion["target_screen"] == {"x": 115, "y": 96}
    assert not motion["within_safe_fire_radius"]

for color in ORB_RGB:
    aligned = plan_orb(colored_orb_frame([(128, 96, color)]), WIDTH, HEIGHT)
    assert aligned["within_safe_fire_radius"], color
    # Colored HUD glyphs are smaller than the 9x9 Orb silhouette.
    if color != "pink":
        assert locate_orbs(colored_orb_frame([(120, 95, color)], size=7),
                           WIDTH, HEIGHT) == []

# White, cyan, gold and red projectile colors are not Dream Orb targets.
for rgb in ((255, 255, 255), (0, 255, 255),
            (255, 255, 0), (255, 40, 40)):
    noise = bytearray(WIDTH * HEIGHT * 3)
    for y in range(92 + OFFSET, 101 + OFFSET):
        for x in range(124, 133):
            at = (y * WIDTH + x) * 3
            noise[at:at + 3] = bytes(rgb)
    assert locate_orbs(noise, WIDTH, HEIGHT) == [], rgb
print("PASS: four-color Dream Orb cycling, motion and observed-only safe firing")
