#!/usr/bin/env python3
"""Entirely synthetic DARC/CLIM fixtures. No original game bytes are used."""
from pathlib import Path
from tempfile import TemporaryDirectory
import struct
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from inventory_darc import DarcError, parse_darc, inspect_bclim, inspect_tree


def synthetic_bclim():
    pix = bytes(range(8))
    return pix + struct.pack('<4sHHIII4sIHHII', b'CLIM', 0xfeff, 20,
                             0x02020000, 48, 1, b'imag', 16, 2, 2, 5, 8)


def synthetic_darc(payload):
    names = b'\x00\x00' + 'original'.encode('utf-16le') + b'\x00\x00'
    name_off = len(names)
    names += 'texture.bclim'.encode('utf-16le') + b'\x00\x00'
    table_size = 36 + len(names)
    offset = ((28 + table_size + 3) // 4) * 4
    nodes = (struct.pack('<III', 0x01000000, 0, 3) +
             struct.pack('<III', 0x01000002, 0, 3) +
             struct.pack('<III', name_off, offset, len(payload)))
    header = struct.pack('<4sHHIIIII', b'darc', 0xfeff, 28, 0x01000000,
                         offset + len(payload), 28, table_size, offset)
    return header + nodes + names + b'\x00' * (offset - 28 - table_size) + payload


blob = synthetic_darc(synthetic_bclim())
meta = parse_darc(blob)
assert meta == [{'path': 'original/texture.bclim', 'size': 48,
                 'offset': len(blob) - 48}]
assert inspect_bclim(blob[-48:]) == {
    'width': 2, 'height': 2, 'format_code': 5, 'image_bytes': 8,
    'version': 0x02020000}
with TemporaryDirectory() as d:
    root = Path(d)
    source = root / 'archives'
    source.mkdir()
    (source / 'sample.darc').write_bytes(blob)
    out = root / 'report.json'
    extracted = root / 'assets'
    report = inspect_tree(source, out, extracted)
    assert report['archive_count'] == 1 and report['file_count'] == 1
    assert report['extensions'] == {'.bclim': 1}
    assert (extracted / 'sample/original/texture.bclim').read_bytes() == synthetic_bclim()
    assert out.is_file()
    broken = root / 'bad'
    broken.mkdir()
    for case in (blob[:-1], b'XXXX' + blob[4:],
                 blob[:8] + b'\x01\x00\x00\x00' + blob[12:],
                 blob[:28 + 24] + struct.pack('<III', 9999, len(blob) - 48, 48) + blob[28 + 36:],
                 synthetic_darc(synthetic_bclim()[:-1])):
        (broken / 'sample.darc').write_bytes(case)
        try:
            inspect_tree(broken, root / 'bad.json')
        except DarcError:
            pass
        else:
            raise AssertionError('Invalid DARC/CLIM fixture accepted')
print('PASS: DARC inventory, BCLIM metadata, private extraction and malformed inputs')
