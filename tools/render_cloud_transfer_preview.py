#!/usr/bin/env python3
"""Illustrative screenshot-style previews, not captures from a running emulator."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps
from struct import unpack_from
root=Path(__file__).resolve().parents[1];out=root/'preview';nit=root/'nitrofs';out.mkdir(exist_ok=True)
def raw(name):
 b=(nit/(name+'.raw')).read_bytes();im=Image.new('RGB',(256,192));pix=[]
 for o in range(0,len(b),2):
  v=unpack_from('<H',b,o)[0];pix.append(((v&31)<<3,((v>>5)&31)<<3,((v>>10)&31)<<3))
 im.putdata(pix);return im

def spr(name):
 b=(nit/(name+'.spr')).read_bytes();w,h=unpack_from('<HH',b)
 im=Image.new('RGBA',(w,h));px=[]
 for o in range(4,len(b),2):
  v=unpack_from('<H',b,o)[0];px.append(((v&31)<<3,((v>>5)&31)<<3,((v>>10)&31)<<3,255 if v&0x8000 else 0))
 im.putdata(px);return im
FONT=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf',11)
SMALL=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf',9)
WHITE=(244,249,251);CYAN=(65,244,241);GOLD=(250,191,86)
def text(im,xy,t,fill=WHITE,font=FONT):ImageDraw.Draw(im).text(xy,t,font=font,fill=fill)
def overlay(im,sprite,x,y):im.paste(sprite,(x,y),sprite)
# 1: original-inspired 3DS radar overview, dynamic sample values and original extracted markers.
top=raw('radar_overview')
for x,y,kind in [(132,41,0),(142,73,0),(175,75,1),(201,107,1),(160,122,0),(83,126,0),(78,131,0),(121,90,0),(151,109,0),(139,105,0)]:
 overlay(top,spr('radar_marker_dark' if kind else 'radar_marker_pink'),x-8,y-8)
overlay(top,spr('radar_arrow'),119,163)
text(top,(37,7),'10 / 10');text(top,(39,27),'2');text(top,(39,46),'8')
overlay(top,spr('radar_cloud_white'),8,3);overlay(top,spr('radar_cloud_white'),9,24)
# simple pink category marker from original cloud asset
overlay(top,spr('radar_cloud_pink'),9,43)
bottom=raw('game_bottom')
d=ImageDraw.Draw(bottom)
d.rectangle((53,4,92,20),fill=(10,14,19));text(bottom,(60,6),'10')
d.rectangle((207,4,254,19),fill=(10,14,19));text(bottom,(216,6),'235')
for i,(x,y) in enumerate([(99,110),(223,110),(163,168)]):
 d.rectangle((x-3,y-2,x+16,y+10),fill=(8,19,22));text(bottom,(x,y),str([2,0,1][i]),font=SMALL)
# 2: camera-free encounter uses supplied user's cloud image, still has hex controls.
cam=raw('game_top');overlay(cam,spr('reticle'),112,78)
ImageDraw.Draw(cam).rectangle((203,3,253,18),fill=(15,22,28));text(cam,(212,5),'122')
# 3: transfer screenshot-inspired six+six storage grid and no fake transfer promise.
trans_top=raw('transfer_top')
text(trans_top,(13,22),'Research data for')
text(trans_top,(13,41),'Pokemon White Version 2')
text(trans_top,(13,59),'is ready to archive.')
text(trans_top,(10,104),'Retail transfer unavailable',GOLD,SMALL)
text(trans_top,(10,124),'A saves text data only.',WHITE,SMALL)
text(trans_top,(10,138),'No retail save is changed.',WHITE,SMALL)
trans_bottom=raw('transfer_bottom')
for i,ix in enumerate([3,11,17]):overlay(trans_bottom,spr(f'pokemon_{ix:02d}'),30+33*i,35)
for i,ix in enumerate([0,5,13]):
 overlay(trans_bottom,spr(f'item_{ix:02d}'),30+33*i,80)
 text(trans_bottom,(41+33*i,99),str([3,1,2][i]),WHITE,SMALL)
text(trans_bottom,(11,167),'A ARCHIVE',WHITE,SMALL);text(trans_bottom,(147,167),'B BACK',WHITE,SMALL)
# preview posters with consistent 256x192 screens and no invented DS system shell.
pairs=[('Cloud radar overview',top,bottom),('Camera-free encounter',cam,bottom),('Research data archive',trans_top,trans_bottom)]
for name,t,b in pairs:
 sheet=Image.new('RGB',(256,398),(5,11,17));sheet.paste(t,(0,0));sheet.paste(b,(0,206));sheet.save(out/(name.lower().replace(' ','_')+'.png'))
canvas=Image.new('RGB',(3*536+36,884),(9,16,22));d=ImageDraw.Draw(canvas)
title_font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',21)
for idx,(name,t,b) in enumerate(pairs):
 x=18+idx*536
 d.text((x+7,11),name,font=title_font,fill=(225,249,250))
 canvas.paste(t.resize((512,384),Image.Resampling.NEAREST),(x,60))
 canvas.paste(b.resize((512,384),Image.Resampling.NEAREST),(x,458))
 d.text((x+4,851),'DS/DSi source preview — NOT an emulator capture',font=SMALL,fill=(177,204,204))
canvas.save(out/'cloud_search_transfer_triptych.png')
print('Created 3 pairs and contact sheet')
