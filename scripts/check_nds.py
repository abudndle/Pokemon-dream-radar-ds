#!/usr/bin/env python3
"""Shallow ROM container sanity check, not proof of boot compatibility."""
import pathlib
import struct
import sys


def check_rom(path):
    buf = pathlib.Path(path).read_bytes()
    if len(buf) < 512:
        raise ValueError("ROM missing the 512-byte DS header")
    if not buf[:12].rstrip(b'\x00\x20'):
        raise ValueError("ROM title is blank")
    sections = []
    for label, offset_pos, size_pos in (("ARM9", 0x20, 0x2C), ("ARM7", 0x30, 0x3C),
                                       ("NitroFS FNT", 0x40, 0x44), ("NitroFS FAT", 0x48, 0x4C)):
        start = struct.unpack_from("<I", buf, offset_pos)[0]
        size = struct.unpack_from("<I", buf, size_pos)[0]
        if start < 0x200 or size == 0 or start + size > len(buf):
            raise ValueError(f"{label} has an invalid or missing range")
        sections.append((start, start + size, label))
    for i, (start, end, label) in enumerate(sections):
        for other_start, other_end, other_label in sections[i + 1:]:
            if start < other_end and other_start < end:
                raise ValueError(f"{label} overlaps {other_label}")

    fat_start, fat_end, _ = sections[3]
    fat_size = fat_end - fat_start
    if fat_size % 8:
        raise ValueError("NitroFS FAT size is not a multiple of 8")
    for n in range(fat_size // 8):
        file_start, file_end = struct.unpack_from("<II", buf, fat_start + n * 8)
        # Zero/zero is legal for an unused or empty FAT entry.
        if file_start == file_end == 0:
            continue
        if file_start < 0x200 or file_end < file_start or file_end > len(buf):
            raise ValueError(f"NitroFS FAT entry {n} points outside ROM")
    return len(buf)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Usage: check_nds.py game.nds")
    try:
        size = check_rom(sys.argv[1])
    except (OSError, ValueError) as exc:
        sys.exit(f"NDS validation failed: {exc}")
    print(f"PASS: ROM header and ARM/NitroFS sections are present ({size} bytes). "
          "Boot on emulator/hardware still unverified.")
