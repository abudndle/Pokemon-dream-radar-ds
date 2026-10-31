from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter
from pathlib import Path
from functools import lru_cache
import sys, struct, math, re
root=Path(__file__).resolve().parents[1]
refs=root/'reference';nt=root/'nitrofs';pv=root/'preview'
def to555(im,path):
 im=im.convert('RGB');assert im.size==(256,192)
 o=bytearray()
 for r,g,b in im.getdata():o+=struct.pack('<H',0x8000 | ((b>>3)<<10)|((g>>3)<<5)|(r>>3))
 (nt/path).write_bytes(o)
def spr(im,name):
 im=im.convert('RGBA');w,h=im.size;out=bytearray(struct.pack('<HH',w,h))
 for r,g,b,a in im.getdata():out+=struct.pack('<H', (0x8000|((b>>3)<<10)|((g>>3)<<5)|(r>>3)) if a>=80 else 0)
 (nt/(name+'.spr')).write_bytes(out)
for i in range(3):
 spr(Image.open(refs/f'IconBom0{i}_original.png').resize((16,16),Image.Resampling.LANCZOS),f'support_{i}')
# The original photographed title screen has a dark, almost solid midnight-blue
# background behind the extracted English logo (not a sci-fi radar ring).
title=Image.new('RGB',(256,192));px=title.load()
for y in range(192):
 for x in range(256):
  dx=(x-128)/130;dy=(y-88)/95
  glow=max(0,1-(dx*dx+dy*dy))
  px[x,y]=(int(6+6*glow),int(13+13*glow),int(29+33*glow))
draw_title=ImageDraw.Draw(title,'RGBA')
for y in range(0,192,3):
 draw_title.line((0,y,255,y),fill=(48,75,137,12))
to555(title,'title_original_top.raw');title.save(pv/'title_original_top.png')
# Main menu: 3DS screenshot geometry translated to 256x192 with flat blue horizontal list.
im=Image.new('RGB',(256,192));p=im.load()
for y in range(192):
 for x in range(256):
  v=math.sin((x+y)/22)*2;p[x,y]=(max(0,int(10+4*y/192+v)),int(25+19*y/192+v),int(42+22*y/192+v))
d=ImageDraw.Draw(im,'RGBA')
for x in range(0,256,12):d.line((x,0,x,192),fill=(30,112,135,30),width=1)
for y in range(0,192,12):d.line((0,y,256,y),fill=(30,112,135,20),width=1)
d.rounded_rectangle((6,7,249,40),radius=3,fill=(27,52,80,230),outline=(85,156,224,235),width=2)
d.rounded_rectangle((9,10,245,37),radius=3,fill=(35,75,118,200),outline=(134,218,255,140))
d.rounded_rectangle((13,12,239,32),radius=4,fill=(39,103,161,155))
# Share exactly the same title geometry as the renderer and touch hitboxes.
title_header=(root/'source/title_panes_generated.h').read_text()
pane_block=title_header.split('dr_title_panes[4] = {',1)[1].split('};',1)[0]
title_rects=[tuple(map(int,parts)) for parts in re.findall(r'\\{(\\d+),(\\d+),(\\d+),(\\d+)\\}',pane_block)]
assert len(title_rects)==4, 'expected 4 extracted title pane rectangles'
for xx,yy,ww,hh in title_rects:
 d.rounded_rectangle((xx,yy,xx+ww-1,yy+hh-1),radius=3,fill=(21,83,111,210),outline=(67,196,234,225),width=2)
 d.line((xx+5,yy+2,xx+ww-5,yy+2),fill=(165,238,255,70),width=2)
# menu button labels dynamic in program: leave text free
# footer from screenshot
d.rectangle((0,176,256,192),fill=(4,14,27,230))
to555(im,'title_menu_bottom.raw');im.save(pv/'title_menu_bottom.png')
# Search HUD from uploaded actual gameplay frame, the bottom half only.
source=Image.open(refs/'image(1).png').convert('RGB')
assert source.size==(400,480),source.size
# This is the original touchscreen region (x40..359, y240..479)
hud=source.crop((40,240,360,480)).resize((256,192),Image.Resampling.LANCZOS)
# The screenshot contains original buttons and hexagon art; counters and touch back label are overdrawn live in C.
to555(hud,'game_bottom.raw');hud.save(pv/'reference_game_bottom.png')
# Development Lab top: proper three rows, gold original equipment illustrations, dynamic levels/messages overlayed in C.
im=Image.new('RGB',(256,192));p=im.load()
for y in range(192):
 for x in range(256):
  v= int(3*math.sin((x+y)/27));p[x,y]=(int(36+4*y/192+v),int(38+5*y/192+v),int(38+6*y/192+v))
d=ImageDraw.Draw(im,'RGBA')
for x in range(0,256,15): d.line((x,0,x,191),fill=(169,171,164,27))
for y in range(0,192,15): d.line((0,y,255,y),fill=(169,171,164,27))
for i,y in enumerate([2,65,128]):
 d.rounded_rectangle((3,y,252,y+61),radius=3,fill=(22,23,28,215),outline=(155,155,160,200),width=1)
 d.rounded_rectangle((6,y+2,103,y+58),radius=2,fill=(12,12,12,155),outline=(180,139,45,200),width=1)
 tile=Image.open(refs/f'ShopImage0{i}_original.png').convert('RGBA')
 tile.thumbnail((91,54),Image.Resampling.LANCZOS)
 im.paste(tile,(8+(93-tile.width)//2,y+3+(55-tile.height)//2),tile)
 d.rounded_rectangle((105,y+2,250,y+58),radius=2,fill=(48,49,50,220),outline=(110,111,109,185),width=1)
 d.line((106,y+22,247,y+22),fill=(24,25,26,240),width=2)
# actual icons dynamic in C (and screenshot dialogue box overlay) not baked into this bitmap
to555(im,'development_top.raw');im.save(pv/'reference_development_top.png')
print('Created 3 reference-based backgrounds + original support item sprites.')
