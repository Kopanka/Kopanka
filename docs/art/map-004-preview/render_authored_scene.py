#!/usr/bin/env python3
"""MAP-005: compose the EXISTING Android demo geography (32x32) using tile sprites.

Produces a test-only full-scene reference at the approved camera angle.
Procedural trees/houses/cliff/river are preview placeholders, not game-ready
assets; candidate ridge/cave RGBA images are reused without re-rasterization.
No hero, UI, advertising, economic or gameplay elements.
"""
from __future__ import annotations
import json, math, random, hashlib, os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parent
DATA=json.loads((ROOT/"demo_32x32.json").read_text(encoding="utf-8"))
MANIFEST=json.loads((ROOT/"manifest.json").read_text(encoding="utf-8"))
assert DATA["width"]==DATA["height"]==32
assert MANIFEST["geometry"]["tileWidthPx"]==128
assert MANIFEST["geometry"]["tileHeightPx"]==64
ASSETS={a["id"]:a for a in MANIFEST["assets"]}
W,H=4650,2600
DX,DY=64,32
OX,OY=2300,110
HEIGHT_STEP=13
SEED=12345
rng=random.Random(SEED)
INTEGRATED=os.environ.get("MAP005_SCENE_VARIANT")=="integrated"
cliff_counts={"ordinary":0,"water":0,"corner_equal":0,"corner_mixed":0}
C=Image.new("RGBA",(W,H),(220,230,219,255))
d=ImageDraw.Draw(C,"RGBA")
cells=DATA["cells"]

def at(c,r):
    return cells[r][c] if 0<=c<32 and 0<=r<32 else None

def point(c,r):
    z=at(c,r)["elevation"]
    return round(OX+(c-r)*DX),round(OY+(c+r)*DY-z*HEIGHT_STEP)

def diamond(x,y):
    return [(x,y-DY),(x+DX,y),(x,y+DY),(x-DX,y)]

def height(c,r):
    v=at(c,r)
    return v["elevation"] if v else 0

def color(c,r,typ):
    noise=((c*37+r*19+c*r*3)%9)-4
    if typ=="sea": return (35,121+noise,155+noise//2,255)
    if typ=="mountain": return (151+noise,163+noise,135+noise,255)
    if typ=="meadow": return (159+noise,184+noise,112+noise,255)
    return (142+noise,178+noise,110+noise,255)

# A single antialias-free opaque base layer: no tile checker overlay under fog.
for level in range(63):
    for r in range(32):
        c=level-r
        v=at(c,r)
        if v is None: continue
        x,y=point(c,r)
        k=v["terrain"]
        z=v["elevation"]
        if INTEGRATED and z>0 and k!="sea":
            # Render the *same* authored height field with candidate RGBA
            # faces. This is a scene-composition diagnostic, not Android art.
            side_data=[]
            for dc,dr,side in ((1,0,"E"),(0,1,"S")):
                adj=at(c+dc,r+dr)
                lower=height(c+dc,r+dr)
                gap=max(0,z-lower)
                if not gap: continue
                mat="rock" if k=="mountain" else "grass"
                water=adj is not None and adj["terrain"]=="sea"
                side_data.append((side,gap,mat,water))
            images=[]
            if len(side_data)==2 and not any(t[3] for t in side_data):
                e,south=side_data
                if e[1]==south[1] and e[2]==south[2]:
                    file=ROOT.parent/"map-005-height-faces"/"cliff_png"/(
                        f"cliff_es_corner_h{e[1]}_{e[2]}.png")
                    cliff_counts["corner_equal"]+=1
                else:
                    file=ROOT.parent/"map-005-mixed-corners"/"corner_png"/(
                        f"cliff_es_he{e[1]}_{e[2]}_hs{south[1]}_{south[2]}.png")
                    cliff_counts["corner_mixed"]+=1
                images.append(file)
            else:
                for side,gap,mat,water in side_data:
                    if water:
                        file=ROOT.parent/"map-005-water-cliffs"/"water_cliff_png"/(
                            f"cliff_water_{side.lower()}_h{gap}_{mat}.png")
                        cliff_counts["water"]+=1
                    else:
                        file=ROOT.parent/"map-005-height-faces"/"cliff_png"/(
                            f"cliff_{side.lower()}_h{gap}_{mat}.png")
                        cliff_counts["ordinary"]+=1
                    images.append(file)
            for file in images:
                if not file.exists():
                    raise FileNotFoundError(file)
                im=Image.open(file).convert("RGBA")
                C.alpha_composite(im,(x-64,y-32))
        elif z>0 and k!="sea":
            for dc,dr,shade in ((1,0,(96,106,96,255)),(0,1,(117,126,109,255))):
                h=max(0,z-height(c+dc,r+dr))
                if h==0: continue
                if dc:
                    pts=[(x+DX,y),(x,y+DY),(x,y+DY+h*HEIGHT_STEP),
                         (x+DX,y+h*HEIGHT_STEP)]
                else:
                    pts=[(x,y+DY),(x-DX,y),(x-DX,y+h*HEIGHT_STEP),
                         (x,y+DY+h*HEIGHT_STEP)]
                # Earth/rock wall; organic striation instead of thin grey
                # border strokes crossing many adjacent cells.
                d.polygon(pts,fill=shade if k=="mountain" else (109,129,99,255))
        base=color(c,r,k)
        d.polygon(diamond(x,y),fill=base)
        if k!="sea":
            rr=random.Random((c*1009+r*7681)^SEED)
            for _ in range(9 if k=="mountain" else 7):
                px=x+rr.randrange(-42,43)
                py=y+rr.randrange(-18,19)
                d.ellipse((px-2,py-1,px+2,py+1),
                          fill=(210,205,168,rr.randrange(45,115)) if k=="mountain"
                          else (71,116,72,rr.randrange(35,80)))

# Technical MAP-005 shoreline experiment: zero-elevation land tiles only.
# Four-way adjacency corresponds exactly to Android MapSurface.neighborMask.
# Height-aware cliff/shore sprites must be designed separately, and these
# flat overlays are not the final approved painterly terrain.
shore_cnt=0
for row in range(32):
    for col in range(32):
        cell=at(col,row)
        if cell["terrain"]=="sea" or cell["elevation"]!=0:
            continue
        mask=0
        for dx,dy,bit in ((0,-1,1),(1,0,2),(0,1,4),(-1,0,8)):
            neighbor=at(col+dx,row+dy)
            if neighbor is not None and neighbor["terrain"]=="sea":
                mask|=bit
        if not mask: continue
        shore_file=(ROOT.parent/"map-005-natural-shore"/"shore_png"/f"natural_shore_mask_{mask:02d}.png"
                    if (INTEGRATED or os.environ.get("MAP005_SHORE_VARIANT")=="natural")
                    else ROOT/"shore_png"/f"coast_mask_{mask:02d}.png")
        shore=Image.open(shore_file).convert("RGBA")
        x,y=point(col,row)
        px,py=round(x-64),round(y-32)
        if 0<=px<=W-128 and 0<=py<=H-64:
            C.alpha_composite(shore,(px,py))
            shore_cnt+=1

# This is the original 37-cell author route, not a newly invented waterway.
path=[(v["col"],v["row"]) for v in DATA["riverPath"]]
assert path[0]==(5,3) and path[-1]==(24,20) and len(path)==37
p=[point(c,r) for c,r in path]
def catmull(a,b,c,e,t):
    t2=t*t;t3=t2*t
    return (.5*((2*b[0])+(-a[0]+c[0])*t+
       (2*a[0]-5*b[0]+4*c[0]-e[0])*t2+
       (-a[0]+3*b[0]-3*c[0]+e[0])*t3),
       .5*((2*b[1])+(-a[1]+c[1])*t+
       (2*a[1]-5*b[1]+4*c[1]-e[1])*t2+
       (-a[1]+3*b[1]-3*c[1]+e[1])*t3))
curve=[p[0]]
for i in range(len(p)-1):
    for j in range(1,9):
        curve.append(tuple(map(round,catmull(p[max(0,i-1)],p[i],
                                p[i+1],p[min(len(p)-1,i+2)],j/8))))
d.line(curve,fill=(202,189,140,255),width=24,joint="curve")
d.line(curve,fill=(43,126,159,255),width=19,joint="curve")
d.line(curve,fill=(99,165,179,125),width=4,joint="curve")
if INTEGRATED:
    # Estuary test: widen the final river segment into sea, keeping the
    # exact last authored cell (24,20) and avoiding a round terminal cap.
    a,b=curve[-10],curve[-1]
    vx,vy=b[0]-a[0],b[1]-a[1]
    size=math.hypot(vx,vy)
    if size:
        ux,uy=vx/size,vy/size
        nx,ny=-uy,ux
        reach=36;neck=10;wide=27
        target=(b[0]+ux*reach,b[1]+uy*reach)
        pts=[
            (b[0]+nx*neck,b[1]+ny*neck),
            (target[0]+nx*wide,target[1]+ny*wide),
            (target[0]-nx*wide,target[1]-ny*wide),
            (b[0]-nx*neck,b[1]-ny*neck)]
        d.polygon(pts,fill=(39,126,158,255))
        d.line([pts[0],pts[1]],fill=(181,194,150,110),width=2)
        d.line([pts[2],pts[3]],fill=(181,194,150,110),width=2)


def sprite(identifier,col,row,offset=0):
    a=ASSETS[identifier]
    im=Image.open(ROOT/a["path"]).convert("RGBA")
    x,y=point(col,row)
    left=int(x-a["anchorX"])
    top=int(y-a["anchorY"]-offset)
    if left>=0 and top>=0 and left+im.width<W and top+im.height<H:
        C.alpha_composite(im,(left,top))

def evergreen(x,y,scale=1):
    rr=random.Random(x*13+y*11)
    h=int(rr.randrange(36,54)*scale)
    d.ellipse((x-15*scale,y-5*scale,x+15*scale,y+5*scale),
              fill=(56,100,65,80))
    d.line((x,y-h//3,x,y),fill=(98,72,48,255),width=max(2,int(4*scale)))
    for t in (0,.22,.48):
        yt=y-h+round(h*t)
        wide=round((10+19*t)*scale)
        d.polygon([(x,yt),(x-wide,y-round(5*scale)),
                   (x+wide,y-round(5*scale))],
                  fill=rr.choice(((31,85,71,255),(32,98,77,255),(37,106,74,255))))
def broadleaf(x,y,scale=1):
    rr=random.Random(x*17+y*7)
    h=int(27*scale)
    d.ellipse((x-16*scale,y-5*scale,x+17*scale,y+4*scale),
              fill=(57,87,54,70))
    d.line((x,y-h-4*scale,x,y),fill=(118,83,53,255),width=max(2,int(5*scale)))
    for dx,dy,rad in [(-12,-h,13),(8,-h-8,15),(0,-h-14,16),(17,-h+4,10)]:
        q=(x+dx*scale,y+dy*scale)
        fill=rr.choice(((70,137,61,255),(83,148,73,255),(104,151,72,255)))
        d.ellipse((q[0]-rad*scale,q[1]-rad*scale,
                   q[0]+rad*scale,q[1]+rad*scale),fill=fill)

def village(x,y):
    # Pure visualization of the existing settlement footprint, not
    # individual Android assets and not additional gameplay.
    for i,(dx,dy) in enumerate([(-32,-1),(-1,-19),(32,4),(-11,19)]):
        bx,by=x+dx,y+dy
        d.polygon([(bx-14,by-8),(bx,by-16),(bx+14,by-8),(bx,by)],
                  fill=(147,82+i*7,47,255))
        d.polygon([(bx-11,by-7),(bx+11,by-7),(bx+11,by+11),(bx-11,by+11)],
                  fill=(229,206,164,255))
        d.rectangle((bx-3,by+1,bx+3,by+11),fill=(97,67,46,255))
def quarry(x,y):
    d.ellipse((x-45,y-18,x+44,y+22),fill=(174,154,114,255))
    for ox,oy,s in [(-19,-7,11),(13,-7,15),(1,8,8),(-28,11,6)]:
        d.polygon([(x+ox-s,y+oy),(x+ox,y+oy-s//2),
                   (x+ox+s,y+oy),(x+ox+8,y+oy+8)],
                  fill=(174,176,163,255))
def mine(x,y):
    d.ellipse((x-30,y-9,x+34,y+16),fill=(75,91,80,120))
    d.polygon([(x-25,y+7),(x-23,y-13),(x+4,y-23),(x+27,y-4),
               (x+25,y+10)],fill=(130,135,125,255))
    d.ellipse((x-15,y-13,x+16,y+14),fill=(31,40,39,255))
    d.line((x-16,y-15,x+17,y-15),fill=(111,84,57,255),width=5)

# Depth sorted scenery according to authored object cells.
objects=[]
for row in range(32):
    for col in range(32):
        v=at(col,row)
        for object_id in v.get("objects",[]):
            objects.append((col+row,col,row,object_id))
objects.sort()
counts={}
for _,c,r,obj in objects:
    counts[obj]=counts.get(obj,0)+1
    x,y=point(c,r)
    rr=random.Random(c*7757+r*127+SEED)
    if obj.startswith("forest_pine"):
        for dx,dy in [(-16,6),(10,1),(1,-10)]:
            evergreen(x+dx,y+dy,.84+rr.random()*.32)
    elif obj.startswith("forest_deciduous"):
        for dx,dy in [(-14,7),(11,-2),(3,-9)]:
            broadleaf(x+dx,y+dy,.76+rr.random()*.29)
    elif obj.startswith("mountain_"):
        idx=(c*7+r*13)%6+1
        sprite(f"ridge_peak_{idx:02d}",c,r)
    elif obj=="cave_entrance_small":
        sprite("natural_cave_01",c,r)
    elif obj=="mine_mountain_small":mine(x,y)
    elif obj=="quarry_plain_01":quarry(x,y)
    elif obj=="settlement_hamlet_01":village(x,y)
    elif obj=="island_small_01":
        d.ellipse((x-19,y-9,x+19,y+9),fill=(186,189,127,255))
        evergreen(x-4,y-4,.55)

# Footer/title annotations are on the *preview*, never Android gameplay UI.
try: font=ImageFont.truetype("DejaVuSans.ttf",38)
except OSError: font=ImageFont.load_default()
d.rounded_rectangle((35,30,1530,155),radius=18,fill=(247,250,243,235))
d.text((65,42),"KOPANKA — 32×32 authored world preview",fill=(36,56,52,255),font=font)
d.text((65,101),"MAP-005  |  2.5D scene-composition diagnostic  |  NOT Android art QA",
       fill=(95,104,91,255))
preview=C.convert("RGB")
preview.thumbnail((2050,1240),Image.Resampling.LANCZOS)
natural=INTEGRATED or os.environ.get("MAP005_SHORE_VARIANT")=="natural"
preview_file=("scene_32x32_integrated_candidate.jpg" if INTEGRATED
              else "scene_32x32_natural_shore.jpg" if natural
              else "scene_32x32_preview.jpg")
preview.save(ROOT/preview_file,quality=90,optimize=True)
report={"status":"TECHNICAL COMPOSITE, NOT FINAL ART",
        "width":32,"height":32,
        "authoredRiverCells":len(path),
        "shoreMaskCells":shore_cnt,
        "shoreCandidate":"natural v2" if natural else "flat v1",
        "sceneCandidate":"integrated v6" if INTEGRATED else ("natural shore v2" if natural else "baseline"),
        "cliffAssetsUsed":cliff_counts,
        "shoreMaskSchema":"N=1,E=2,S=4,W=8; demo flat land only",
        "objectsById":counts,
        "source":"Android PR #10 map_32x32.json exact copy",
        "components":"candidate PNG mountains/cave + procedural preview trees/river/cliffs",
        "doesNotReplace":"game tile atlas, QA or integration"}
(ROOT/("scene_32x32_integrated_candidate_report.json" if INTEGRATED
        else "scene_32x32_natural_shore_report.json" if natural
        else "scene_32x32_report.json")).write_text(
    json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
print("PASS: assembled 32x32 authored scene candidate",preview_file,cliff_counts)
