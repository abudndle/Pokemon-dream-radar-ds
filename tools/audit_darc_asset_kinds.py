#!/usr/bin/env python3
"""Read-only classification of *private* decoded Dream Radar DARC collections.

Accepts a folder of .darc files or a ZIP of decoded .darc files. Verifies each
DARC directory and embedded format header/footer but exports metadata ONLY,
never copyrighted payloads. No CLAN (UI animation) is counted as a 3D rig.
"""
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import stat
import zipfile

from inventory_darc import DarcError, inspect_bclim, parse_darc

MAX_ARCHIVES = 4096
MAX_ARCHIVE_BYTES = 32 * 1024 * 1024
MAX_COLLECTION_BYTES = 256 * 1024 * 1024

# Extensions are *candidates*, never proof of geometry, animation or encoding.
MODEL_EXTENSIONS = frozenset({
    '.bcmdl', '.bcres', '.bch', '.cmb', '.cgfx', '.bcskl', '.csab',
    '.canm', '.bck', '.bca', '.bcsk', '.cmdl',
})
MODEL_MAGICS = {b'CGFX': 'CGFX', b'BCH\x00': 'BCH',
                b'CSAB': 'CSAB', b'CANM': 'CANM', b'CMB\x00': 'CMB'}
KNOWN_RESOURCES = {'.bclan': (b'CLAN', 'ui_animation'),
                   '.bclyt': (b'CLYT', 'ui_layout'),
                   '.msbt': (b'MsgS', 'message')}


def safe_archive_name(name):
    if (not isinstance(name, str) or not name or name.startswith('/') or
            '\\' in name or ':' in name or any(ord(ch) < 32 for ch in name) or
            any(part in ('', '.', '..') for part in name.split('/'))):
        raise DarcError('Unsafe DARC archive path')
    return name


def source_archives(source):
    """Yield validated (relative name, DARC bytes) without writing payloads."""
    source = Path(source)
    if source.is_file() and source.suffix.lower() == '.zip':
        if source.stat().st_size > MAX_COLLECTION_BYTES:
            raise DarcError('DARC ZIP exceeds compressed size budget')
        with zipfile.ZipFile(source) as archive:
            members = []
            seen = set()
            total = 0
            for entry in archive.infolist():
                if entry.is_dir() or not entry.filename.lower().endswith('.darc'):
                    continue
                name = safe_archive_name(entry.filename)
                if name.casefold() in seen:
                    raise DarcError('Duplicate DARC archive name')
                seen.add(name.casefold())
                unix_mode = entry.external_attr >> 16
                if stat.S_ISLNK(unix_mode):
                    raise DarcError('DARC ZIP contains a symbolic link')
                if entry.flag_bits & 1:
                    raise DarcError('Encrypted DARC ZIP entry unsupported')
                if entry.file_size > MAX_ARCHIVE_BYTES or entry.file_size < 40:
                    raise DarcError('DARC member exceeds size constraints')
                total += entry.file_size
                if total > MAX_COLLECTION_BYTES or len(seen) > MAX_ARCHIVES:
                    raise DarcError('DARC collection exceeds budget')
                members.append(entry)
            if not members:
                raise DarcError('ZIP contains no DARC files')
            for entry in sorted(members, key=lambda x: x.filename):
                blob = archive.read(entry)
                if len(blob) != entry.file_size:
                    raise DarcError('DARC ZIP entry size mismatch')
                yield entry.filename, blob
    elif source.is_dir():
        matches = sorted(p for p in source.rglob('*') if p.suffix.lower() == '.darc')
        if not matches or len(matches) > MAX_ARCHIVES:
            raise DarcError('DARC folder empty or over archive count budget')
        total = 0
        for path in matches:
            if path.is_symlink() or not path.is_file():
                raise DarcError('DARC folder contains unsupported non-file or link')
            name = safe_archive_name(path.relative_to(source).as_posix())
            size = path.stat().st_size
            if size < 40 or size > MAX_ARCHIVE_BYTES:
                raise DarcError('DARC exceeds size budget')
            total += size
            if total > MAX_COLLECTION_BYTES:
                raise DarcError('DARC collection exceeds budget')
            yield name, path.read_bytes()
    else:
        raise DarcError('Expected a DARC ZIP file or decoded DARC folder')


def classify_item(name, data):
    extension = Path(name).suffix.lower()
    if extension == '.bclim':
        inspect_bclim(data)  # CLIM footer: pixel data is not prefixed by magic.
        return 'image', 'CLIM_footer', False
    if extension in KNOWN_RESOURCES:
        signature, kind = KNOWN_RESOURCES[extension]
        valid_header = (len(data) >= 20 and data[:4] == signature and
                        ((extension == '.msbt' and data[:8] == b'MsgStdBn' and
                          data[8:10] == b'\xff\xfe') or
                         (extension != '.msbt' and data[4:6] == b'\xff\xfe')))
        if not valid_header:
            raise DarcError(f'Invalid {extension} resource header')
        return kind, signature.decode('ascii'), False
    signature = MODEL_MAGICS.get(data[:4])
    if extension in MODEL_EXTENSIONS or signature is not None:
        return '3d_candidate_unverified', signature or 'extension_only', True
    return 'other_unclassified', data[:4].hex() if len(data) >= 4 else 'short', False


def audit(source, expected_archives=None, expected_files=None):
    kinds = Counter()
    extensions = Counter()
    signatures = Counter()
    groups = defaultdict(lambda: {'archives': 0, 'files': 0, 'categories': Counter()})
    archive_count = file_count = 0
    candidates = []
    for name, blob in source_archives(source):
        archive_count += 1
        files = parse_darc(blob)
        group = name.partition('/')[0] if '/' in name else '(root)'
        groups[group]['archives'] += 1
        for item in files:
            begin, count = item['offset'], item['size']
            if begin < 0 or count < 0 or begin + count > len(blob):
                raise DarcError('DARC item outside validated archive')
            payload = memoryview(blob)[begin:begin + count]
            kind, magic, candidate = classify_item(item['path'], payload)
            kinds[kind] += 1
            extensions[Path(item['path']).suffix.lower() or '(none)'] += 1
            signatures[magic] += 1
            groups[group]['files'] += 1
            groups[group]['categories'][kind] += 1
            file_count += 1
            if candidate:
                candidates.append({'archive': name, 'member': item['path'],
                                   'kind': magic, 'bytes': count,
                                   'status': 'candidate_only_not_decoded'})
    if expected_archives is not None and archive_count != expected_archives:
        raise DarcError(f'Archive count mismatch: {archive_count} != {expected_archives}')
    if expected_files is not None and file_count != expected_files:
        raise DarcError(f'File count mismatch: {file_count} != {expected_files}')
    return {
        'format': 'DARC_ASSET_KIND_AUDIT_V1',
        'archive_count': archive_count,
        'file_count': file_count,
        'categories': dict(sorted(kinds.items())),
        'extensions': dict(sorted(extensions.items())),
        'validated_signatures': dict(sorted(signatures.items())),
        'archive_groups': {key: {'archives': val['archives'], 'files': val['files'],
                                 'categories': dict(sorted(val['categories'].items()))}
                           for key, val in sorted(groups.items())},
        '3d_candidate_count': len(candidates),
        '3d_candidates': candidates,
        'caveat': ('Only recognized top-level DARC member formats were checked. '
                   'Zero 3D candidates here does not prove that the original game '
                   'contains no 3D models or skeletal animation elsewhere, '
                   'including other RomFS or executable sections.'),
        'private_asset_bytes_exported': 0,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path, help='Private ZIP of decoded DARC archives or their directory')
    parser.add_argument('report', type=Path, help='Metadata-only JSON report output')
    parser.add_argument('--expect-archives', type=int)
    parser.add_argument('--expect-files', type=int)
    args = parser.parse_args()
    result = audit(args.source, args.expect_archives, args.expect_files)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    print(f"Validated {result['archive_count']} DARC archives, "
          f"{result['file_count']} files, "
          f"{result['3d_candidate_count']} unverified 3D candidates. "
          'UI BCLAN is not skeletal animation.')


if __name__ == '__main__':
    main()
