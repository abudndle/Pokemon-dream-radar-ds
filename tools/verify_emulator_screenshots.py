#!/usr/bin/env python3
"""Validate actual emulator screenshots and record conservative smoke-test proof.

Only screens captured from a live emulator window may be submitted by the
Linux workflow; this tool cannot prove game controls, save integrity, or FPS.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def inspect_image(path: Path):
    if not path.is_file() or path.stat().st_size < 64:
        raise ValueError(f"Empty or missing emulator screenshot: {path}")
    raw = path.read_bytes()
    if raw[:8] != PNG_SIGNATURE or raw[12:16] != b'IHDR':
        raise ValueError(f"Expected real PNG file: {path}")
    width, height = struct.unpack_from(">II", raw, 16)
    if width < 240 or height < 360 or width > 2000 or height > 2000:
        raise ValueError(f"Screenshot is not a plausible dual-screen DS display: {width}x{height}")
    # ImageMagick reports actual decoded pixel statistics; a PNG header
    # alone is not sufficient to establish that the emulator drew anything.
    command = ['identify', '-format', '%k|%[fx:mean]', str(path)]
    p = subprocess.run(command, capture_output=True, text=True, check=True, timeout=12)
    values = p.stdout.strip().split('|')
    if len(values) != 2:
        raise ValueError(f"Could not read screenshot pixel statistics: {path}")
    colors = int(values[0])
    mean = float(values[1])
    if colors < 12 or not 0.012 <= mean <= 0.985:
        raise ValueError(f"Emulator capture is blank/uninformative: colors={colors} mean={mean:.5f}")
    return {
        'filename': path.name,
        'width': width, 'height': height,
        'distinct_colors': colors,
        'average_luminance': round(mean, 6),
        'sha256': hashlib.sha256(raw).hexdigest(),
        'bytes': len(raw),
    }


def verify(paths):
    if len(paths) < 2:
        raise ValueError('At least two live emulator capture stages are required')
    results = [inspect_image(Path(p)) for p in paths]
    if len({entry['width'] for entry in results}) != 1 or len(
        {entry['height'] for entry in results}) != 1:
        raise ValueError('Emulator screen dimensions unexpectedly changed')
    return {
        'kind': 'real-linux-desmume-emulator-screenshots',
        'verified': 'nonblank_dual_screen_window_captures',
        'emulator': 'DeSmuME CLI / SDL under Xvfb',
        'count': len(results),
        'captures': results,
        'distinct_frame_hashes': len({entry['sha256'] for entry in results}),
        'input_attempts': ['Return / DS Start', 'Return / DS Start from intro',
                           'Z / DS B', 'X / DS A'],
        'limitations': [
            'Live window and nonblank pixel validation are not a gameplay or performance test',
            'Input events were attempted but transition success must be visually reviewed',
            'DSi-only camera, SD, and hardware features remain unverified',
        ],
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', required=True, type=Path)
    p.add_argument('screenshots', nargs='+', type=Path)
    args = p.parse_args()
    report = verify(args.screenshots)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(f"PASS: {report['count']} actual nonblank DeSmuME screenshot captures "
          f"({report['distinct_frame_hashes']} distinct pixel hashes).")
    if report['distinct_frame_hashes'] < 2:
        print('WARNING: emulator captures did not change; gameplay progress NOT confirmed')


if __name__ == '__main__':
    main()
