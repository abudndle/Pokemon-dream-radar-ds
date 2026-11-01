#!/usr/bin/env python3
"""Batch staging must not leave partial results when one model is invalid."""
import json
import hashlib
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
sys.path.insert(0,str(ROOT/'tests'))
from test_gltf_skin_converter import make_fixture
from stage_gltf_animations import stage

with tempfile.TemporaryDirectory() as temporary:
    root=pathlib.Path(temporary)
    gltf=root/'gltf';gltf.mkdir()
    mesh=root/'meshes';mesh.mkdir()
    staged=root/'staged'
    document,buffer,geometry=make_fixture()
    for species in ('00','25'):
        (gltf/f'pokemon_{species}.gltf').write_text(json.dumps(document),encoding='utf-8')
        (mesh/f'pokemon_{species}.drm').write_bytes(geometry)
    (gltf/'pokemon_26.gltf').write_text('invalid deliberately')
    report=stage(gltf,mesh,staged)
    assert len(report['models'])==2
    assert [row['file'] for row in report['models']]==['pokemon_00.drk','pokemon_25.drk']
    assert (staged/'pokemon_00.drk').read_bytes()[:4]==b'DRK1'
    assert (staged/'pokemon_25.drk').read_bytes()[:4]==b'DRK1'
    assert not (staged/'pokemon_26.drk').exists()
    assert not report['verified_original_3ds_animation']
    for row in report['models']:
        payload=(staged/row['file']).read_bytes()
        assert row['bytes']==len(payload)
        assert row['sha256']==hashlib.sha256(payload).hexdigest()
    assert json.loads((staged/'gltf_animation_manifest.json').read_text())==report
    saved_files={p.name:p.read_bytes() for p in staged.iterdir()}
    saved=(staged/'pokemon_00.drk').read_bytes()
    (gltf/'pokemon_25.gltf').write_text('{"invalid": true}')
    try:stage(gltf,mesh,staged)
    except ValueError:pass
    else:raise AssertionError('Bad batch was accepted')
    assert saved==(staged/'pokemon_00.drk').read_bytes()
    assert saved==(staged/'pokemon_25.drk').read_bytes()
    assert saved_files=={p.name:p.read_bytes() for p in staged.iterdir()}
    (gltf/'pokemon_00.gltf').unlink()
    (gltf/'pokemon_25.gltf').unlink()
    try:stage(gltf,mesh,staged)
    except ValueError:pass
    else:raise AssertionError('Empty model batch accepted')
    print('PASS: staged private glTF animation batch and all-before-write safety')
