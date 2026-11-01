"""Synthetic regression tests for screenshot-guided DS fallback aiming."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from plan_melonds_aim import locate_clouds, plan

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

print("PASS: screenshot-driven cloud aim planner handles nearest target and invalid frames")
