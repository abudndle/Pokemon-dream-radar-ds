#!/usr/bin/env python3
"""Recognize actual DS screen headings, rejecting arbitrary frame changes.

The screenshot must contain a native-size 256x384 vertical DS display below
the emulator menu. Uses the game's existing 6x8 font, not OCR guesses.
ImageMagick supplies PNG decoding; source images are never modified.
"""
import argparse
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
STAGES = {
    "02-intro": (10, 8, "PROFESSOR BURNET"),
    "03-lab": (10, 8, "RESEARCH LAB"),
    "04-extensions": (10, 8, "SEARCH EXTENSIONS"),
    "05-radar": (6, 6, "CLOUDS"),
    "06-results": (10, 8, "RESEARCH RESULTS"),
    "07-lab-return": (10, 8, "RESEARCH LAB"),
}

def font_rows():
    source = (ROOT / "source/font6.h").read_text()
    rows = [int(value, 16) for value in re.findall(r"0x([0-9a-fA-F]+)", source)]
    if len(rows) != 768:
        raise ValueError("Unexpected game font dimensions")
    return rows

def check_heading(pixels, width, height, x, y, text, font, ink="white"):
    if width != 256 or not 384 <= height <= 480 or len(pixels) != width * height * 3:
        raise ValueError("Expected an unscaled vertical DS window")
    if ink not in ("white", "gold"):
        raise ValueError("Unsupported text color")
    y += height - 384  # Discard only the emulator's menu, not DS pixels.
    if x < 0 or y < 0 or x + len(text) * 6 > width or y + 8 > height:
        raise ValueError("Heading lies outside the captured DS screen")
    for index, character in enumerate(text):
        if not 32 <= ord(character) < 128:
            raise ValueError("Unsupported heading character")
        for row in range(8):
            mask = font[(ord(character) - 32) * 8 + row]
            for column in range(6):
                at = ((y + row) * width + x + index * 6 + column) * 3
                r, g, b = pixels[at:at + 3]
                colored = (r >= 220 and g >= 190 and b <= 110) if ink == "gold" else (r >= 220 and g >= 220 and b >= 220)
                if colored != bool(mask & (1 << (5 - column))):
                    raise ValueError(f"Expected rendered heading {text!r} was not found")

def read_radar_counters(pixels, width, height, font):
    """Read actual cloud/orb counts from the top-screen 6x8 game font.

    Unlike a static CLOUDS heading check, this establishes that the live
    radar screen has initialized its cloud population. It does not prove
    shooting, an encounter, or reward persistence.
    """
    x, y = 6, 6
    check_heading(pixels, width, height, x, y, "CLOUDS ", font)
    x += 7 * 6

    def matches(column, character):
        try:
            check_heading(pixels, width, height, column, y, character, font)
            return True
        except ValueError:
            return False

    def decimal(column):
        digits = ""
        for _ in range(2):
            candidates = [str(d) for d in range(10)
                          if matches(column, str(d))]
            if len(candidates) != 1:
                break
            digits += candidates[0]
            column += 6
        if not digits:
            raise ValueError("Radar counter is missing or illegible")
        return int(digits), column

    clouds, x = decimal(x)
    check_heading(pixels, width, height, x, y, "  ORBS ", font)
    x += 7 * 6
    orbs, x = decimal(x)
    # A trailing digit must not be silently accepted as part of another
    # number; the game draws both counters against a dark label rectangle.
    check_heading(pixels, width, height, x, y, " ", font)
    if not (0 <= clouds <= 30 and 0 <= orbs <= 24):
        raise ValueError("Radar counters exceed game entity capacity")
    return {"clouds": clouds, "orbs": orbs}


def read_sphere_state(pixels, width, height, font):
    """Identify a real capture screen from its gold class label AND white timer.

    This verifies an encounter was displayed, not that a capture succeeded.
    The timer is a separate UI element, reducing false positives from artwork.
    """
    classes = ("DRIFTING", "SWIFT", "ERRATIC", "LEGENDARY", "ITEM")
    matches = []
    for label in classes:
        try:
            check_heading(pixels, width, height, 10, 25, label, font, ink="gold")
        except ValueError:
            continue
        matches.append(label)
    if len(matches) != 1:
        raise ValueError("Capture class label is missing or ambiguous")
    x, y = 213, 7
    digits = ""
    for _ in range(4):
        candidates = []
        for digit in "0123456789":
            try:
                check_heading(pixels, width, height, x, y, digit, font)
            except ValueError:
                continue
            candidates.append(digit)
        if len(candidates) != 1:
            break
        digits += candidates[0]
        x += 6
    if not digits or (len(digits) > 1 and digits[0] == "0"):
        raise ValueError("Capture timer is missing or malformed")
    check_heading(pixels, width, height, x, y, " ", font)
    seconds = int(digits)
    if not 1 <= seconds <= 9999:
        raise ValueError("Capture timer is not active")
    return {"capture_class": matches[0].lower(), "remaining_seconds": seconds}


def observe_search_state(pixels, width, height, font):
    """Distinguish actual radar and encounter frames; never guess a transition."""
    try:
        return {"state": "radar", "radar_counters":
                read_radar_counters(pixels, width, height, font)}
    except ValueError:
        return {"state": "sphere", "encounter":
                read_sphere_state(pixels, width, height, font)}



def read_capture_reward(pixels, width, height, font):
    """Verify an actual results-screen reward using the game's font and catalog.

    This recognizes a displayed Pokemon/item reward, not a successful save,
    cartridge transfer, or persistence after restarting the emulator.
    """
    check_heading(pixels, width, height, 10, 8, "RESEARCH RESULTS", font)
    catalogs = (
        ("pokemon", "Caught: ", "gold", "game.c", "species_names"),
        ("item", "Item: ", "white", "item_catalog_generated.h",
         "original_item_names"),
    )
    matches = []
    for kind, prefix, ink, filename, variable in catalogs:
        source = (ROOT / "source" / filename).read_text()
        block = re.search(r"\b" + variable + r"\s*\[[^]]*\]\s*=\s*\{(.*?)\};",
                          source, re.S)
        if not block:
            raise ValueError(f"Cannot locate {variable} catalog")
        for name in re.findall(r'"([^"]+)"', block.group(1)):
            # The bottom screen begins at native y=192. Requiring the
            # trailing blank prevents a shorter prefix from matching a name.
            phrase = prefix + name + " "
            try:
                check_heading(pixels, width, height, 16, 192 + 68,
                              phrase, font, ink=ink)
            except ValueError:
                continue
            matches.append({"reward_kind": kind, "reward_name": name})
    if len(matches) != 1:
        raise ValueError("No unique stored Pokemon/item reward shown on results screen")
    return matches[0]


def read_capture_progress(pixels, width, height, font):
    """Read the visible gold capture meter; do not mistake a shot for a hit."""
    encounter = read_sphere_state(pixels, width, height, font)
    offset = height - 384
    # progress_bar(9,4,181,hp,240,GOLD): inner fill is x=11..187, y=6..14.
    # Check three interior rows to avoid a single background-colored pixel.
    def gold(x):
        for y in (8, 9, 10):
            at = ((y + offset) * width + x) * 3
            r, g, b = pixels[at:at + 3]
            if not (r >= 220 and g >= 190 and b <= 110):
                return False
        return True
    filled = 0
    for x in range(11, 188):
        if not gold(x):
            break
        filled += 1
    return {"encounter": encounter, "filled_pixels": filled,
            "bar_width": 177,
            "limitations": "Visual meter only; no reward, save, or restart verified."}

def compare_radar_counters(before, after):
    """Describe visible counter changes; never infer a successful capture."""
    removed = before["clouds"] - after["clouds"]
    orb_change = after["orbs"] - before["orbs"]
    if removed > 0:
        status = "cloud_count_decreased"
    elif removed or orb_change:
        status = "counters_changed_without_confirmed_cloud_removal"
    else:
        status = "no_counter_change"
    return {"status": status, "before": before, "after": after,
            "clouds_removed": max(0, removed), "orb_count_change": orb_change,
            "cloud_removal_observed": removed > 0,
            "limitations": "A counter change alone does not prove a sphere encounter, capture, reward, or save."}


def compare_orb_counters(before, after):
    """A decrease in visible live Orbs is evidence of collection, not saving."""
    collected = before["orbs"] - after["orbs"]
    return {"status": "orb_count_decreased" if collected > 0 else "orb_count_not_decreased",
            "before": before, "after": after,
            "orbs_collected": max(0, collected),
            "orb_collection_observed": collected > 0,
            "limitations": "Does not establish an encounter, reward persistence or restart."}


def decode_native_capture(path):
    size = subprocess.run(["identify", "-format", "%w %h", str(path)],
                          capture_output=True, text=True, check=True, timeout=12)
    width, height = map(int, size.stdout.split())
    if width != 256 or not 384 <= height <= 480:
        raise ValueError(f"Unscaled DS capture required: {path.name}")
    raw = subprocess.run(["convert", str(path), "-depth", "8", "rgb:-"],
                         capture_output=True, check=True, timeout=12)
    return raw.stdout, width, height


def verify(directory, stages=None):
    font = font_rows()
    results = []
    radar_before = None
    for name in (stages or STAGES):
        x, y, text = STAGES[name]
        path = Path(directory) / (name + ".png")
        pixels, width, height = decode_native_capture(path)
        check_heading(pixels, width, height, x, y, text, font)
        entry = {"file": path.name, "recognized_heading": text}
        if name == "05-radar":
            counters = read_radar_counters(pixels, width, height, font)
            if counters["clouds"] == 0:
                raise ValueError("Radar opened without any searchable clouds")
            entry["radar_counters"] = counters
            radar_before = counters
        results.append(entry)
    report = {"kind": "melonds-native-ds-navigation", "stages": results,
              "limitations": ["DS mode only; no DSi camera or hardware proof",
                              "A screenshot does not establish encounters, rewards, saves or frame rate"]}
    if radar_before is not None:
        post_path = Path(directory) / "05-radar-postfire.png"
        if post_path.is_file():
            pixels, width, height = decode_native_capture(post_path)
            try:
                after = read_radar_counters(pixels, width, height, font)
            except ValueError:
                try:
                    encounter = read_sphere_state(pixels, width, height, font)
                except ValueError:
                    report["postfire_observation"] = {
                        "file": post_path.name, "status": "radar_not_recognized",
                        "cloud_removal_observed": False,
                        "limitations": "Could be a scene transition or unreadable frame; not proof of a capture."}
                else:
                    report["postfire_observation"] = {
                        "file": post_path.name, "status": "sphere_encounter_observed",
                        "sphere_encounter_observed": True, "encounter": encounter,
                        "cloud_removal_observed": False,
                        "limitations": "An encounter screen does not prove a capture or saved reward."}
            else:
                report["postfire_observation"] = {
                    "file": post_path.name, **compare_radar_counters(radar_before, after)}
        else:
            report["postfire_observation"] = {
                "status": "not_captured", "cloud_removal_observed": False}
        postfire = report["postfire_observation"]
        orb_path = Path(directory) / "05-radar-orb-postfire.png"
        if orb_path.is_file() and "after" in postfire:
            pixels, width, height = decode_native_capture(orb_path)
            try:
                orb_after = read_radar_counters(pixels, width, height, font)
            except ValueError:
                report["orb_observation"] = {
                    "file": orb_path.name, "status": "radar_not_recognized",
                    "orb_collection_observed": False}
            else:
                report["orb_observation"] = {
                    "file": orb_path.name,
                    **compare_orb_counters(postfire["after"], orb_after)}
        else:
            report["orb_observation"] = {
                "status": "not_captured_or_not_radar", "orb_collection_observed": False}
    sphere_path = Path(directory) / "05-sphere-encounter.png"
    if sphere_path.is_file():
        pixels, width, height = decode_native_capture(sphere_path)
        try:
            encounter = read_sphere_state(pixels, width, height, font)
        except ValueError:
            report["sphere_observation"] = {
                "file": sphere_path.name, "verified": False,
                "status": "unrecognized_encounter"}
        else:
            report["sphere_observation"] = {
                "file": sphere_path.name, "verified": True,
                "status": "sphere_encounter_observed", "encounter": encounter,
                "limitations": "No capture, reward, or save verification."}
    else:
        report["sphere_observation"] = {
            "status": "not_captured", "verified": False}
    return report

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--stage", choices=STAGES,
                        help="Check one stage without writing a full navigation report")
    parser.add_argument("--touch-verified", choices=("0", "1"), default="0")
    parser.add_argument("--observe-search-screenshot", type=Path,
                        help="Print verified radar/encounter state from one actual screenshot")
    args = parser.parse_args()
    if sum(v is not None for v in
           (args.observe_search_screenshot, args.observe_reward_screenshot,
            args.observe_capture_progress)) > 1:
        parser.error("Select only one screenshot observation")
    if args.observe_reward_screenshot:
        pixels, width, height = decode_native_capture(args.observe_reward_screenshot)
        print(json.dumps(read_capture_reward(pixels, width, height, font_rows())))
        return
    if args.observe_capture_progress:
        pixels, width, height = decode_native_capture(args.observe_capture_progress)
        print(json.dumps(read_capture_progress(pixels, width, height, font_rows())))
        return
    if args.observe_search_screenshot:
        pixels, width, height = decode_native_capture(args.observe_search_screenshot)
        print(json.dumps(observe_search_state(pixels, width, height, font_rows())))
        return
    report = verify(args.directory, [args.stage] if args.stage else None)
    if args.stage:
        print(f"PASS: actual DS heading recognized for {args.stage}")
        return
    report["title_touch_verified"] = args.touch_verified == "1"
    if not report["title_touch_verified"]:
        report["limitations"].append("Stylus attempt did not enter intro; navigation used DS Start instead")
    (args.directory / "navigation-report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(f"PASS: {len(report['stages'])} actual DS navigation headings recognized")

if __name__ == "__main__":
    main()
