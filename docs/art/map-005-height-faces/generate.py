#!/usr/bin/env python3
"""MAP-005: height-aware visible cliff faces E/S; *experimental* art.
Two material classes × levels 1/2, fixed STEP=13px at zoom 1x.
RGBA objects, native width128, anchor(64,32); no game renderer changes.
"""
from pathlib import Path
from PIL import Image,ImageDraw,ImageChops
import hashlib,json,math,random
P=Path(__file__).resolve().parent
V={'E':((128,32),(64,64)),'S':((64,64),(0,32))}
MATS={'grass':((110,143,93),(74,111,71),(170,174,119)),
      'rock':((135,138,126),(79,88,84),(187,181,162))}
STEP=13

def paint(side,level,mat):
    W=128;H=64+level*STEP+2;S=4
    img=Image.new('RGBA',(W*S,H*S))
    d=ImageDraw.Draw(img)
    a,b=V[side];dy=level*STEP
    def bottom(t):
        jiggle=1.8*math.sin(3*math.pi*t+.7)*math.sin(math.pi*t)
        return (a[0]+(b[0]-a[0])*t,
                a[1]+(b[1]-a[1])*t+dy+jiggle)
    poly=[(round(x*S),round(y*S)) for x,y in (a,b)]
    poly += [(round(x*S),round(y*S))
             for x,y in (bottom(j/32) for j in range(32,-1,-1))]
    base,shade,light=MATS[mat]
    d.polygon(poly,fill=(*base,255))
    mask=Image.new('L',img.size)
    ImageDraw.Draw(mask).polygon(poly,fill=255)
    rnd=random.Random(1246+level*991+
                      (1 if side=='E' else 3)*176+
                      (1 if mat=='rock' else 0)*2263)
    for i in range(33):
        t=rnd.uniform(.03,.97)
        x=a[0]+(b[0]-a[0])*t
        y=a[1]+(b[1]-a[1])*t
        h=rnd.uniform(.15,.85)*dy
        wid=rnd.uniform(1.2,4.1)
        col=light if i%4==0 else shade
        d.line([(int((x-wid)*S),int((y+h*.12)*S)),
                (int((x+wid*.4)*S),int((y+h*.38)*S)),
                (int((x+wid*.55)*S),int((y+h)*S))],
                fill=(*col,155),width=rnd.choice([1,2,3])*S)
    img.putalpha(ImageChops.multiply(img.getchannel('A'),mask))
    return img.resize((W,H),Image.Resampling.LANCZOS)

def main():
    output=P/'cliff_png';output.mkdir(exist_ok=True)
    m={'family':'map005_height_cliff_face_v2',
       'status':'TECHNICAL ART CANDIDATE — NOT APPROVED',
       'geometry':{'worldCols':512,'worldRows':512,
                   'tileWidthPx':128,'tileHeightPx':64,
                   'tileAnchor':[64,32],'zoom':1.2,'heightStepPx':STEP},
       'limitations':['E/S sides only; corners/junctions not covered',
                      'Levels 3-5 not generated',
                      'On-device visual, fog and occlusion QA required'],
       'assets':[]}
    sheet=Image.new('RGB',(960,560),'#e7e8df')
    variants=((s,l,mat) for s in 'ES' for l in (1,2)
              for mat in ('grass','rock'))
    for i,(side,level,mat) in enumerate(variants):
        im=paint(side,level,mat)
        name=f'cliff_{side.lower()}_h{level}_{mat}.png'
        path=output/name;im.save(path,optimize=True)
        m['assets'].append({
            'id':path.stem,'path':str(path.relative_to(P)),
            'widthPx':im.width,'heightPx':im.height,
            'anchorX':64,'anchorY':32,'sortFootY':64+level*STEP,
            'heightLevel':level,'visibleSide':side,
            'material':mat,'layer':'cliff',
            'footprintCols':1,'footprintRows':1,
            'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
        x=25+(i%4)*235;y=20+(i//4)*270
        frame=Image.new('RGBA',(220,245),(222,227,217,255))
        base=Image.new('RGBA',(128,64))
        ImageDraw.Draw(base).polygon(
            [(64,0),(128,32),(64,64),(0,32)],fill=(139,181,105,255))
        frame.alpha_composite(base,(43,44))
        frame.alpha_composite(im,(43,44))
        ImageDraw.Draw(frame).text((12,207),name,fill=(35,49,34,255))
        sheet.paste(frame.convert('RGB'),(x,y))
    sheet.save(P/'preview_8.png')
    (P/'manifest.json').write_text(
        json.dumps(m,ensure_ascii=False,indent=2)+'\n')
    print('Generated eight candidate height-aware cliff faces; ART PENDING')

if __name__=='__main__':
    main()
