#!/usr/bin/env python3
"""MAP-005 16 flat natural shoreline prototypes; not final artist-approved art.
Shared N=1, E=2, S=4, W=8; native RGBA diamond 128x64, anchor 64,32.
Drawing is clipped to the land tile and never draws on fog.
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageChops
import hashlib,json,math,random

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'shore_png'
S=4; W=128;H=64
V=[(64,0),(128,32),(64,64),(0,32)]
PAL={'sand':(196,180,126),'pebbles':(153,148,122),
     'grass':(126,158,103),'foam':(223,215,171)}

def paint(mask):
    img=Image.new('RGBA',(W*S,H*S),(0,0,0,0))
    for edge in range(4):
        if not(mask & (1<<edge)):continue
        a=V[edge];b=V[(edge+1)%4]
        mid=((a[0]+b[0])*.5,(a[1]+b[1])*.5)
        inx=64-mid[0];iny=32-mid[1]
        z=math.hypot(inx,iny);inx/=z;iny/=z
        def curve(dist):
            pts=[]
            for k in range(33):
                t=k/32
                bend=math.sin(math.pi*t)
                wiggle=(1.75*math.sin(3*math.pi*t+edge*.6)
                        +.95*math.sin(7*math.pi*t+edge))*bend
                d=max(0,dist+wiggle)
                pts.append((int((a[0]+(b[0]-a[0])*t+inx*d)*S),
                            int((a[1]+(b[1]-a[1])*t+iny*d)*S)))
            return pts
        d=ImageDraw.Draw(img)
        for outer,inner,color,alpha in [
                (0,12,PAL['sand'],132),(1,9,PAL['pebbles'],70),
                (2,5,PAL['foam'],92)]:
            d.polygon(curve(outer)+list(reversed(curve(inner))),
                      fill=(*color,alpha))
        rnd=random.Random(0xBEEF+edge*683)
        for j in range(14):
            t=rnd.uniform(.09,.91);dd=rnd.uniform(3.0,9.5)
            x=a[0]+(b[0]-a[0])*t+inx*dd
            y=a[1]+(b[1]-a[1])*t+iny*dd
            rr=rnd.uniform(.3,1.2)
            d.ellipse((int((x-rr)*S),int((y-rr*.6)*S),
                       int((x+rr)*S),int((y+rr*.6)*S)),
                      fill=(*PAL['grass'],145))
    crop=Image.new('L',img.size,0)
    ImageDraw.Draw(crop).polygon(
        [(int(x*S),int(y*S)) for x,y in V],fill=255)
    img.putalpha(ImageChops.multiply(img.getchannel('A'),crop))
    img=img.resize((W,H),Image.Resampling.LANCZOS)
    exact=Image.new('L',(W,H),0)
    ImageDraw.Draw(exact).polygon(V,fill=255)
    img.putalpha(ImageChops.multiply(img.getchannel('A'),exact))
    return img

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    m={'schemaVersion':1,'family':'natural_shore_flat_candidate_v2',
       'status':'TECHNICAL_AND_ART_CANDIDATE_NOT_APPROVED',
       'geometry':{'tileWidthPx':128,'tileHeightPx':64,
                   'tileAnchor':[64,32],'worldCols':512,
                   'worldRows':512,'cameraZoom':1.2},
       'bitOrder':'N=1 E=2 S=4 W=8','elevationLevels':[0],
       'limitations':['Flat grass-water only, not height-aware cliffs',
                      'Requires visual art and Android QA'],
       'assets':[]}
    for i in range(16):
        png=paint(i)
        p=OUT/f'natural_shore_mask_{i:02d}.png'
        png.save(p,optimize=True)
        m['assets'].append({
            'id':p.stem,'path':str(p.relative_to(ROOT)),
            'widthPx':128,'heightPx':64,'anchorX':64,'anchorY':32,
            'adjacencyMask':i,'footprintCols':1,'footprintRows':1,
            'layer':'coast',
            'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
    (ROOT/'manifest.json').write_text(
        json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    preview=Image.new('RGB',(1000,720),'#e3e8df')
    for i in range(16):
        x=24+i%4*246;y=24+i//4*175
        bg=Image.new('RGBA',(218,150),(224,230,219,255))
        ground=Image.new('RGBA',(128,64))
        ImageDraw.Draw(ground).polygon(V,fill=(130,178,106,255))
        bg.alpha_composite(ground,(43,28))
        bg.alpha_composite(
            Image.open(OUT/f'natural_shore_mask_{i:02d}.png'),(43,28))
        ImageDraw.Draw(bg).text((12,116),f'{i:02d} / {i:04b}',
                                fill=(29,50,35,255))
        preview.paste(bg.convert('RGB'),(x,y))
    preview.save(ROOT/'preview_16.png')
    print('Generated 16 candidate shore tiles; ART REVIEW PENDING')

if __name__=='__main__':
    main()
