#!/usr/bin/env python3
"""MAP-005 experimental 16-shoreline-mask generator.

Masks match Android MapSurface.neighborMask bit order N=1,E=2,S=4,W=8.
Each translucent RGBA overlay has a 128x64 iso diamond footprint,
anchor=(64,32); use on zero-elevation LAND adjacent to WATER only.
Not final painterly shoreline art or height-aware cliff textures.
"""
import hashlib
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageChops

ROOT=Path(__file__).resolve().parent
OUT=ROOT/"shore_png"
OUT.mkdir(exist_ok=True)
WIDTH,HEIGHT,SUPER=128,64,4
corners=[(64,0),(128,32),(64,64),(0,32)]
edges=list(zip(corners,corners[1:]+corners[:1]))
assets=[]

def render(mask):
    im=Image.new("RGBA",(WIDTH*SUPER,HEIGHT*SUPER),(0,0,0,0))
    d=ImageDraw.Draw(im)
    for edge_index,(a,b) in enumerate(edges):
        if not mask & (1<<edge_index): continue
        xy=[(round(x*SUPER),round(y*SUPER)) for x,y in [a,b]]
        for thickness,color in [
            (15,(132,124,81,112)),(11,(195,182,121,215)),
            (7,(225,207,149,235)),(2,(237,223,165,222))]:
            d.line(xy,fill=color,width=thickness*SUPER,joint="curve")
    crop=Image.new("L",im.size,0)
    ImageDraw.Draw(crop).polygon(
        [(x*SUPER,y*SUPER) for x,y in corners],fill=255)
    im.putalpha(ImageChops.multiply(im.getchannel("A"),crop))
    return im.resize((WIDTH,HEIGHT),Image.Resampling.LANCZOS)

for mask in range(16):
    name=f"coast_mask_{mask:02d}.png"
    im=render(mask)
    target=OUT/name
    im.save(target,optimize=True)
    assets.append(dict(
        id=name.removesuffix(".png"),path=f"shore_png/{name}",
        widthPx=WIDTH,heightPx=HEIGHT,footprintCols=1,footprintRows=1,
        anchorX=64,anchorY=32,sortFootY=32,layer="coast",
        adjacencyMask=mask,bitOrder="N=1 E=2 S=4 W=8",
        sha256=hashlib.sha256(target.read_bytes()).hexdigest()))
manifest=dict(name="MAP-005 shoreline adjacency technical prototypes",
              status="NOT ART APPROVED; zero-height shore only",
              geometry=dict(tileWidthPx=WIDTH,tileHeightPx=HEIGHT,
                            anchor=[64,32],zoom=1.2,
                            worldCols=512,worldRows=512),
              limitations=[
                  "Flat shoreline overlays, not natural height-aware coast",
                  "Diagonal corners, cliff transitions and physical Android QA pending"],
              assets=assets)
(ROOT/"shoreline_manifest.json").write_text(
    json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf8")
sheet=Image.new("RGB",(980,720),"#e4eae2")
for idx in range(16):
    x,y=(idx%4)*245+12,(idx//4)*180+12
    bg=Image.new("RGBA",(220,154),"#a9c58c")
    tile=Image.new("RGBA",(128,64),(0,0,0,0))
    ImageDraw.Draw(tile).polygon(corners,fill="#93b875")
    bg.alpha_composite(tile,(46,31))
    bg.alpha_composite(Image.open(OUT/f"coast_mask_{idx:02d}.png"),(46,31))
    ImageDraw.Draw(bg).text((11,123),f"MASK {idx:02d} / {idx:04b}",fill="#27372f")
    sheet.paste(bg.convert("RGB"),(x,y))
sheet.save(ROOT/"shoreline_16_preview.png")
print("MAP-005 generated all 16 shoreline candidates; NOT art-approved.")
