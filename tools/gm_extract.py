"""Export every sprite frame of a GameMaker data.win / game.ios as PNGs (texture pages cut by the TPAG table).

    python tools/gm_extract.py DATA_FILE OUTDIR

Used on Elevator Pitch (Hugimugi, Amerigo Gazaway) to get the elevator doors, frame and buttons for the lift
cutscene; see tools/make_elevator_sprites.py. The game files and the raw frames are not in the repository.
"""
import struct,sys,os,io,re
from PIL import Image
path,out=sys.argv[1:3]
d=open(path,'rb').read()
assert d[:4]==b'FORM'
chunks={};p=8
while p<len(d):
    n=d[p:p+4].decode();ln=struct.unpack_from('<I',d,p+4)[0];chunks[n]=(p+8,ln);p+=8+ln
print(list(chunks))
u32=lambda o:struct.unpack_from('<I',d,o)[0]
u16=lambda o:struct.unpack_from('<H',d,o)[0]
def string(ptr):                      # ptr -> chars
    e=d.index(b'\0',ptr);return d[ptr:e].decode('utf8','replace')
# textures
txtr_off,txtr_len=chunks['TXTR']
pngs=[]
seg=d[txtr_off:txtr_off+txtr_len]
for m in re.finditer(b'\x89PNG\r\n\x1a\n',seg):
    s=m.start();e=seg.index(b'IEND',s)+8
    pngs.append(Image.open(io.BytesIO(seg[s:e])).convert('RGBA'))
print('texture pages',[im.size for im in pngs])
# tpag
to,tl=chunks['TPAG'];cnt=u32(to);tp={}
for i in range(cnt):
    off=u32(to+4+i*4)
    sx,sy,sw,sh,tx,ty,tw,th,bw,bh,pg=struct.unpack_from('<HHHHHHHHHHH',d,off)
    tp[off]=(sx,sy,sw,sh,tx,ty,tw,th,bw,bh,pg)
print('tpag',cnt)
# sprites
so,sl=chunks['SPRT'];cnt=u32(so);sprites={}
for i in range(cnt):
    off=u32(so+4+i*4)
    name=string(u32(off))
    w,h,ml,mr,mb,mt,tr,sm,pre,bb,sep,ox,oy=struct.unpack_from('<IIiiiiIIIIIii',d,off+4)
    q=off+4+13*4
    if u32(q)==0xFFFFFFFF:                                  # GMS2 'special' sprite header
        ver=u32(q+4); q+=16+(4 if ver>=2 else 0)+(4 if ver>=3 else 0)
        q+=4
    n=u32(q);frames=[u32(q+4+k*4) for k in range(n)]
    sprites[name]=(w,h,frames)
print('sprites',len(sprites)); 
os.makedirs(out,exist_ok=True)
saved=0
for name,v in sprites.items():
    if not v: continue
    w,h,frames=v
    for k,f in enumerate(frames):
        if f not in tp: continue
        sx,sy,sw,sh,tx,ty,tw,th,bw,bh,pg=tp[f]
        im=Image.new('RGBA',(max(w,1),max(h,1)),(0,0,0,0))
        im.paste(pngs[pg].crop((sx,sy,sx+sw,sy+sh)),(tx,ty))
        im.save(os.path.join(out,'%s_%d.png'%(name,k)));saved+=1
print('saved',saved)
print(sorted(sprites)[:300])
