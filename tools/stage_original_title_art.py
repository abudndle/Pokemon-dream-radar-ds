#!/usr/bin/env python3
"""Stage privately extracted original 3DS title backdrops for DS/DSi.

The public repo does not contain the original title backdrop BCLIM images.
This tool accepts owner-supplied full-screen (opaque) BCLIM/PNG images, resizes
each *entire* source screen to 256x192, and writes a paired RGB555 runtime
override into the user's private SD/FAT folder. Pane/material compositing and
exact original title transitions are separate outstanding work.
"""
import argparse
import os
from pathlib import Path
import struct
import tempfile
from PIL import Image
from convert_bclim_spr import decode_bclim

ROOT = Path(__file__).resolve().parents[1]
TARGET_W, TARGET_H = 256, 192
SOURCE_SIZE = {"top": (400, 240), "bottom": (320, 240)}

def load_original(path, screen):
    if not path.is_file() or path.stat().st_size > 16 * 1024 * 1024:
        raise ValueError(f"{screen}: missing or oversized source")
    if path.suffix.lower() == ".bclim":
        w, h, rgba = decode_bclim(path.read_bytes())
        image = Image.frombytes("RGBA", (w, h), rgba)
    elif path.suffix.lower() in (".png", ".bmp"):
        with Image.open(path) as imported:
            if imported.format not in ("PNG", "BMP"):
                raise ValueError("unsupported image encoding")
            image = imported.convert("RGBA")
    else:
        raise ValueError("source must be original extracted BCLIM, PNG, or BMP")
    if image.size != SOURCE_SIZE[screen]:
        raise ValueError(f"{screen} must use original screen size {SOURCE_SIZE[screen]}, got {image.size}")
    if image.getchannel("A").getextrema() != (255, 255):
        raise ValueError("transparent/partial textures need original BCLYT material compositing")
    return image.convert("RGB")

def encode_raw(image):
    scaled = image.resize((TARGET_W, TARGET_H), Image.Resampling.LANCZOS)
    out = bytearray()
    for r, g, b in scaled.getdata():
        value = 0x8000 | (r >> 3) | ((g >> 3) << 5) | ((b >> 3) << 10)
        out.extend(struct.pack("<H", value))
    if len(out) != TARGET_W * TARGET_H * 2:
        raise ValueError("unexpected title raw length")
    return bytes(out)

def stage(top, bottom, root):
    root = root.resolve()
    if root == ROOT.resolve() or ROOT.resolve() in root.parents:
        raise ValueError("do not write user-owned original Nintendo art into a public repo")
    paths = [Path(top).resolve(), Path(bottom).resolve()]
    if paths[0] == paths[1]:
        raise ValueError("top and bottom must be distinct original screens")
    payload = [encode_raw(load_original(paths[i], screen))
               for i, screen in enumerate(("top", "bottom"))]
    out = root / "DreamRadarDSi" / "UI"
    out.mkdir(parents=True, exist_ok=True)
    staged = []
    try:
        for filename, data in zip(("title_top.raw", "title_bottom.raw"), payload):
            with tempfile.NamedTemporaryFile(prefix=".drtitle-", suffix=".tmp",
                                             dir=out, delete=False) as tmp:
                tmp.write(data)
                staged.append((Path(tmp.name), out / filename))
        for temp, final in staged:
            os.replace(temp, final)
    finally:
        for temp, _ in staged:
            temp.unlink(missing_ok=True)
    return out

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--top", type=Path, required=True,
                   help="owner-extracted 400x240 3DS top background")
    p.add_argument("--bottom", type=Path, required=True,
                   help="owner-extracted 320x240 3DS bottom background")
    p.add_argument("--output-root", type=Path, required=True,
                   help="private SD/FAT volume root (never this public repo)")
    args = p.parse_args()
    out = stage(args.top, args.bottom, args.output_root)
    print(f"Staged private title backgrounds in {out}; no original files committed")

if __name__ == "__main__":
    main()
