#!/usr/bin/env python3
"""Check all preconverted NitroFS assets match the DS bitmap loader contract."""
import pathlib
import struct

ROOT = pathlib.Path(__file__).resolve().parents[1] / 'nitrofs'
BITMAPS = ('title_top.raw', 'menu_top.raw', 'menu_bottom.raw',
           'game_top.raw', 'game_bottom.raw',
           'title_menu_bottom.raw','development_top.raw','title_original_top.raw',
           'radar_overview.raw','transfer_top.raw','transfer_bottom.raw')
SPRITES = ('logo.spr', 'cloud.spr', 'cloud_yellow.spr', 'reticle.spr',
           'orb.spr', 'shop.spr', 'icon.spr', 'burnet.spr',
           'upgrade_beam.spr', 'upgrade_energy.spr', 'upgrade_scope.spr',
           'support_0.spr', 'support_1.spr', 'support_2.spr',
           'radar_marker_pink.spr','radar_marker_dark.spr','radar_arrow.spr') + tuple(f'pokemon_{i:02d}.spr' for i in range(26)) + tuple(f'item_{i:02d}.spr' for i in range(23)) + ('radar_cloud_white.spr','radar_cloud_pink.spr')


def verify(root=ROOT):
    for name in BITMAPS:
        path = root / name
        data = path.read_bytes()
        assert len(data) == 256 * 192 * 2, f'Bad bitmap: {name}'
        # Full-screen backgrounds are opaque BGR555 framebuffers.
        pixels = struct.unpack(f'<{256 * 192}H', data)
        assert all(p & 0x8000 for p in pixels), f'Non-opaque background: {name}'
    for name in SPRITES:
        data = (root / name).read_bytes()
        assert len(data) >= 4, f'Missing sprite header: {name}'
        w, h = struct.unpack_from('<HH', data)
        assert 0 < w <= 256 and 0 < h <= 192, f'Bad sprite dimensions: {name}'
        assert len(data) == 4 + w * h * 2, f'Bad pixel data length: {name}'
        # Sprite converter reserves zero for transparent texels and sets
        # RGB555 bit 15 on all visible pixels. Reject malformed opacity
        # values that would disappear or render incorrectly on DS hardware.
        pixels = struct.unpack_from(f'<{w * h}H', data, 4)
        assert any(p & 0x8000 for p in pixels), f'Fully invisible sprite: {name}'
        assert all(p == 0 or p & 0x8000 for p in pixels), (
            f'Invalid RGB555 opacity bit: {name}'
        )
    return len(BITMAPS), len(SPRITES)


if __name__ == '__main__':
    bmps, sprs = verify()
    print(f'PASS: NitroFS asset sizes ({bmps} backgrounds and {sprs} sprites)')
