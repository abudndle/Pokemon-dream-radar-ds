#!/usr/bin/env python3
"""Extract labelled English Nintendo MSBT texts from player's own Dream Radar RomFS.
Nonprintable styling/control codes are removed from the readable TSV; raw files remain in user's RomFS.
"""
import csv,sys,struct,re
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from darc import unpack_carc
rom=Path(__file__).resolve().parents[2]/'original_romfs/Message/English/MsgData.carc'
out=Path(__file__).resolve().parents[1]/'reference_original_dialogue.tsv'
def sections(b):
 pos=32; result={}
 while pos+16<=len(b):
  code=b[pos:pos+4].decode('ascii',errors='replace');size=struct.unpack_from('<I',b,pos+4)[0]
  if not size or pos+16+size>len(b):break
  result[code]=b[pos+16:pos+16+size];pos=(pos+16+size+15)&~15
 return result

def read_msbt(b):
 s=sections(b)
 if 'LBL1' not in s or 'TXT2' not in s:return []
 lbl=s['LBL1'];txt=s['TXT2'];groups=struct.unpack_from('<I',lbl,0)[0]
 count=struct.unpack_from('<I',txt,0)[0]
 offsets=struct.unpack_from('<%dI'%count,txt,4)
 names={}
 for i in range(groups):
  n,pos=struct.unpack_from('<II',lbl,4+i*8)
  for j in range(n):
   length=lbl[pos];pos+=1
   label=lbl[pos:pos+length].decode('ascii','replace');pos+=length
   index=struct.unpack_from('<I',lbl,pos)[0];pos+=4
   names[index]=label
 records=[]
 for i,off in enumerate(offsets):
  # Strip leading message controls and inline codes, keeping only readable UTF-16.
  end=offsets[i+1] if i+1<count else len(txt)
  bb=txt[off:end]
  text=bb.decode('utf-16-le',errors='ignore')
  # Codes FF FE are control introducers used by MSBT.
  text=re.sub(r'[\ue000-\uf8ff]','',text)
  text=''.join(c for c in text if c.isprintable() or c in '\n\t')
  text=text.replace('\x00','').strip()
  records.append((names.get(i,f'idx_{i}'),text))
 return records

files=unpack_carc(rom)
with open(out,'w',newline='',encoding='utf-8') as f:
 w=csv.writer(f,delimiter='\t');w.writerow(['table','label','text'])
 for filename,b in files.items():
  rows=read_msbt(b)
  for label,text in rows:w.writerow([filename,label,text])
  print(filename,'rows',len(rows),'example',rows[:1])
print('Wrote',out)
