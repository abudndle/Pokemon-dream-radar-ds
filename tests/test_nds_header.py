"""Tests for a shallow NDS sanity checker, without claiming a successful build."""
import pathlib
import struct
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'scripts'))
from check_nds import check_rom


def fixture(valid=True):
    data = bytearray(2048)
    data[:11] = b'DREAM RADAR'
    for offset_pos, size_pos, pos, size in ((0x20, 0x2C, 0x200, 64),
                                            (0x30, 0x3C, 0x280, 32),
                                            (0x40, 0x44, 0x300, 32),
                                            (0x48, 0x4C, 0x340, 32)):
        struct.pack_into('<I', data, offset_pos, pos)
        struct.pack_into('<I', data, size_pos, size)
    if not valid:
        struct.pack_into('<II', data, 0x40, 0x2000, 100)
    return data


with tempfile.TemporaryDirectory() as tmp:
    path = pathlib.Path(tmp) / 'build.nds'
    cases = [(fixture(), True, 'valid'),
             (fixture(False), False, 'out-of-bounds FNT'),
             (bytearray(48), False, 'short header')]
    overlap = fixture()
    struct.pack_into('<II', overlap, 0x48, 0x308, 32)
    cases.append((overlap, False, 'overlapping FNT/FAT'))
    malformed_fat = fixture()
    struct.pack_into('<II', malformed_fat, 0x48, 0x340, 31)
    cases.append((malformed_fat, False, 'invalid FAT length'))
    outside_file = fixture()
    struct.pack_into('<II', outside_file, 0x340, 0x500, 0x2000)
    cases.append((outside_file, False, 'out-of-bounds file'))
    reversed_file = fixture()
    struct.pack_into('<II', reversed_file, 0x340, 0x650, 0x500)
    cases.append((reversed_file, False, 'reversed file offsets'))
    valid_file = fixture()
    struct.pack_into('<II', valid_file, 0x340, 0x500, 0x600)
    cases.append((valid_file, True, 'valid file entry'))
    for data, accepted, name in cases:
        path.write_bytes(data)
        try:
            check_rom(path)
            assert accepted, f'{name}: invalid ROM accepted'
        except ValueError:
            assert not accepted, f'{name}: valid ROM rejected'
print('PASS: NDS header, section overlaps and NitroFS FAT bounds (8 cases)')
