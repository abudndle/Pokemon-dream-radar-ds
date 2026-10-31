#!/usr/bin/env python3
"""Convert verified images from the user's extracted Dream Radar NCCH into DSi assets.
Uses original RomFS CARC->LZH8->DARC->BCLIM; does not redistribute a commercial ROM.
"""
import sys, struct, math
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,ImageOps
ROOT=Path(__file__).resolve().parents[1]
TOOL_ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(TOOL_ROOT))
from darc import unpack_carc
from bclim import decode
rom=TOOL_ROOT/'original_romfs'
out=ROOT/'nitrofs'
out.mkdir(exist_ok=True,parents=True)

def image_from_carc(path,filename):
 files=unpack_carc(rom/path)
 for name,blob in files.items():
  if name.split('/')[-1]==filename:
   im,fmt=decode(blob)
   print(path,filename,im.size,fmt)
   return im
 raise FileNotFoundError(filename)

def rgb555(r,g,b):return 0x8000|((b>>3)<<10)|((g>>3)<<5)|(r>>3)

def save_raw(im,path):
 im=im.convert('RGB')
 if im.size!=(256,192):raise ValueError(im.size)
 d=bytearray()
 for r,g,b in im.getdata():d.extend(struct.pack('<H',rgb555(r,g,b)))
 (out/path).write_bytes(d)

def sprite(im,name,maxw=None,maxh=None):
 im=im.convert('RGBA')
 if maxw and maxh:im.thumbnail((maxw,maxh),Image.Resampling.LANCZOS)
 d=bytearray(struct.pack('<HH',*im.size))
 for r,g,b,a in im.getdata():
  v=(rgb555(r,g,b) if a>=80 else 0)
  d.extend(struct.pack('<H',v))
 (out/(name+'.spr')).write_bytes(d)

logo=image_from_carc('LocalizeTex/Tex_Title_En.carc','titlelogo00.bclim')
radar=image_from_carc('Ui/MnIf_U_MainMenu.carc','Radar00.bclim')
cloud=image_from_carc('Ui/MnIf_U_MainMenu.carc','RadarCloud00.bclim')
yellow=image_from_carc('Ui/MnIf_U_MainMenu.carc','RadarCloud01.bclim')
visor=image_from_carc('Ui/MnGm_U_Visor.carc','Search03.bclim')
orb=image_from_carc('Ui/MnGm_U_Visor.carc','Search00.bclim')
shop=image_from_carc('Ui/MnIf_U_Shop.carc','ShopImage00.bclim')
burnet=image_from_carc('Ui/MnIf_U_MessageWindow.carc','Chara00.bclim')
beam=image_from_carc('Ui/MnIf_S_ShopList.carc','IconPowerUp00.bclim')
energy=image_from_carc('Ui/MnIf_S_ShopList.carc','IconPowerUp01.bclim')
scope=image_from_carc('Ui/MnIf_S_ShopList.carc','IconPowerUp02.bclim')
icon=Image.open(TOOL_ROOT/'dream_radar_original_icon.png').convert('RGBA')
# Authentically sourced original UI sprites. No redraw of the logo.
sprite(logo,'logo',230,117)
sprite(cloud,'cloud',42,42)
sprite(yellow,'cloud_yellow',30,30)
sprite(visor,'reticle',32,32)
sprite(orb,'orb',58,58)
sprite(shop,'shop',128,64)
sprite(icon,'icon',96,96)
sprite(burnet,'burnet',150,150)
sprite(beam,'upgrade_beam')
sprite(energy,'upgrade_energy')
sprite(scope,'upgrade_scope')

font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',12)
font_sm=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',10)
def background(kind):
 if kind=='game':
  # User-provided camera-free fallback (not a real camera image).
  cloud_path=ROOT/'assets'/'no_camera_cloud_original.png'
  return ImageOps.fit(Image.open(cloud_path).convert('RGB'),(256,192),Image.Resampling.LANCZOS)
 im=Image.new('RGB',(256,192)); pix=im.load()
 for y in range(192):
  for x in range(256):
   dist=math.sqrt((x-128)**2+((y-96)*1.2)**2)
   level=max(0,int(17*(1-dist/240)))
   t=(y+5)/198
   pix[x,y]=(max(0,int(5+4*t+level//5)), int(30+20*t+level),int(43+26*t+level))
 draw=ImageDraw.Draw(im,'RGBA')
 if kind in ('title','top'):
  for r in (66,96,131,165):
   draw.ellipse((128-r,90-r,128+r,90+r),outline=(57,190,192,40),width=2)
  draw.arc((20,5,236,221),20,240,fill=(66,255,232,65),width=4)
  draw.line((10,174,247,174),fill=(45,176,201,70),width=2)
 if kind=='menu':
  # The turquoise ring and cloud are extracted from the original textures.
  rad=radar.convert('RGBA')
  if rad.size[0]>=128:
   rad.thumbnail((232,232));im.paste(rad,(36,-10),rad)
  draw.rounded_rectangle((8,11,248,178),12,outline=(39,178,202,110),width=2)
 if kind=='bottom':
  draw.rounded_rectangle((9,12,247,180),12,fill=(7,19,28,125),outline=(61,187,220,100),width=2)
 if kind=='game':
  for r in (40,72,115):draw.ellipse((128-r,92-r,128+r,92+r),outline=(44,210,210,30),width=2)
  draw.line((128,0,128,191),fill=(50,160,185,37),width=1)
  draw.line((0,92,255,92),fill=(50,160,185,37),width=1)
 return im
for name,kind in [('title_top','title'),('menu_top','menu'),('menu_bottom','bottom'),('game_top','game'),('game_bottom','bottom')]:
 im=background(kind)
 save_raw(im,name+'.raw')
 im.save(ROOT/'preview'/(name+'.png'))
print('Generated',len(list(out.iterdir())),'NitroFS assets')
