#!/usr/bin/env python3
"""Synthetic archive fixtures only; original game asset payloads are not used."""
import json
from pathlib import Path
import struct
import sys
from tempfile import TemporaryDirectory
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from audit_darc_asset_kinds import audit, classify_item, safe_archive_name
from inventory_darc import DarcError, parse_darc


def resource(extension):
    if extension == '.bclim':
        pixels = b'\xff\xff' * 4
        return pixels + struct.pack('<4sHHIII4sIHHII', b'CLIM', 0xfeff, 20,
                                    0x02020000, 48, 1, b'imag', 16, 2, 2, 5, 8)
    if extension == '.bclan':
        return b'CLAN\xff\xfe\x14\x00' + b'\x00' * 12
    if extension == '.bclyt':
        return b'CLYT\xff\xfe\x14\x00' + b'\x00' * 12
    if extension == '.msbt':
        return b'MsgStdBn\xff\xfe' + b'\x00' * 12
    if extension == '.bcres':
        return b'CGFX' + b'\x00' * 16
    raise AssertionError(extension)


def create_darc(name, payload, dot=False):
    # Original DARCs may contain a leading '.' directory marker, which is
    # *not* a path component or a traversal instruction.
    names = b'\x00\x00'
    if dot:
        dot_offset = len(names)
        names += '.'.encode('utf-16le') + b'\x00\x00'
    file_name_offset = len(names)
    names += name.encode('utf-16le') + b'\x00\x00'
    count = 3 if dot else 2
    table_size = 12 * count + len(names)
    data_offset = (28 + table_size + 3) // 4 * 4
    nodes = struct.pack('<III', 0x01000000, 0, count)
    if dot:
        nodes += struct.pack('<III', 0x01000000 | dot_offset, 0, count)
    nodes += struct.pack('<III', file_name_offset, data_offset, len(payload))
    header = struct.pack('<4sHHIIIII', b'darc', 0xfeff, 28, 0x01000000,
                         data_offset + len(payload), 28, table_size, data_offset)
    return header + nodes + names + b'\x00'*(data_offset - 28 - table_size) + payload


def expect_error(callback, fragment=None):
    try:
        callback()
    except (DarcError, ValueError) as e:
        if fragment is not None:
            assert fragment.lower() in str(e).lower(), (fragment, str(e))
    else:
        raise AssertionError('Invalid archive/input was accepted')


with TemporaryDirectory() as directory:
    root = Path(directory)
    archives = root / 'archives'
    archives.mkdir()
    examples = [
        ('Ui/sample.darc', '.bclan', True),
        ('Obj/atlas.darc', '.bclim', True),
        ('Ui/layout.darc', '.bclyt', False),
        ('Message/dialogue.darc', '.msbt', True),
        ('Other/candidate.darc', '.bcres', False),
    ]
    for name, extension, dot in examples:
        path = archives / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(create_darc('asset' + extension, resource(extension), dot))
    report = audit(archives, expected_archives=5, expected_files=5)
    assert report['archive_count'] == report['file_count'] == 5
    assert report['3d_candidate_count'] == 1
    assert report['categories'] == {
        '3d_candidate_unverified': 1, 'image': 1, 'message': 1,
        'ui_animation': 1, 'ui_layout': 1,
    }
    assert report['3d_candidates'][0]['archive'] == 'Other/candidate.darc'
    assert report['private_asset_bytes_exported'] == 0
    assert report['archive_groups']['Ui']['archives'] == 2
    assert parse_darc((archives / 'Ui/sample.darc').read_bytes())[0]['path'] == 'asset.bclan'
    expect_error(lambda: audit(archives, expected_files=6), 'File count mismatch')
    expect_error(lambda: audit(archives, expected_archives=6), 'Archive count mismatch')
    zipped = root / 'private_darcs.zip'
    with zipfile.ZipFile(zipped, 'w', compression=zipfile.ZIP_DEFLATED) as z:
        for path in sorted(archives.rglob('*.darc')):
            z.write(path, path.relative_to(archives).as_posix())
        z.writestr('private_metadata.json', '{}')
    assert audit(zipped) == report

    # This tool produces metadata only, with no original extracted payloads.
    output = root / 'public_summary.json'
    output.write_text(json.dumps(report))
    assert output.read_text() == json.dumps(report)
    assert not (root / 'asset.bclan').exists()
    expect_error(lambda: safe_archive_name('../escape.darc'), 'Unsafe')
    expect_error(lambda: safe_archive_name('/absolute.darc'), 'Unsafe')
    expect_error(lambda: safe_archive_name('A\\model.darc'), 'Unsafe')
    expect_error(lambda: safe_archive_name('C:/model.darc'), 'Unsafe')

    for extension in ('.bclan', '.bclyt', '.msbt', '.bclim'):
        damaged = bytearray(resource(extension))
        damaged[0] = 0x58 if extension != '.bclim' else damaged[0]
        if extension == '.bclim':
            damaged[-40] = 0x58
        expect_error(lambda: classify_item('asset'+extension, damaged), 'Invalid')

    dot = bytearray(create_darc('asset.bclan', resource('.bclan'), True))
    struct.pack_into('<I', dot, 28+12, 2)
    expect_error(lambda: parse_darc(dot), 'dot')
    dot = bytearray(create_darc('asset.bclan', resource('.bclan'), True))
    struct.pack_into('<I', dot, 28+12+4, 3)
    expect_error(lambda: parse_darc(dot), 'dot')

    missing = root / 'empty.zip'
    with zipfile.ZipFile(missing, 'w') as z:
        z.writestr('only.json', '{}')
    expect_error(lambda: audit(missing), 'no DARC')
    traversal = root / 'bad.zip'
    with zipfile.ZipFile(traversal, 'w') as z:
        z.writestr('../evil.darc', create_darc('asset.msbt', resource('.msbt')))
    expect_error(lambda: audit(traversal), 'Unsafe')
    duplicate = root / 'duplicate.zip'
    with zipfile.ZipFile(duplicate, 'w') as z:
        z.writestr('Ui/One.darc', create_darc('asset.msbt', resource('.msbt')))
        z.writestr('ui/one.DARC', create_darc('asset.msbt', resource('.msbt')))
    expect_error(lambda: audit(duplicate), 'Duplicate')
    bad_resource = archives / 'Ui/sample.darc'
    bad_resource.write_bytes(create_darc('asset.bclan', b'CLYT' + b'\x00'*16, True))
    expect_error(lambda: audit(archives), 'Invalid')
    bad_resource.write_bytes(b'bad')
    expect_error(lambda: audit(archives), 'size')

print('PASS: DARC UI animation vs skeletal classification, dot roots, ZIP safety')
