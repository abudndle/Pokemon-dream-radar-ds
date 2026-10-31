from PIL import Image,ImageDraw,ImageFont
from pathlib import Path
from array import array
import struct
root=Path(__file__).resolve().parents[1];pv=root/'preview';n=root/'nitrofs';ref=root/'reference'
f='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
try: F=ImageFont.truetype(f,9);F2=ImageFont.truetype(f,10);F3=ImageFont.truetype(f,12)
except OSError: F=F2=F3=ImageFont.load_default()
def spr(name):
 raw=(n/(name+'.spr')).read_bytes();w,h=struct.unpack_from('<HH',raw,0);im=Image.new('RGBA',(w,h));px=[]
 for (v,) in struct.iter_unpack('<H',raw[4:]):
  px.append(((v&31)*255//31,((v>>5)&31)*255//31,((v>>10)&31)*255//31,255 if v&0x8000 else 0))
 im.putdata(px);return im
def paste(im,sp,x,y):
 tmp=spr(sp);im.paste(tmp,(x,y),tmp)
def b(name):return Image.open(pv/(name+'.png')).convert('RGB').copy()
def tx(d,x,y,s,font=F,col='#ecfeff'):d.text((x,y),s,fill=col,font=font)
def rect(d,xy,fill,outline=None,width=1):d.rectangle(xy,fill=fill,outline=outline,width=width)
# menu screen: same graphic as code, dynamic data (representative sample)
mt=b('title_original_top');paste(mt,'logo',13,22)
d=ImageDraw.Draw(mt);tx(d,11,165,'(c) 2012 Pokemon / Creatures',F,'#b9c2c4');tx(d,50,179,'GAME FREAK inc.',F,'#b9c2c4')
mb=b('title_menu_bottom');d=ImageDraw.Draw(mb)
tx(d,29,19,'CLOUDS 8/30',F2)
for i,t in enumerate(('Start','Send Research Data','Credits','Records')):
 y=45+31*i
 if i==0:d.rectangle((14,y,242,y+25),outline='#ffe23a',width=2)
 txtW=d.textbbox((0,0),t,font=F2)[2];tx(d,(256-txtW)//2,y+7,t,F2)
tx(d,41,178,'B: OPTIONS   A: SELECT',F,'#5ee7fa')
# development shop screen: faithful source row art and dynamic overlay
st=b('reference_development_top');d=ImageDraw.Draw(st)
for i,(label,lvl) in enumerate(zip(('Beam','Energy Pack','Visoscope'),(3,3,2))):
 y=[2,65,128][i];paste(st,('upgrade_beam','upgrade_energy','upgrade_scope')[i],105,y+5)
 tx(d,141,y+7,label,F3)
 for j in range(5):
  rect(d,(110+j*16,y+31,124+j*16,y+37),'#182329','#868687')
  if j<lvl:rect(d,(112+j*16,y+33,122+j*16,y+35),'#1ed75f')
 tx(d,209,y+32,f'Lv. {lvl}',F)
 if i==1:
  tx(d,109,y+43,'Support',F,'#57defc')
  for j,v in enumerate((0,0,1)):
   paste(st,f'support_{j}',159+j*29,y+38)
   tx(d,175+j*28,y+50,str(v),F)
rect(d,(7,27,249,57),'#222930','#64d7e9',2)
tx(d,13,33,'Pulls in Pokemon to a place',F2)
tx(d,13,44,'that makes them easy to catch.',F2)
rect(d,(180,0,255,10),'#171b1c');tx(d,187,0,'NEXT 1000',F,'#eac951')
sb=b('menu_bottom');d=ImageDraw.Draw(sb);tx(d,8,8,'Development Lab  ORBS 235',F2,'#f5d858')
for i,t in enumerate(('Beam Lv.3 -> 1000','Energy Pack Lv.3 -> 1000','Visoscope Lv.2 -> 500','Vortex Charge x0  100','Dragnet Charge x0  50','Energy Recharge x1  50')):
 y=26+24*i
 rect(d,(10,y,246,y+22),'#234755' if i==0 else '#153540','#ebd45b' if i==0 else '#4ab4c5',2)
 tx(d,19,y+6,t,F)
tx(d,12,177,'A: PURCHASE   B: RETURN',F,'#63dff2')
# Search camera-free top uses given user's exact cloud image, radar objects overlay
rt=b('game_top');paste(rt,'cloud',45,48);paste(rt,'cloud_yellow',173,95);paste(rt,'reticle',112,77)
d=ImageDraw.Draw(rt);d.rectangle((0,0,255,191),outline='#71f3fc',width=2)
tx(d,9,8,'CLOUDS 8',F2,'#74f5ff')
rb=b('reference_game_bottom');d=ImageDraw.Draw(rb)
d.rectangle((55,5,85,19),fill='#000000');tx(d,64,5,'8',F3)
d.rectangle((213,5,249,19),fill='#000000');tx(d,215,5,'235',F3)
for x,y,amt in ((99,111,'x0'),(223,111,'x0'),(162,167,'x1')):
 rect(d,(x-4,y-2,x+22,y+10),'#0a1419');tx(d,x,y,amt,F)
rect(d,(181,164,255,191),'#202a31');rect(d,(192,174,255,191),'#202a31','#95bfc8');tx(d,199,178,'B: BACK',F)
# native screenshot pairs and large composite
cols=[('MAIN MENU',mt,mb),('DEVELOPMENT LAB',st,sb),('NO-CAMERA SEARCH',rt,rb)]
for title,up,low in cols:
 name=title.lower().replace(' ','_').replace('-','_')
 up.save(pv/(name+'_top.png'));low.save(pv/(name+'_bottom.png'))
 sheet=Image.new('RGB',(256,388),'#11191c');sheet.paste(up,(0,0));sheet.paste(low,(0,196));sheet.save(pv/(name+'_native.png'))
W=3*288;canvas=Image.new('RGB',(W,492),'#101a20');d=ImageDraw.Draw(canvas)
for j,(title,up,low) in enumerate(cols):
 x=j*288+16
 tx(d,x,8,title,F3,'#92fbff');canvas.paste(up.resize((256,192),Image.Resampling.NEAREST),(x,37));canvas.paste(low.resize((256,192),Image.Resampling.NEAREST),(x,239))
 tx(d,x,447,'256 x 192 per screen',F2,'#aeb6c0')
 tx(d,x,466,'SOURCE PREVIEW / NOT EMULATOR',F,'#f5d477')
canvas.save(pv/'original_reference_layout_triptych.png')
print('Generated native-resolution previews and comparison sheet')
