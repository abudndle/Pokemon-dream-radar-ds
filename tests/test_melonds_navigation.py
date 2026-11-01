"""Validate heading recognition, especially wrong-screen and blank-frame failures."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from verify_melonds_navigation import (check_heading, font_rows, read_radar_counters,
                                       compare_radar_counters, compare_orb_counters,
                                       read_sphere_state, observe_search_state)

font = font_rows()
width, height = 256, 403
text = "RESEARCH LAB"
pixels = bytearray(width * height * 3)
for index, letter in enumerate(text):
    for row in range(8):
        mask = font[(ord(letter) - 32) * 8 + row]
        for column in range(6):
            if mask & (1 << (5 - column)):
                at = ((19 + 8 + row) * width + 10 + index * 6 + column) * 3
                pixels[at:at + 3] = b'\xff\xff\xff'
check_heading(pixels, width, height, 10, 8, text, font)
for raw, w, h, x, expected in (
    (bytes(len(pixels)), width, height, 10, text),
    (b'\xff' * len(pixels), width, height, 10, text),
    (pixels, width, height, 10, "SEARCH EXTENSIONS"),
    (pixels, width, height, 11, text),
    (pixels[:-1], width, height, 10, text),
    (pixels, 512, height, 10, text),
    (pixels, width, 900, 10, text),
):
    try:
        check_heading(raw, w, h, x, 8, expected, font)
    except ValueError:
        pass
    else:
        raise AssertionError("invalid or wrong-screen capture accepted")
# The radar must expose actual generated entity counters, not only a static
# CLOUDS heading. Synthetic font frames test parsing without emulator assets.
def radar_frame(label):
    frame = bytearray(width * height * 3)
    for index, letter in enumerate(label):
        for row in range(8):
            mask = font[(ord(letter) - 32) * 8 + row]
            for column in range(6):
                if mask & (1 << (5 - column)):
                    at = ((19 + 6 + row) * width + 6 + index * 6 + column) * 3
                    frame[at:at + 3] = bytes((255, 255, 255))
    return frame

for label, expected in (
    ("CLOUDS 5  ORBS 0", {"clouds": 5, "orbs": 0}),
    ("CLOUDS 30  ORBS 24", {"clouds": 30, "orbs": 24}),
    ("CLOUDS 1  ORBS 9", {"clouds": 1, "orbs": 9}),
):
    assert read_radar_counters(radar_frame(label), width, height, font) == expected

for label in (
    "CLOUDS 31  ORBS 0", "CLOUDS 5  ORBS 25",
    "CLOUDS 5 ORBS 0", "CLOUDS 5  ORBS X",
    "CLOUDS 5  ORBS 000", "CLOUDS 5  ORBS",
    "CLOUDS 5  ORBS 1X",
):
    try:
        read_radar_counters(radar_frame(label), width, height, font)
    except ValueError:
        pass
    else:
        raise AssertionError(f"Invalid radar counters accepted: {label!r}")

# A fire input is not equivalent to a successful hit. Report only observed
# changes in actual on-screen counters, including a no-hit result.
before = {"clouds": 5, "orbs": 0}
same = compare_radar_counters(before, {"clouds": 5, "orbs": 0})
assert same["status"] == "no_counter_change"
assert not same["cloud_removal_observed"]
hit = compare_radar_counters(before, {"clouds": 4, "orbs": 3})
assert hit["status"] == "cloud_count_decreased"
assert hit["clouds_removed"] == 1 and hit["orb_count_change"] == 3
assert hit["cloud_removal_observed"]
unexpected = compare_radar_counters(before, {"clouds": 6, "orbs": 0})
assert unexpected["status"] == "counters_changed_without_confirmed_cloud_removal"
assert not unexpected["cloud_removal_observed"]
orb_only = compare_radar_counters(before, {"clouds": 5, "orbs": 1})
assert orb_only["status"] == "counters_changed_without_confirmed_cloud_removal"
assert not orb_only["cloud_removal_observed"]

collected = compare_orb_counters({"clouds": 4, "orbs": 3},
                                 {"clouds": 4, "orbs": 2})
assert collected["status"] == "orb_count_decreased"
assert collected["orbs_collected"] == 1
assert collected["orb_collection_observed"]
missed = compare_orb_counters({"clouds": 4, "orbs": 3},
                              {"clouds": 4, "orbs": 3})
assert missed["status"] == "orb_count_not_decreased"
assert not missed["orb_collection_observed"]

# The dedicated sphere scene has a GOLD capture-class label and a WHITE timer.
# Do not confuse a radar cloud hit with a successful Pokemon/item capture.
def sphere_frame(label="DRIFTING", timer="90", color=(255, 255, 0)):
    frame = bytearray(width * height * 3)
    def draw(x, y, text, rgb):
        for index, letter in enumerate(text):
            for row in range(8):
                mask = font[(ord(letter) - 32) * 8 + row]
                for column in range(6):
                    if mask & (1 << (5 - column)):
                        at = ((19 + y + row) * width + x + index * 6 + column) * 3
                        frame[at:at + 3] = bytes(rgb)
    draw(10, 25, label, color)
    draw(213, 7, timer, (255, 255, 255))
    return frame

for label in ("DRIFTING", "SWIFT", "ERRATIC", "LEGENDARY", "ITEM"):
    actual = read_sphere_state(sphere_frame(label, "90"), width, height, font)
    assert actual == {"capture_class": label.lower(), "remaining_seconds": 90}
    observed = observe_search_state(sphere_frame(label, "90"), width, height, font)
    assert observed["state"] == "sphere" and observed["encounter"] == actual

assert observe_search_state(radar_frame("CLOUDS 5  ORBS 0"),
                            width, height, font)["state"] == "radar"

for invalid in (
    sphere_frame("DRIFTING", "0"),
    sphere_frame("DRIFTING", "000"),
    sphere_frame("DRIFTING", "99999"),
    sphere_frame("DRIFTING", ""),
    sphere_frame("DRIFTING", "90", (255, 255, 255)),
    sphere_frame("UNKNOWN", "90"),
    radar_frame("CLOUDS 5  ORBS 0"),
    bytearray(width * height * 3),
):
    try:
        read_sphere_state(invalid, width, height, font)
    except ValueError:
        pass
    else:
        raise AssertionError("Malformed or wrong-stage sphere frame accepted")

try:
    observe_search_state(bytearray(width * height * 3), width, height, font)
except ValueError:
    pass
else:
    raise AssertionError("Blank screen accepted as radar or sphere")

print("PASS: gold capture-class and white timer independently verify live sphere screens")

print("PASS: emulator heading and radar-counter recognition reject blank, wrong-stage, shifted and scaled frames")
