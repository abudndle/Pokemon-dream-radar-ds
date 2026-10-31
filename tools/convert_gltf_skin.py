#!/usr/bin/env python3
"""Strict, private glTF 2.0 skeletal animation export -> DRK1 sidecar.

Requires an existing DRM1 mesh with identical vertex ordering and triangles.
Does not decode copyrighted native Nintendo 3DS animation archives.
"""
import argparse
import base64
import bisect
import json
import math
import re
import struct
from pathlib import Path
from pack_drk1 import pack as pack_drk1

MAX_BUFFER = 16 * 1024 * 1024
MAX_JSON = 2 * 1024 * 1024
MAX_VERTICES = 2048
MAX_TRIANGLES = 2048
TOL = 1e-4
COMPONENTS = {5121: ('B', 1), 5123: ('H', 2), 5125: ('I', 4), 5126: ('f', 4)}
SIZES = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4, 'MAT4': 16}


def number(v):
    if type(v) not in (int, float) or not math.isfinite(v):
        raise ValueError('Nonfinite or nonnumeric glTF value')
    return float(v)


def indexed(arr, idx, what):
    if type(idx) is not int or not 0 <= idx < len(arr):
        raise ValueError(f'Invalid {what} index')
    return arr[idx]


def load_document(path: Path):
    if not path.is_file() or path.suffix.lower() != '.gltf' or path.stat().st_size > MAX_JSON:
        raise ValueError('Expected bounded glTF 2.0 JSON file (.gltf)')
    root = path.parent.resolve()
    obj = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(obj, dict) or obj.get('asset', {}).get('version') != '2.0':
        raise ValueError('Expected glTF asset version 2.0')
    if obj.get('extensionsRequired'):
        raise ValueError('Required glTF extensions are unsupported')
    blobs = []
    total = 0
    for b in obj.get('buffers', []):
        uri = b.get('uri')
        length = b.get('byteLength')
        if type(length) is not int or not 0 <= length <= MAX_BUFFER:
            raise ValueError('Invalid glTF buffer byte length')
        if not isinstance(uri, str):
            raise ValueError('GLB or missing buffer URI unsupported; export .gltf')
        if uri.startswith('data:application/octet-stream;base64,'):
            raw = uri.partition(',')[2]
            if len(raw) > MAX_BUFFER * 2:
                raise ValueError('Embedded buffer is too large')
            try:
                data = base64.b64decode(raw, validate=True)
            except (ValueError, base64.binascii.Error) as error:
                raise ValueError('Invalid embedded base64 buffer') from error
        else:
            if (not re.fullmatch(r'[A-Za-z0-9_./ -]+', uri) or
                    uri.startswith('/') or
                    any(part in ('', '.', '..') for part in uri.split('/'))):
                raise ValueError('Unsafe external glTF buffer URI')
            asset = (root / uri).resolve()
            if not asset.is_relative_to(root) or not asset.is_file() or asset.is_symlink():
                raise ValueError('glTF buffer escapes export directory')
            if asset.stat().st_size > MAX_BUFFER:
                raise ValueError('External glTF buffer too large')
            data = asset.read_bytes()
        if len(data) < length or len(data) > length + 3:
            raise ValueError('glTF buffer length mismatch')
        total += len(data)
        if total > MAX_BUFFER:
            raise ValueError('glTF binary budget exceeded')
        blobs.append(data)
    return obj, blobs


def accessor(obj, blobs, idx, *, kind=None, allowed=(5126,)):
    item = indexed(obj.get('accessors', []), idx, 'accessor')
    if not isinstance(item, dict) or 'sparse' in item:
        raise ValueError('Sparse/malformed glTF accessor unsupported')
    typ, component, count = item.get('type'), item.get('componentType'), item.get('count')
    if typ not in SIZES or (kind is not None and typ != kind) or component not in allowed:
        raise ValueError('Unexpected glTF accessor type')
    if type(count) is not int or not 1 <= count <= MAX_VERTICES * 8:
        raise ValueError('Invalid glTF accessor count')
    view = indexed(obj.get('bufferViews', []), item.get('bufferView'), 'bufferView')
    if not isinstance(view, dict):
        raise ValueError('Invalid glTF bufferView')
    buf = indexed(blobs, view.get('buffer'), 'buffer')
    code, size = COMPONENTS[component]
    unit = size * SIZES[typ]
    stride = view.get('byteStride', unit)
    offset = item.get('byteOffset', 0)
    start = view.get('byteOffset', 0)
    length = view.get('byteLength')
    if (any(type(n) is not int for n in (stride, offset, start, length)) or
            stride < unit or stride > 252 or offset < 0 or start < 0 or length < 0 or
            offset + (count - 1) * stride + unit > length or
            start + length > len(buf) or (start + offset) % size != 0):
        raise ValueError('Out-of-bounds or unaligned glTF accessor')
    decoder = struct.Struct('<' + code * SIZES[typ])
    rows = [decoder.unpack_from(buf, start + offset + i * stride) for i in range(count)]
    if component == 5126:
        for row in rows:
            for value in row:
                number(value)
    elif item.get('normalized', False):
        if component not in (5121, 5123):
            raise ValueError('Unexpected normalized component type')
        maximum = (1 << (size * 8)) - 1
        rows = [tuple(v / maximum for v in row) for row in rows]
    return rows


def read_drm(mesh: bytes):
    if len(mesh) < 8 or mesh[:4] != b'DRM1':
        raise ValueError('Expected DRM1 model')
    n, t = struct.unpack_from('<HH', mesh, 4)
    if not 3 <= n <= MAX_VERTICES or not 1 <= t <= MAX_TRIANGLES or len(mesh) != 8 + 6 * (n + t):
        raise ValueError('DRM1 model exceeds converter bounds or has invalid size')
    points = [struct.unpack_from('<hhh', mesh, 8 + i * 6) for i in range(n)]
    indices = [v for i in range(t) for v in struct.unpack_from('<HHH', mesh, 8 + 6*n + i*6)]
    if any(v >= n for v in indices):
        raise ValueError('Invalid DRM1 triangle index')
    return points, indices


def neutral_node(node):
    if not isinstance(node, dict) or 'matrix' in node:
        raise ValueError('Nodes with matrices require baking before export')
    if any(abs(number(x)-v) > TOL for x,v in zip(node.get('scale', [1,1,1]), [1,1,1])) or len(node.get('scale', [1,1,1])) != 3:
        raise ValueError('Non-identity scale unsupported; apply transforms')
    q = node.get('rotation', [0,0,0,1])
    if len(q) != 4 or any(abs(number(x)-v) > TOL for x,v in zip(q,[0,0,0,1])):
        raise ValueError('Non-identity bind rotation unsupported; bake rest pose')
    v = node.get('translation', [0,0,0])
    if len(v) != 3:
        raise ValueError('Malformed node translation')
    return [number(x) for x in v]


def yaw(q):
    if len(q) != 4:
        raise ValueError('Malformed quaternion')
    x,y,z,w = [number(v) for v in q]
    magnitude = math.sqrt(x*x+y*y+z*z+w*w)
    if abs(magnitude-1.0) > .005 or abs(x) > .001 or abs(z) > .001:
        raise ValueError('Only normalized Y-axis bone rotations supported')
    return math.atan2(y,w)*2


def interpolated(times, values, t, path, method):
    if t <= times[0]: return values[0]
    if t >= times[-1]: return values[-1]
    i = bisect.bisect_right(times, t)-1
    if method == 'STEP': return values[i]
    ratio = (t-times[i])/(times[i+1]-times[i])
    if path == 'rotation':
        # Pure Y-axis quaternion slerp reduces to shortest-angle interpolation.
        a,b = yaw(values[i]), yaw(values[i+1])
        delta = (b-a+math.pi)%(2*math.pi)-math.pi
        angle = a + delta * ratio
        return [0,math.sin(angle/2),0,math.cos(angle/2)]
    return [a+(b-a)*ratio for a,b in zip(values[i],values[i+1])]


def convert(document: dict, blobs: list, drm: bytes, *, animation_index=0, frames=4, ticks=8):
    if type(frames) is not int or not 2 <= frames <= 8 or type(ticks) is not int or not 1 <= ticks <= 60:
        raise ValueError('DRK1 needs 2..8 samples, each 1..60 ticks')
    points, topology = read_drm(drm)
    nodes = document.get('nodes', [])
    skins = document.get('skins', [])
    meshes = document.get('meshes', [])
    if not all(isinstance(node,dict) for node in nodes):
        raise ValueError('Malformed glTF nodes')
    owners = {}
    for i,node in enumerate(nodes):
        for child in node.get('children', []):
            indexed(nodes,child,'child node')
            if child in owners: raise ValueError('Nodes with multiple parents unsupported')
            owners[child] = i
    roots = [i for i,node in enumerate(nodes) if 'skin' in node and 'mesh' in node]
    if len(roots) != 1:
        raise ValueError('Requires exactly one node with skin and mesh')
    instance = nodes[roots[0]]
    skin = indexed(skins,instance['skin'],'skin')
    mesh = indexed(meshes,instance['mesh'],'mesh')
    if neutral_node(instance) != [0.,0.,0.]:
        raise ValueError('Skin mesh node must have identity transform')
    primitives = mesh.get('primitives', [])
    if len(primitives) != 1:
        raise ValueError('Requires one uncompressed mesh primitive')
    primitive = primitives[0]
    if primitive.get('extensions') or primitive.get('targets') or primitive.get('mode',4) != 4:
        raise ValueError('Unsupported compressed, morph or nontriangle primitive')
    attributes = primitive.get('attributes',{})
    if any(x in attributes for x in ('JOINTS_1','WEIGHTS_1')):
        raise ValueError('More than four incoming joint influences unsupported')
    positions = accessor(document,blobs,attributes.get('POSITION'),kind='VEC3')
    joints = accessor(document,blobs,attributes.get('JOINTS_0'),kind='VEC4',allowed=(5121,5123))
    weights = accessor(document,blobs,attributes.get('WEIGHTS_0'),kind='VEC4',allowed=(5121,5123,5126))
    if len(positions)!=len(points) or len(joints)!=len(points) or len(weights)!=len(points):
        raise ValueError('Original glTF and DRM1 vertex counts disagree')
    for old,new in zip(positions,points):
        if any(abs(a*4096-b) > 1.05 for a,b in zip(old,new)):
            raise ValueError('Vertex order/position mismatch between glTF and DRM1')
    if 'indices' not in primitive:
        if topology != list(range(len(topology))):
            raise ValueError('glTF has no index array but DRM1 topology is not sequential')
    else:
        indices = [row[0] for row in accessor(document,blobs,primitive['indices'],kind='SCALAR',allowed=(5121,5123,5125))]
        if indices != topology:
            raise ValueError('Mesh triangle indices/order mismatch with DRM1')
    old_joints = skin.get('joints')
    if not isinstance(old_joints,list) or not 1 <= len(old_joints) <= 16 or len(set(old_joints)) != len(old_joints):
        raise ValueError('Unsupported skin joint list')
    for j in old_joints: indexed(nodes,j,'joint')
    # Stable parent-before-child order, even if skin.joints lists children first.
    joint_set = set(old_joints)
    sorted_joints=[]
    visiting=set()
    def add(j):
        if j in sorted_joints:return
        if j in visiting:raise ValueError('Cyclic bone hierarchy')
        visiting.add(j)
        p=owners.get(j)
        if p is not None and p not in joint_set:
            raise ValueError('Joint parent outside selected skin unsupported')
        if p is not None:add(p)
        neutral_node(nodes[j])
        sorted_joints.append(j)
        visiting.remove(j)
    for j in old_joints:add(j)
    to_new = {joint:i for i,joint in enumerate(sorted_joints)}
    pivots={}
    bones=[]
    for j in sorted_joints:
        local = neutral_node(nodes[j])
        parent = owners.get(j)
        base = pivots[parent] if parent is not None else [0.,0.,0.]
        pivot=[local[i]+base[i] for i in range(3)]
        pivots[j]=pivot
        q12=[round(x*4096) for x in pivot]
        if any(abs(v)>32767 for v in q12):
            raise ValueError('Bind pivot outside DRM1 signed-Q12 range')
        bones.append({'pivot':q12,'parent':to_new[parent] if parent is not None else -1})
    if skin.get('inverseBindMatrices') is not None:
        matrices=accessor(document,blobs,skin['inverseBindMatrices'],kind='MAT4')
        if len(matrices)!=len(old_joints):
            raise ValueError('Inverse bind matrix count mismatch')
        for j,matrix in zip(old_joints,matrices):
            target=[1,0,0,0, 0,1,0,0, 0,0,1,0,
                    -pivots[j][0],-pivots[j][1],-pivots[j][2],1]
            if any(abs(a-b)>.002 for a,b in zip(matrix,target)):
                raise ValueError('Nontranslation inverse-bind matrix; bake bind transforms')
    influences=[]
    for js,ws in zip(joints,weights):
        values=[]
        for ji,w in zip(js,ws):
            if type(ji) is not int or not 0 <= ji < len(old_joints):
                raise ValueError('Invalid glTF JOINTS_0 entry')
            w=number(w)
            if not 0 <= w <= 1.01:raise ValueError('Invalid vertex weight')
            if w>1e-5:values.append((to_new[old_joints[ji]],w))
        if len(values)>2 or not values:
            raise ValueError('DRK1 supports exactly one or two positive bone influences')
        total=sum(w for _,w in values)
        if abs(total-1)>0.025:
            raise ValueError('glTF weights must be normalized')
        if len(values)==1:
            a=values[0][0];influences.append([a,a,255])
        else:
            (a,w),(b,_) = values
            influences.append([a,b,max(0,min(255,round(w/total*255)))])
    animations = document.get('animations',[])
    anim=indexed(animations,animation_index,'animation')
    channels={}
    duration=0.
    for channel in anim.get('channels',[]):
        target=channel.get('target',{})
        joint=target.get('node')
        path=target.get('path')
        if joint not in joint_set or path not in ('rotation','translation'):
            raise ValueError('Animation channels must target joint translation/yaw only')
        if (joint,path) in channels:
            raise ValueError('Duplicate joint animation channels')
        samp=indexed(anim.get('samplers',[]),channel.get('sampler'),'sampler')
        method=samp.get('interpolation','LINEAR')
        if method not in ('LINEAR','STEP'):
            raise ValueError('CUBICSPLINE interpolation unsupported')
        times=[x[0] for x in accessor(document,blobs,samp.get('input'),kind='SCALAR')]
        values=accessor(document,blobs,samp.get('output'),kind='VEC4' if path=='rotation' else 'VEC3')
        if len(times)!=len(values) or len(times)<2 or times[0]<0 or any(b<=a for a,b in zip(times,times[1:])):
            raise ValueError('Invalid animation sampler timeline')
        if path=='rotation':
            for v in values:yaw(v)
        if times[-1] > duration:duration=times[-1]
        channels[(joint,path)]=(times,values,method)
    if not channels or duration<=0 or duration>60:
        raise ValueError('Empty, overlong or invalid animation duration')
    def pose_at(j,t):
        rest=neutral_node(nodes[j])
        if (j,'translation') in channels:
            times,values,method=channels[(j,'translation')]
            trans=interpolated(times,values,t,'translation',method)
        else:
            trans=rest
        offset=[]
        for x,origin in zip(trans,rest):
            value=round((x-origin)*256)
            if not -128<=value<=127:
                raise ValueError('Animated bone translation outside DRK1 signed-8-bit range')
            offset.append(value)
        if (j,'rotation') in channels:
            times,values,method=channels[(j,'rotation')]
            theta=yaw(interpolated(times,values,t,'rotation',method))
            angle=round(theta/(2*math.pi)*256)
            angle=(angle+128)%256-128
        else:angle=0
        return offset+[angle]
    # Reject non-looping actions instead of making an invisible seam at wrap.
    for j in sorted_joints:
        start=pose_at(j,0.)
        end=pose_at(j,duration)
        if any(abs(a-b)>1 for a,b in zip(start[:3],end[:3])) or abs((start[3]-end[3]+128)%256-128)>1:
            raise ValueError('Animation is not a closed loop: bake a looping glTF clip')
    poses=[[pose_at(j,duration*f/frames) for j in sorted_joints] for f in range(frames)]
    data=pack_drk1(drm,bones,influences,poses,ticks)
    return data,{'format':'DRK1','source':'user_glTF_2.0_export',
                 'verified_original_3ds_animation':False,
                 'vertices':len(points),'bones':len(bones),'frames':frames,
                 'ticks_per_frame':ticks,'source_duration_seconds':duration,
                 'limitations':['yaw_only','max_two_influences','baked_neutral_pose_required',
                                'uniform_loop_samples','integer_quantization']}


def convert_paths(gltf: Path, mesh: Path, output: Path, *, animation=0, frames=4, ticks=8):
    document,blobs=load_document(gltf)
    data,report=convert(document,blobs,mesh.read_bytes(),animation_index=animation,
                        frames=frames,ticks=ticks)
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_bytes(data)
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--gltf',type=Path,required=True)
    p.add_argument('--mesh',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--animation',type=int,default=0)
    p.add_argument('--frames',type=int,default=4)
    p.add_argument('--ticks',type=int,default=8)
    p.add_argument('--report',type=Path,help='Optional metadata-only validation report')
    args=p.parse_args()
    report=convert_paths(args.gltf,args.mesh,args.output,animation=args.animation,
                         frames=args.frames,ticks=args.ticks)
    if args.report:
        args.report.parent.mkdir(parents=True,exist_ok=True)
        args.report.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print('Converted',report['vertices'],'aligned vertices and',report['bones'],
          'validated bones (not an original 3DS animation decoder)')


if __name__=='__main__':main()
