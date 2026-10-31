#!/usr/bin/env python3
"""Batch-validate user-owned pokemon_00..25 glTF exports before staging DRK1.

All conversions are checked before any output is published, so a broken pair
cannot silently leave only part of a newly converted set.
"""
import argparse
import json
import re
from pathlib import Path
from convert_gltf_skin import convert, load_document

FILENAME = re.compile(r'pokemon_(0[0-9]|1[0-9]|2[0-5])\.gltf\Z')


def stage(gltf_dir: Path, mesh_dir: Path, out_dir: Path, *, frames=4, ticks=8, animation=0):
    if not gltf_dir.is_dir() or not mesh_dir.is_dir():
        raise ValueError('Expected existing private glTF and DRM1 directories')
    candidates = sorted(path for path in gltf_dir.iterdir()
                        if path.is_file() and not path.is_symlink() and
                        FILENAME.fullmatch(path.name))
    if not candidates:
        raise ValueError('No pokemon_00.gltf ... pokemon_25.gltf exports found')
    converted = []
    for path in candidates:
        mesh = mesh_dir / (path.stem + '.drm')
        if not mesh.is_file() or mesh.is_symlink():
            raise ValueError(f'No matching DRM1 mesh for {path.name}')
        doc, buffers = load_document(path)
        result, info = convert(doc, buffers, mesh.read_bytes(),
                               frames=frames, ticks=ticks, animation_index=animation)
        converted.append((path.stem, result, info))
    out_dir.mkdir(parents=True, exist_ok=True)
    report = {'format': 'DRK1', 'source': 'private_gltf_export',
              'verified_original_3ds_animation': False, 'models': []}
    for stem, data, info in converted:
        filename = stem + '.drk'
        (out_dir / filename).write_bytes(data)
        report['models'].append({'file':filename,'vertices':info['vertices'],
                                 'bones':info['bones'],'frames':info['frames'],
                                 'bytes':len(data)})
    (out_dir / 'gltf_animation_manifest.json').write_text(
        json.dumps(report, indent=2) + '\n', encoding='utf-8')
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('gltf_dir',type=Path)
    parser.add_argument('mesh_dir',type=Path)
    parser.add_argument('out_dir',type=Path)
    parser.add_argument('--frames',type=int,default=4)
    parser.add_argument('--ticks',type=int,default=8)
    parser.add_argument('--animation',type=int,default=0)
    args=parser.parse_args()
    report=stage(args.gltf_dir,args.mesh_dir,args.out_dir,
                 frames=args.frames,ticks=args.ticks,animation=args.animation)
    print('Converted',len(report['models']),'private models to DRK1; '
          'not verified from original 3DS animations')


if __name__=='__main__':main()
