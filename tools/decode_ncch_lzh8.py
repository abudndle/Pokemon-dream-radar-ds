#!/usr/bin/env python3
"""Decode privately owned Dream Radar NCCH RomFS CARC files (Nintendo LZH8).

Default output is a metadata-only JSON report. --extract-dir exports original
DARC bytes only to a path selected by the user; never run it on public CI.
The 0x40 files contain a 9-bit literal/match Huffman tree followed by a 5-bit
backreference-displacement-length Huffman tree.
"""
import argparse
import json
import struct
from pathlib import Path
from inventory_ncch_romfs import audit

MAX_OUTPUT = 16 * 1024 * 1024

class Lzh8Error(ValueError):
    pass

class BitReader:
    def __init__(self, data, bitpos=0):
        self.data = data
        self.bitpos = bitpos

    def read(self, count):
        if count < 0 or count > 16 or self.bitpos + count > len(self.data) * 8:
            raise Lzh8Error('truncated or invalid bit read')
        value = 0
        for bit_index in range(self.bitpos, self.bitpos + count):
            value = (value << 1) | ((self.data[bit_index // 8] >> (7 - bit_index % 8)) & 1)
        self.bitpos += count
        return value


def _tree_values(data, start, table_bytes, prefix_size, width):
    if table_bytes < prefix_size or start + table_bytes > len(data):
        raise Lzh8Error('truncated Huffman tree')
    reader = BitReader(data, (start + prefix_size) * 8)
    values = [0]
    for _ in range((table_bytes - prefix_size) * 8 // width):
        values.append(reader.read(width))
    return values


def _symbol(tree, reader, leaf_bit, payload_mask):
    index = 1
    for _ in range(1024):
        if index <= 0 or index >= len(tree):
            raise Lzh8Error('invalid Huffman tree index')
        child = reader.read(1)
        node = tree[index]
        next_index = (index // 2 * 2) + ((node & payload_mask) + 1) * 2 + child
        if next_index >= len(tree) or next_index == index:
            raise Lzh8Error('invalid Huffman branch')
        if node & (leaf_bit >> child):
            return tree[next_index]
        index = next_index
    raise Lzh8Error('Huffman tree depth exceeded')


def decompress_lzh8(data, max_output=MAX_OUTPUT):
    """Return precisely sized LZH8 bytes or fail (never accept partial output)."""
    if len(data) < 8 or data[0] != 0x40:
        raise Lzh8Error('missing LZH8 header')
    expected = int.from_bytes(data[1:4], 'little')
    cursor = 4
    if expected == 0:
        if len(data) < 8:
            raise Lzh8Error('truncated extended size')
        expected = int.from_bytes(data[4:8], 'little')
        cursor = 8
    if expected <= 0 or expected > max_output:
        raise Lzh8Error('uncompressed size outside allowed limit')
    if cursor + 2 > len(data):
        raise Lzh8Error('missing first tree header')
    table_size = (int.from_bytes(data[cursor:cursor + 2], 'little') + 1) * 4
    lengths = _tree_values(data, cursor, table_size, 2, 9)
    cursor += table_size
    if cursor >= len(data):
        raise Lzh8Error('missing displacement tree')
    disp_size = (data[cursor] + 1) * 4
    displacements = _tree_values(data, cursor, disp_size, 1, 5)
    cursor += disp_size
    bits = BitReader(data, cursor * 8)
    result = bytearray()
    while len(result) < expected:
        code = _symbol(lengths, bits, 0x100, 0x7F)
        if code < 256:
            result.append(code)
            continue
        copy_len = (code & 255) + 3
        distance_bits = _symbol(displacements, bits, 0x10, 0x07)
        if distance_bits > 16:
            raise Lzh8Error('invalid displacement bit length')
        distance = (1 << (distance_bits - 1)) | bits.read(distance_bits - 1) if distance_bits else 0
        distance += 1
        if distance > len(result):
            raise Lzh8Error('backreference before output start')
        if copy_len > expected - len(result):
            raise Lzh8Error('backreference exceeds declared output')
        # For copy_len == distance, slicing with a zero end index produces an
        # EMPTY slice in Python. Handle it with the overlapping-copy path.
        if copy_len < distance:
            result.extend(result[-distance:-distance + copy_len])
        else:
            for _ in range(copy_len):
                result.append(result[-distance])
    return bytes(result)


def inspect_ncch(path, extract_dir=None):
    image = Path(path).read_bytes()
    if len(image) < 0x200:
        raise Lzh8Error('NCCH image is too small')
    romfs_start = struct.unpack_from('<I', image, 0x1B0)[0] * 512
    summary = {'compression': 'LZH8', 'archives': [], 'total_decoded_bytes': 0}
    for item in audit(path)['files']:
        if not item['path'].lower().endswith('.carc'):
            continue
        offset = romfs_start + item['romfs_offset']
        end = offset + item['size']
        if offset < romfs_start or end > len(image):
            raise Lzh8Error(f'archive outside NCCH: {item["path"]}')
        unpacked = decompress_lzh8(image[offset:end])
        if unpacked[:4] != b'darc' or len(unpacked) < 28:
            raise Lzh8Error(f'unexpected decoded container: {item["path"]}')
        declared = int.from_bytes(unpacked[12:16], 'little')
        if declared != len(unpacked):
            raise Lzh8Error(f'DARC length mismatch: {item["path"]}')
        summary['archives'].append({'path': item['path'], 'compressed_bytes': item['size'],
                                    'decoded_bytes': len(unpacked), 'container': 'DARC'})
        summary['total_decoded_bytes'] += len(unpacked)
        if extract_dir is not None:
            target = Path(extract_dir).joinpath(item['path'].lstrip('/')).with_suffix('.darc')
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(unpacked)
    summary['archive_count'] = len(summary['archives'])
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('ncch', type=Path)
    parser.add_argument('report_json', type=Path)
    parser.add_argument('--extract-dir', type=Path,
                        help='optional LOCAL-ONLY directory for original DARC bytes')
    args = parser.parse_args()
    result = inspect_ncch(args.ncch, args.extract_dir)
    args.report_json.parent.mkdir(parents=True, exist_ok=True)
    args.report_json.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(f"Verified {result['archive_count']} LZH8-DARC files "+
          f"({result['total_decoded_bytes']} original decoded bytes)")

if __name__ == '__main__':
    main()
