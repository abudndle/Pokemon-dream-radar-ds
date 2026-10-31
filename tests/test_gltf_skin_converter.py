#!/usr/bin/env python3
"""Synthetic glTF 2.0 fixtures for strict glTF -> DRK1 conversion."""
import base64
import copy
import json
import math
import pathlib
import struct
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from convert_gltf_skin import load_document, convert, convert_paths


def make_fixture(*, external=False):
    vertices=[(0,0,0),(1,0,0),(0,1,0),
              (1,0,0),(2,0,0),(1,1,0)]
    indices=[0,1,2,3,4,5]
    drm=bytearray(struct.pack('<4sHH',b'DRM1',6,2))
    for p in vertices:drm.extend(struct.pack('<hhh',*(round(x*4096) for x in p)))
    for j in indices:drm.extend(struct.pack('<H',j))
    data=bytearray()
    views=[];access=[]
    def append(value,kind,component,count):
        nonlocal data
        while len(data)%4:data.append(0)
        off=len(data);data.extend(value)
        views.append({'buffer':0,'byteOffset':off,'byteLength':len(value)})
        access.append({'bufferView':len(views)-1,'componentType':component,
                       'count':count,'type':kind})
        return len(access)-1
    pos=append(b''.join(struct.pack('<fff',*p) for p in vertices),'VEC3',5126,6)
    joints=append(b''.join(struct.pack('<BBBB',*( (0,0,0,0) if i<3 else (1,0,0,0))) for i in range(6)),'VEC4',5121,6)
    weights=append(b''.join(struct.pack('<ffff',*((1,0,0,0) if i<5 else (.5,.5,0,0))) for i in range(6)),'VEC4',5126,6)
    ix=append(struct.pack('<6H',*indices),'SCALAR',5123,6)
    identity=lambda x:[1,0,0,0,0,1,0,0,0,0,1,0,-x,0,0,1]
    bind=append(struct.pack('<32f',*(identity(0)+identity(1))),'MAT4',5126,2)
    times=append(struct.pack('<3f',0,.5,1),'SCALAR',5126,3)
    rotations=append(b''.join(struct.pack('<ffff',0,math.sin(a/2),0,math.cos(a/2))
                              for a in (0,math.pi/2,0)),'VEC4',5126,3)
    translations=append(b''.join(struct.pack('<fff',*p) for p in
                                 ((1,0,0),(1,0.25,0),(1,0,0))), 'VEC3',5126,3)
    doc={'asset':{'version':'2.0'},'buffers':[{'byteLength':len(data),'uri':
           'model.bin' if external else 'data:application/octet-stream;base64,'+base64.b64encode(data).decode()}],
         'bufferViews':views,'accessors':access,
         'nodes':[{'mesh':0,'skin':0},{'children':[2]},
                  {'translation':[1,0,0]}],
         'meshes':[{'primitives':[{'mode':4,'indices':ix,'attributes':{
               'POSITION':pos,'JOINTS_0':joints,'WEIGHTS_0':weights}}]}],
         'skins':[{'joints':[2,1],'inverseBindMatrices':bind}],
         'animations':[{'samplers':[
             {'input':times,'output':rotations,'interpolation':'LINEAR'},
             {'input':times,'output':translations,'interpolation':'LINEAR'}],
             'channels':[{'sampler':0,'target':{'node':2,'path':'rotation'}},
                         {'sampler':1,'target':{'node':2,'path':'translation'}}]}]}
    block=bytearray(data)
    offset=views[access[joints]['bufferView']]['byteOffset']
    for i in range(6):
        block[offset+4*i:offset+4*i+4]=bytes([1,0,0,0] if i<3 else [0,1,0,0])
    offset=views[access[bind]['bufferView']]['byteOffset']
    block[offset:offset+128]=struct.pack('<32f',*(identity(1)+identity(0)))
    doc['buffers'][0]['uri']=('model.bin' if external else
        'data:application/octet-stream;base64,'+base64.b64encode(block).decode())
    return doc,bytes(block),bytes(drm)


def reject(doc,blobs,drm,needle=None):
    try:convert(doc,blobs,drm)
    except ValueError as error:
        if needle:assert needle in str(error),(needle,str(error))
    else:raise AssertionError('Malformed export was accepted')


def test():
    d,blob,drm=make_fixture()
    drk,report=convert(d,[blob],drm)
    assert drk[:10]==b'DRK1\x06\x00\x02\x04\x08\x00'
    assert len(drk)==10+2*8+6*3+4*2*4
    assert drk[16]==255 and drk[24]==0
    assert drk[26:29]==bytes([0,0,255])
    assert drk[35:38]==bytes([1,1,255])
    assert report['bones']==2 and not report['verified_original_3ds_animation']
    assert drk[60:64]==bytes([0,0,0,0])
    assert drk[64:68]==bytes([0,64,0,64])
    assert drk[56:60]==bytes([0,32,0,32])
    assert len(drk)==76
    assert convert(d,[blob],drm)[0]==drk
    assert convert(d,[blob],drm,frames=2,ticks=15)[1]['frames']==2
    assert convert(d,[blob],drm,frames=8,ticks=4)[1]['frames']==8
    reject(d,[blob],drm[:-1],'invalid size')
    bad=bytearray(drm);bad[8]=8
    reject(d,[blob],bytes(bad),'position mismatch')
    changed=copy.deepcopy(d);changed['meshes'][0]['primitives'][0]['attributes']['POSITION']=999
    reject(changed,[blob],drm,'accessor')
    changed=copy.deepcopy(d);changed['meshes'][0]['primitives'][0]['mode']=5
    reject(changed,[blob],drm,'nontriangle')
    changed=copy.deepcopy(d);changed['nodes'][2]['scale']=[2,1,1]
    reject(changed,[blob],drm,'scale')
    changed=copy.deepcopy(d);changed['nodes'][1]['children']=[2];changed['nodes'][2]['children']=[1]
    reject(changed,[blob],drm,'Cyclic')
    changed=copy.deepcopy(d);changed['skins'][0]['joints']=[1,2,2]
    reject(changed,[blob],drm,'joint list')
    changed=copy.deepcopy(d);changed['animations'][0]['samplers'][0]['interpolation']='CUBICSPLINE'
    reject(changed,[blob],drm,'CUBICSPLINE')
    changed=copy.deepcopy(d);changed['animations'][0]['channels'][0]['target']['path']='scale'
    reject(changed,[blob],drm,'channels')
    changed=copy.deepcopy(d);changed['accessors'][0]['sparse']={'count':0}
    reject(changed,[blob],drm,'Sparse')
    changed=copy.deepcopy(d);changed['bufferViews'][0]['byteLength']=1
    reject(changed,[blob],drm,'Out-of-bounds')
    with tempfile.TemporaryDirectory() as temp:
        root=pathlib.Path(temp)
        image=root/'source.gltf';image.write_text(json.dumps(d))
        mesh=root/'pokemon_00.drm';mesh.write_bytes(drm)
        out=root/'pokemon_00.drk'
        report=convert_paths(image,mesh,out)
        assert out.read_bytes()==drk and report['vertices']==6
        ext,raw,_=make_fixture(external=True)
        image.write_text(json.dumps(ext))
        (root/'model.bin').write_bytes(raw)
        parsed,bufs=load_document(image)
        assert bufs==[raw] and convert(parsed,bufs,drm)[0]==drk
        ext['buffers'][0]['uri']='../escape.bin'
        image.write_text(json.dumps(ext))
        try:load_document(image)
        except ValueError as error:assert 'Unsafe' in str(error)
        else:raise AssertionError('Path traversal accepted')
        ext['buffers'][0]['uri']='file:///etc/passwd'
        image.write_text(json.dumps(ext))
        try:load_document(image)
        except ValueError:pass
        else:raise AssertionError('Absolute file URI accepted')
    print('PASS: exact glTF/DRM mesh alignment, joint remap, keyframe retarget, strict rejections')


if __name__=='__main__':test()
