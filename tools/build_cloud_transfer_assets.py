#!/usr/bin/env python3
"""Create native 256x192 DS surfaces from user reference shots + extracted original NCCH radar icons.
Dynamic counters, slots and live targets are deliberately rendered by ARM9 code.
Requires original ROM extraction only to REGENERATE these prebuilt .raw and .spr files.
"""
from pathlib import Path
from PIL import Image, ImageDraw
import math, struct, sys
ROOT=Path(__file__).resolve().parents[1]
NT=ROOT/'nitrofs';PV=ROOT/'preview'
ROMROOT=ROOT.parent/'dream_radar_dsi'
sys.path.insert(0,str(ROMROOT))
from darc import unpack_carc
from bclim import decode
files=unpack_carc(ROMROOT/'original_romfs'/'Ui'/'MnIf_U_MainMenu.carc')

def original(name):
    for key,data in files.items():
        if key.endswith('/'+name):return decode(data)[0].convert('RGBA')
    raise ValueError(name)

def rgb15(p):
    r,g,b=p[:3]
    return 0x8000|((b>>3)<<10)|((g>>3)<<5)|(r>>3)

def save_bitmap(im,name):
    im=im.convert('RGB'); assert im.size==(256,192)
    NT.joinpath(name+'.raw').write_bytes(b''.join(struct.pack('<H',rgb15(p)) for p in im.getdata()))
    im.save(PV/(name+'.png'))

def save_sprite(im,name,maxdim=None):
    im=im.convert('RGBA')
    if maxdim:im.thumbnail((maxdim,maxdim),Image.Resampling.LANCZOS)
    out=bytearray(struct.pack('<HH',*im.size))
    for p in im.getdata():out.extend(struct.pack('<H',rgb15(p) if p[3]>=70 else 0))
    NT.joinpath(name+'.spr').write_bytes(out)

save_sprite(original('RadarIcon00.bclim'),'radar_marker_pink',16)
save_sprite(original('RadarIcon01.bclim'),'radar_marker_dark',16)
save_sprite(original('Radar06.bclim'),'radar_arrow',23)
# Reference style: dark grid and large mint-green semicircle.
im=Image.new('RGB',(256,192));p=im.load()
for y in range(192):
 for x in range(256):
  r=math.hypot(x-128,y-202)
  inside=r<197
  fade=max(0,1-r/230)
  if inside:p[x,y]=(int(8+10*fade),int(66+67*fade),int(68+66*fade))
  else:p[x,y]=(8,20,23)
d=ImageDraw.Draw(im,'RGBA')
for x in range(0,256,16):d.line((x,0,x,191),fill=(72,153,157,32))
for y in range(0,192,16):d.line((0,y,255,y),fill=(72,153,157,32))
for r in (197,154,106,54):
 d.arc((128-r,202-r,128+r,202+r),180,360,fill=(83,234,225,245) if r==197 else (66,187,182,59),width=3 if r==197 else 1)
d.line((0,183,255,183),fill=(118,207,189,85),width=2)
# Use original 3DS radar ring texture faintly as detail behind live icons.
ring=original('Radar00.bclim').resize((194,194),Image.Resampling.LANCZOS)
ring.putalpha(ring.getchannel('A').point(lambda a: min(65,a//3)))
im_rg=im.convert('RGBA');im_rg.alpha_composite(ring,(62,0));im=im_rg.convert('RGB')
# Baked-in category strips, no values (render live and update each cloud hit).
d=ImageDraw.Draw(im,'RGBA')
for y,w in [(4,93),(25,65),(44,65)]:
 d.rounded_rectangle((5,y,w,y+17),radius=2,fill=(6,10,17,218),outline=(86,103,103,145),width=1)
save_bitmap(im,'radar_overview')
# Transfer top dialogue: source screenshot has a black grid with cyan-bordered box.
im=Image.new('RGB',(256,192),(3,9,15));d=ImageDraw.Draw(im,'RGBA')
for x in range(0,256,11):d.line((x,0,x,191),fill=(17,53,66,85))
for y in range(0,192,11):d.line((0,y,255,y),fill=(16,52,65,64))
d.rounded_rectangle((5,10,250,79),radius=4,fill=(24,25,29,248),outline=(28,206,223,235),width=2)
d.rounded_rectangle((9,89,246,184),radius=3,fill=(19,25,31,230),outline=(33,92,102,185))
save_bitmap(im,'transfer_top')
# Transfer bottom: exactly six cells across each of two separate rows.
im=Image.new('RGB',(256,192));p=im.load()
for y in range(192):
 for x in range(256):p[x,y]=(int(14+3*y/192),int(23+4*y/192),int(30+6*y/192))
d=ImageDraw.Draw(im,'RGBA')
for y in range(0,192,12):d.line((0,y,255,y),fill=(66,102,112,32))
for x in range(0,256,12):d.line((x,0,x,191),fill=(66,102,112,29))
d.rounded_rectangle((14,8,241,148),radius=12,fill=(81,82,88,245),outline=(120,227,239,255),width=4)
d.rounded_rectangle((20,13,235,143),radius=7,outline=(199,247,250,150),width=1)
for row in range(2):
 for col in range(6):
  x=28+col*33;y=30+row*47
  d.rectangle((x,y,x+27,y+32),fill=(88,92,97,245),outline=(69,76,81,220),width=1)
  d.rectangle((x+1,y+1,x+26,y+15),fill=(126,128,130,130))
for x in (5,130):
 d.rounded_rectangle((x,157,x+120,189),radius=4,fill=(70,79,87,250),outline=(159,178,192,240),width=2)
save_bitmap(im,'transfer_bottom')
print('PASS: 3 native backgrounds and 3 original radar icon sprites')
# Exact original 3DS Pokémon research icons, in the same species-index order as game.c.
species=['Munna','Tyltto','Fuwante','Riolu','Symboler','Pupurin','Tsubotsubo','Hitodeman','Porygon','Ralts','Dohmirror','Togepi','Muchul','Mikaruge','Rotom','Tornelos','Voltolos','Landlos','Dialga','Palkia','Giratina','Houou','Lugia','Dumbber','Yadon','Hoho']
monfiles=unpack_carc(ROMROOT/'original_romfs'/'Ui'/'MnIf_T_Pokemon.carc')
itemfiles=unpack_carc(ROMROOT/'original_romfs'/'Ui'/'MnIf_T_Item.carc')
def fromfiles(files,name):
    for key,data in files.items():
        if key.endswith('/'+name):return decode(data)[0].convert('RGBA')
    raise FileNotFoundError(name)
for i,name in enumerate(species):
    im=fromfiles(monfiles,'Ic'+name+'.bclim').resize((24,24),Image.Resampling.LANCZOS)
    save_sprite(im,f'pokemon_{i:02d}')
for i in range(23):
    im=fromfiles(itemfiles,'Ic%02d.bclim'%i).resize((24,24),Image.Resampling.LANCZOS)
    save_sprite(im,f'item_{i:02d}')
print('PASS: 26 real Pokémon thumbnail sprites + 23 original research-item icons')

# Small live cloud counter badges cropped from the player's real-game radar screenshot.
# Pixel transparency strips the photographed black HUD backing, so game counters stay dynamic.
radar_ref=Image.open(ROOT/'reference'/'image(4).png').convert('RGB')
for name,rect in [('radar_cloud_white',(12,8,53,38)),('radar_cloud_pink',(18,67,47,88))]:
    icon=radar_ref.crop(rect).convert('RGBA')
    px=[]
    for r,g,b,a in icon.getdata():
        light=max(r,g,b);alpha=255 if light>125 and (r+g+b)>300 else 0
        px.append((r,g,b,alpha))
    icon.putdata(px)
    icon.thumbnail((26,21),Image.Resampling.LANCZOS)
    save_sprite(icon,name)
print('PASS: reference-sourced original white/pink counter badges')
