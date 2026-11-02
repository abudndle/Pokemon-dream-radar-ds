"""Validate heading recognition, especially wrong-screen and blank-frame failures."""
from pathlib import Path
import sys
import json
import struct
import subprocess
import tempfile
import zlib
import shutil
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from verify_melonds_navigation import (check_heading, font_rows, read_radar_counters,
                                       compare_radar_counters, compare_orb_counters,
                                       read_sphere_state, observe_search_state,
                                       read_capture_reward, read_capture_progress,
                                       read_shop_orb_balance, compare_shop_orb_balances,
                                       compare_restart_shop_orb_balances)

font = font_rows()
width, height = 256, 403
OFFSET = height - 384
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

# A live Orb can disappear by expiry after 210 frames, not only by
# collection. A shot plus lower active counter is NOT reward evidence.
expired_or_hit = compare_orb_counters({"clouds": 4, "orbs": 3},
                                      {"clouds": 4, "orbs": 2})
assert expired_or_hit["status"] == "orb_count_decreased_unattributed"
assert expired_or_hit["orbs_disappeared"] == 1
assert not expired_or_hit["orb_collection_observed"]
missed = compare_orb_counters({"clouds": 4, "orbs": 3},
                              {"clouds": 4, "orbs": 3})
assert missed["status"] == "orb_count_not_decreased"
assert not missed["orb_collection_observed"]
spawned = compare_orb_counters({"clouds": 4, "orbs": 1},
                               {"clouds": 4, "orbs": 3})
assert spawned["status"] == "orb_count_increased"
assert spawned["orbs_disappeared"] == 0
assert not spawned["orb_collection_observed"]

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


# A screenshot of an encounter is not a successful capture. Check the real
# gold HP meter and recognize a reward only on the separate Results screen.
meter = sphere_frame("SWIFT", "90")
for x in range(11, 11 + 88):
    for y in range(6, 15):
        at = ((y + OFFSET) * width + x) * 3
        meter[at:at + 3] = bytes((255, 255, 0))
progress = read_capture_progress(meter, width, height, font)
assert progress["filled_pixels"] == 88 and progress["bar_width"] == 177
assert progress["encounter"]["capture_class"] == "swift"
assert read_capture_progress(sphere_frame(), width, height, font)["filled_pixels"] == 0

def results_reward_frame(kind, name):
    result = bytearray(width * height * 3)
    def draw_at(x, y, message, rgb):
        for index, character in enumerate(message):
            for row in range(8):
                mask = font[(ord(character) - 32) * 8 + row]
                for column in range(6):
                    if mask & (1 << (5 - column)):
                        at = ((y + OFFSET + row) * width + x + index * 6 + column) * 3
                        result[at:at + 3] = bytes(rgb)
    draw_at(10, 8, "RESEARCH RESULTS", (255, 255, 255))
    prefix = "Caught: " if kind == "pokemon" else "Item: "
    color = (255, 255, 0) if kind == "pokemon" else (255, 255, 255)
    draw_at(16, 192 + 68, prefix + name, color)
    return result

assert read_capture_reward(results_reward_frame("pokemon", "Munna"),
                           width, height, font) == {
                               "reward_kind": "pokemon", "reward_name": "Munna"}
assert read_capture_reward(results_reward_frame("item", "Rare Candy"),
                           width, height, font) == {
                               "reward_kind": "item", "reward_name": "Rare Candy"}

# Exercise the actual command-line entry point, not just imported helpers.
# A missing argparse flag must fail CI before the emulator smoke test boots.
def write_png(path, raw):
    def chunk(kind, data):
        return (struct.pack(">I", len(data)) + kind + data +
                struct.pack(">I", zlib.crc32(kind + data) & 0xffffffff))
    rows = b"".join(
        b"\x00" + bytes(raw[y * width * 3:(y + 1) * width * 3])
        for y in range(height))
    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    path.write_bytes(b"\x89PNG\r\n\x1a\n" +
                     chunk(b"IHDR", header) +
                     chunk(b"IDAT", zlib.compress(rows)) +
                     chunk(b"IEND", b""))

if shutil.which("identify") and shutil.which("convert"):
    with tempfile.TemporaryDirectory() as tmp:
        png = Path(tmp) / "live.png"
        command = [sys.executable, str(Path(__file__).resolve().parents[1] /
                                       "tools" / "verify_melonds_navigation.py"), tmp]
        write_png(png, results_reward_frame("pokemon", "Munna"))
        reward = subprocess.run(command + ["--observe-reward-screenshot", str(png)],
                                capture_output=True, text=True)
        assert reward.returncode == 0, reward.stderr
        assert json.loads(reward.stdout)["reward_name"] == "Munna"
        results = subprocess.run(command + ["--observe-results-screenshot", str(png)],
                                 capture_output=True, text=True)
        assert results.returncode == 0, results.stderr
        assert json.loads(results.stdout)["state"] == "results"
        write_png(png, meter)
        progress_cli = subprocess.run(command + ["--observe-capture-progress", str(png)],
                                      capture_output=True, text=True)
        assert progress_cli.returncode == 0, progress_cli.stderr
        assert json.loads(progress_cli.stdout)["filled_pixels"] == 88
        rejected = subprocess.run(command + ["--observe-reward-screenshot", str(png)],
                                  capture_output=True, text=True)
        assert rejected.returncode != 0
    print("PASS: PNG-backed capture/reward CLI flags are registered and functional")
else:
    print("SKIP: PNG CLI integration requires ImageMagick; tested after installation in melonDS CI")

for invalid in (
    sphere_frame("SWIFT", "90"),
    results_reward_frame("pokemon", "NotASpecies"),
    results_reward_frame("item", "NotAnItem"),
    results_reward_frame("pokemon", "Rare Candy"),
    results_reward_frame("item", "Munna"),
):
    try:
        read_capture_reward(invalid, width, height, font)
    except ValueError:
        pass
    else:
        raise AssertionError("Unverified or wrong-catalog reward accepted")

print("PASS: capture meter and catalog-backed Pokemon/item results recognition")

print("PASS: gold capture-class and white timer independently verify live sphere screens")

print("PASS: emulator heading and radar-counter recognition reject blank, wrong-stage, shifted and scaled frames")


# A radar Orb-count decrease can mean expiry. Verify the separate saved Orb
# balance printed in the Development Lab shop (bottom DS screen) instead.
def shop_frame(balance, rgb=(255, 225, 40)):
    pixels = bytearray(width * height * 3)
    label = "Development Lab  ORBS " + str(balance)
    for index, letter in enumerate(label):
        for row in range(8):
            mask = font[(ord(letter) - 32) * 8 + row]
            for column in range(6):
                if mask & (1 << (5 - column)):
                    at = ((192 + 8 + OFFSET + row) * width + 8 + index * 6 + column) * 3
                    pixels[at:at + 3] = bytes(rgb)
    return pixels


for balance in (0, 1, 45, 4294967295):
    assert read_shop_orb_balance(shop_frame(balance), width, height, font) == {"saved_orbs": balance}
for invalid in (shop_frame(""), shop_frame("01"), shop_frame("4294967296"),
                shop_frame(15, rgb=(255, 255, 255)),
                bytes(width * height * 3)):
    try:
        read_shop_orb_balance(invalid, width, height, font)
    except ValueError:
        pass
    else:
        raise AssertionError("Invalid or wrong-color saved Orb balance accepted")
gain = compare_shop_orb_balances({"saved_orbs": 10}, {"saved_orbs": 13})
assert gain["orb_collection_observed"] and gain["saved_orbs_gained"] == 3
assert gain["status"] == "session_balance_increased_persistence_unverified"
assert gain["balance_increased"] and not gain["persistence_verified"]
assert "restart" in gain["limitations"].lower()
for previous, current in ((10, 10), (10, 9)):
    comparison = compare_shop_orb_balances({"saved_orbs": previous},
                                           {"saved_orbs": current})
    assert not comparison["orb_collection_observed"]
for invalid in ({"saved_orbs": -1}, {"saved_orbs": True},
                {"saved_orbs": 4294967296}):
    try:
        compare_shop_orb_balances(invalid, {"saved_orbs": 1})
    except ValueError:
        pass
    else:
        raise AssertionError("Invalid saved Orb comparison accepted")
print("PASS: saved Orb balance is independent of timed-out radar Orb entities")


# A balance increase during one process is not durable-save evidence.
# A second process must independently read the same balance after the first
# process exited and the emulator harness confirmed writable save media.
def restart_check(before, collected, restarted, **overrides):
    options = dict(first_pid=1001, restart_pid=1002,
                   first_process_exited=True, save_media_present=True)
    options.update(overrides)
    return compare_restart_shop_orb_balances(
        {"saved_orbs": before}, {"saved_orbs": collected},
        {"saved_orbs": restarted}, **options)

restored = restart_check(0, 2, 2)
assert restored["persistence_verified"]
assert restored["status"] == "clean_restart_orb_balance_restored"
assert restored["orbs_gained"] == 2
for args in ((0, 0, 0), (0, 2, 0), (0, 2, 1), (2, 1, 1)):
    assert not restart_check(*args)["persistence_verified"], args
for options in (
    {"first_pid": 1001, "restart_pid": 1001},
    {"first_process_exited": False},
    {"save_media_present": False},
):
    assert not restart_check(0, 2, 2, **options)["persistence_verified"]
for invalid in (
    {"first_pid": True}, {"restart_pid": 0},
    {"first_process_exited": 1}, {"save_media_present": "yes"},
):
    try:
        restart_check(0, 2, 2, **invalid)
    except ValueError:
        pass
    else:
        raise AssertionError("Invalid restart provenance accepted")
for invalid_balance in (True, -1, 4294967296, "2"):
    try:
        compare_restart_shop_orb_balances(
            {"saved_orbs": 0}, {"saved_orbs": 2},
            {"saved_orbs": invalid_balance}, first_pid=1001, restart_pid=1002,
            first_process_exited=True, save_media_present=True)
    except ValueError:
        pass
    else:
        raise AssertionError("Invalid restarted Orb balance accepted")
print("PASS: clean-restart Orb proof rejects same-process, missing-save and stale-balance evidence")


# Exercise the exact restarted-emulator CLI used by the smoke harness.
# The second process must not continue after an absent or invalid balance.
restart_cli = (Path(__file__).resolve().parents[1] /
               "tools" / "check_restored_orbs.py")
with tempfile.TemporaryDirectory() as tmp:
    observation = Path(tmp) / "restart-orbs.json"
    for balance in (1, 2, 4294967295):
        observation.write_text(json.dumps({"saved_orbs": balance}))
        result = subprocess.run([sys.executable, str(restart_cli), str(observation)],
                                capture_output=True, text=True)
        assert result.returncode == 0, result.stderr
        assert f"{balance} previously saved" in result.stdout
    for invalid in (0, -1, 4294967296, True, "2", None):
        observation.write_text(json.dumps({"saved_orbs": invalid}))
        result = subprocess.run([sys.executable, str(restart_cli), str(observation)],
                                capture_output=True, text=True)
        assert result.returncode != 0, invalid
    observation.write_text("{invalid json")
    assert subprocess.run([sys.executable, str(restart_cli), str(observation)],
                          capture_output=True).returncode != 0
    observation.unlink()
    assert subprocess.run([sys.executable, str(restart_cli), str(observation)],
                          capture_output=True).returncode != 0
smoke_source = (Path(__file__).resolve().parents[1] /
                "scripts" / "melonds_smoke.sh").read_text()
assert 'if [[ "${REQUIRE_PREEXISTING_ORB:-0}" == 1 ]]' in smoke_source
assert 'python3 tools/check_restored_orbs.py "$out/orb-balance-before.json"' in smoke_source
print("PASS: second-process Orb CLI rejects absent, zero and malformed saved balances")

# Restart may resume directly into the Development Lab shop rather than the
# title screen. Exercise the exact PNG-backed observer used at boot, with
# both a valid saved shop and a wrong-scene frame; no Nintendo assets needed.
if shutil.which("identify") and shutil.which("convert"):
    with tempfile.TemporaryDirectory() as tmp:
        boot_png = Path(tmp) / "01-title.png"
        observer = [sys.executable, str(Path(__file__).resolve().parents[1] /
                                        "tools" / "verify_melonds_navigation.py"),
                    tmp, "--observe-shop-orbs-screenshot", str(boot_png)]
        write_png(boot_png, shop_frame(2))
        restored_shop = subprocess.run(observer, capture_output=True, text=True)
        assert restored_shop.returncode == 0, restored_shop.stderr
        assert json.loads(restored_shop.stdout) == {"saved_orbs": 2}
        write_png(boot_png, radar_frame("CLOUDS 5  ORBS 0"))
        wrong_scene = subprocess.run(observer, capture_output=True, text=True)
        assert wrong_scene.returncode != 0, wrong_scene.stdout
    print("PASS: resumed shop boot pixels decoded; wrong scene rejected")
else:
    print("SKIP: resume-boot PNG integration requires ImageMagick")

# The strict second-process path must inspect boot pixels before touching
# the screen, and only short-circuit on an independently decoded shop balance.
boot_snapshot = smoke_source.index("snapshot 01-title")
resume_branch = smoke_source.index('if [[ "${REQUIRE_PREEXISTING_ORB:-0}" == 1 ]]', boot_snapshot)
first_touch = smoke_source.index("touch_ds 128 269", boot_snapshot)
assert boot_snapshot < resume_branch < first_touch
resume_block = smoke_source[resume_branch:first_touch]
assert '--observe-shop-orbs-screenshot "$out/01-title.png"' in resume_block
assert 'cp "$out/01-title.png" "$out/03-shop-orbs-before.png"' in resume_block
assert '--expected-balance "$EXPECTED_RESTORED_ORBS"' in resume_block
assert 'rm -f "$out/orb-balance-before.json"' in resume_block
print("PASS: strict restart checks resumed shop before title input, and falls back safely")

# A temporarily obscured sphere can become visible a few frames later.
# Preserve the safe-fire invariant: no beam while the target is ambiguous,
# at most three stationary samples, and no firing if all samples fail.
capture_start = smoke_source.index('for step in $(seq 1 "$capture_steps")')
capture_end = smoke_source.index('capture_last="$out/05-sphere-sweep-$step.png"', capture_start)
capture_section = smoke_source[capture_start:capture_end]
off = capture_section.index("xdotool keyup z")
samples = capture_section.index("for reacquire_sample in 1 2 3; do")
found = capture_section.index('if [[ "$reacquire_state" != found ]]')
on = capture_section.index("xdotool keydown --clearmodifiers z", samples)
assert off < samples < found < on
assert 'reacquire_state=ambiguous' in capture_section
assert 'reacquire_state=found' in capture_section
assert 'reacquire_state=ended' in capture_section
assert 'break' in capture_section[found:on]
assert '--observe-capture-progress "$reacquired"' in capture_section
assert '--observe-reward-screenshot "$reacquired"' in capture_section
print("PASS: three-frame sphere reacquisition never fires blindly or exceeds its bound")
