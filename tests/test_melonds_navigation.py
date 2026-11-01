"""Validate heading recognition, especially wrong-screen and blank-frame failures."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from verify_melonds_navigation import check_heading, font_rows

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
print("PASS: emulator heading recognition rejects blank, wrong-stage, shifted and scaled frames")
