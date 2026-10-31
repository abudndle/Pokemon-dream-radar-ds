#!/usr/bin/env python3
"""Extract geometric pane transforms from Pokémon Dream Radar CLYT files.
Geometry is ROM-derived; animation, material binding, visual parity unverified.
"""
import argparse, json, math, pathlib, struct
KINDS={b'pan1',b'pic1',b'txt1',b'bnd1',b'prt1',b'wnd1'}
def extract(path):
 b=path.read_bytes()
 if b[:4]!=b'CLYT' or b[4:6]!=b'\xff\xfe': raise ValueError(f'{path}: unsupported header/byte order')
 root=[]; stack=[]; last=None; offset=struct.unpack_from('<H',b,6)[0]; count=0
 while offset+8<=len(b):
  tag=b[offset:offset+4]; size=struct.unpack_from('<I',b,offset+4)[0]
  if size<8 or offset+size>len(b): raise ValueError(f'{path}: invalid section at {offset}')
  count+=1
  if tag in KINDS and size>=76:
   name=b[offset+12:offset+36].split(b'\0')[0].decode('utf-8','replace')
   values=struct.unpack_from('<10f',b,offset+36)
   entry={'name':name,'type':tag.decode('ascii'),'section_offset':offset,'flags':b[offset+8], 'origin':b[offset+9], 'alpha':b[offset+10],
          'translation':list(values[0:3]),'rotation':list(values[3:6]),'scale':list(values[6:8]),'size':list(values[8:10]),'children':[]}
   # values has 10 floats in pan1 (36 through 76).
   if stack:stack[-1]['children'].append(entry)
   else:root.append(entry)
   last=entry
  elif tag==b'pas1':
   if last is None:raise ValueError('orphan pas1')
   stack.append(last)
  elif tag==b'pae1':
   if not stack:raise ValueError('orphan pae1')
   stack.pop()
  offset+=size
 if stack:raise ValueError('unclosed pane hierarchy')
 return {'file':str(path),'sections':count,'panes':root}
def main():
 parser=argparse.ArgumentParser(); parser.add_argument('source');parser.add_argument('output');args=parser.parse_args()
 paths=sorted(pathlib.Path(args.source).rglob('*.bclyt'))
 out=[]
 for p in paths:
  try:out.append(extract(p))
  except Exception as exc:print('ERROR',exc);raise
 pathlib.Path(args.output).parent.mkdir(parents=True,exist_ok=True)
 pathlib.Path(args.output).write_text(json.dumps({'notice':'ROM-extracted transforms, not verified DS retargeting; BCLAN animation decoding still pending','layouts':out},indent=2))
 print('layouts',len(out),'panes',sum(len(str(x))>0 for x in out), 'bytes',pathlib.Path(args.output).stat().st_size)
if __name__=='__main__':main()
