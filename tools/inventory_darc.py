#!/usr/bin/env python3
"""Inventory Nintendo DARC files decoded from privately held Dream Radar CARCs.

Default operation writes only filename and metadata JSON. --extract-dir writes
original game payloads to a private local folder; never publish those files.
"""
import argparse
import json
import struct
from collections import Counter
from pathlib import Path


class DarcError(ValueError):
    pass


def read_name(data, start, limit):
    if start % 2 or start < 0 or start + 2 > limit:
        raise DarcError('invalid UTF-16 name offset')
    end = start
    while end + 2 <= limit:
        if data[end:end + 2] == b'\x00\x00':
            try:
                name = data[start:end].decode('utf-16le', errors='strict')
            except UnicodeDecodeError as exc:
                raise DarcError('invalid UTF-16 name') from exc
            if any(ord(c) < 32 for c in name) or '\\' in name or '/' in name:
                raise DarcError('unsafe archive path component')
            return name
        end += 2
    raise DarcError('unterminated archive name')


def parse_darc(data):
    """Validate a DARC directory tree and return file offsets and sizes."""
    if len(data) < 40 or data[:4] != b'darc':
        raise DarcError('missing DARC header')
    magic, bom, header_len, version, total, table_off, table_size, data_off = \
        struct.unpack_from('<4sHHIIIII', data)
    if bom != 0xfeff or header_len != 28 or version != 0x01000000:
        raise DarcError('unsupported DARC header')
    if total != len(data) or not (28 <= table_off <= len(data)) or table_size < 12:
        raise DarcError('invalid DARC size or file table')
    if table_off + table_size > data_off or data_off > len(data):
        raise DarcError('overlapping DARC metadata and data')
    root_name, root_parent, count = struct.unpack_from('<III', data, table_off)
    if root_name != 0x01000000 or root_parent != 0 or count < 1 or count > table_size // 12:
        raise DarcError('invalid root directory')
    names = table_off + count * 12
    limit = table_off + table_size
    if names + 2 > limit or read_name(data, names, limit) != '':
        raise DarcError('missing root name')
    out = []
    seen = set()
    stack = [(count, 0, '')]
    for index in range(1, count):
        while len(stack) > 1 and index >= stack[-1][0]:
            stack.pop()
        parent_path = stack[-1][2]
        raw_name, val, size = struct.unpack_from('<III', data, table_off + index * 12)
        if raw_name & 0xfe000000:
            raise DarcError('unknown DARC entry flags')
        is_dir = bool(raw_name & 0x01000000)
        name = read_name(data, names + (raw_name & 0x00ffffff), limit)
        if not name or name in ('.', '..'):
            raise DarcError('invalid DARC path component')
        path = (parent_path + '/' + name).lstrip('/')
        if is_dir:
            if val != stack[-1][1] or size <= index or size > stack[-1][0]:
                raise DarcError('invalid DARC folder range or parent')
            stack.append((size, index, path))
            continue
        if size > len(data) or val < data_off or val > len(data) - size:
            raise DarcError('file payload outside DARC')
        if path in seen:
            raise DarcError('duplicate DARC filename')
        seen.add(path)
        out.append({'path': path, 'size': size, 'offset': val})
    return out


def inspect_bclim(data):
    """Validate original BCLIM metadata without assuming a pixel decoder."""
    if len(data) < 40:
        raise DarcError('truncated BCLIM image')
    magic, bom, hdr_len, version, file_size, blocks, section, sec_len, width, height, fmt, pixel_size = \
        struct.unpack_from('<4sHHIII4sIHHII', data, len(data) - 40)
    if (magic != b'CLIM' or bom != 0xfeff or hdr_len != 20 or
        file_size != len(data) or blocks != 1 or section != b'imag' or
        sec_len != 16 or pixel_size != len(data) - 40 or not width or not height):
        raise DarcError('invalid BCLIM image footer')
    return {'width': width, 'height': height, 'format_code': fmt,
            'image_bytes': pixel_size, 'version': version}


def inspect_tree(root, output, extract_dir=None):
    root = Path(root)
    if not root.is_dir():
        raise DarcError('DARC source directory does not exist')
    report = {'format': 'DARC', 'archives': [], 'file_count': 0, 'total_file_bytes': 0}
    kinds = Counter()
    archives = sorted(p for p in root.rglob('*.darc') if p.is_file())
    if not archives:
        raise DarcError('No DARC files found')
    prepared = []
    dest_seen = set()
    # Validate the whole collection before writing any original payload bytes.
    for archive in archives:
        archive_rel = archive.relative_to(root)
        data = archive.read_bytes()
        files = parse_darc(data)
        local = []
        for item in files:
            rel = archive_rel.with_suffix('') / item['path']
            if rel.as_posix() in dest_seen:
                raise DarcError('duplicate extraction path')
            dest_seen.add(rel.as_posix())
            kind = rel.suffix.lower() or '(none)'
            kinds[kind] += 1
            meta = {'path': rel.as_posix(), 'size': item['size'],
                    'offset': item['offset']}
            if kind == '.bclim':
                meta['image'] = inspect_bclim(
                    data[item['offset']:item['offset'] + item['size']])
            local.append(meta)
            report['total_file_bytes'] += item['size']
        report['archives'].append({'archive': archive_rel.as_posix(), 'files': local,
                                   'file_count': len(local)})
        report['file_count'] += len(local)
        prepared.append((data, local))
    report['archive_count'] = len(archives)
    report['extensions'] = dict(sorted(kinds.items()))
    if extract_dir is not None:
        dest = Path(extract_dir).resolve()
        dest.mkdir(parents=True, exist_ok=True)
        for data, files in prepared:
            for entry in files:
                target = (dest / entry['path']).resolve()
                if dest not in target.parents:
                    raise DarcError('unsafe extraction path')
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data[entry['offset']:entry['offset'] + entry['size']])
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('darc_directory', type=Path)
    parser.add_argument('report_json', type=Path)
    parser.add_argument('--extract-dir', type=Path,
                        help='private local destination for original assets')
    args = parser.parse_args()
    result = inspect_tree(args.darc_directory, args.report_json, args.extract_dir)
    print(f"Validated {result['archive_count']} DARC containers with "
          f"{result['file_count']} embedded files")


if __name__ == '__main__':
    main()
