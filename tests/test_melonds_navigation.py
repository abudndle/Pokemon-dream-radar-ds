"""Validate heading recognition, especially wrong-screen and blank-frame failures."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from verify_melonds_navigation import check_heading, font_rows, read_radar_counters

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
                    frame[at:at + 3] = b"\\xff\\xff\\xff"
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

print("PASS: emulator heading and radar-counter recognition reject blank, wrong-stage, shifted and scaled frames")
