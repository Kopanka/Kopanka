#!/usr/bin/env python3
"""MAP-005 diagnostic LAB: render existing generated candidate PNGs over
small 2.5D isometric cell arrangements, without changing authored 32x32 map.
This is an art-inspection image, not Android gameplay or seamless certification.
"""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import json,hashlib,math
P=Path(__file__).resolve().parent
ART=P.parent
C=(128,64); STEP=13
OUT=P/"join_lab.png"
CASE=[
  ("grass cliff E→sea, h1","water-cliff","cliff_water_e_h1_grass.png",1,"E"),
  ("rock cliff S→sea, h3","water-cliff","cliff_water_s_h3_rock.png",3,"S"),
  ("rock cliff E→sea, h5","water-cliff","cliff_water_e_h5_rock.png",5,"E"),
  ("grass cliff S→sea, h5","water-cliff","cliff_water_s_h5_grass.png",5,"S"),
  ("mixed cliff E1/S5","mixed","cliff_es_he1_grass_hs5_rock.png",5,"ES"),
  ("mixed cliff E5/S1","mixed","cliff_es_he5_rock_hs1_grass.png",5,"ES"),
  ("material seam E3/S3","mixed","cliff_es_he3_grass_hs3_rock.png",3,"ES"),
  ("material seam E5/S5","mixed","cliff_es_he5_rock_hs5_grass.png",5,"ES"),
]

def locate(kind,name):
    folder=("map-005-water-cliffs/water_cliff_png"
            if kind=="water-cliff"
            else "map-005-mixed-corners/corner_png")
    p=ART/folder/name
    if not p.exists():raise FileNotFoundError(p)
    return p

def diamond(x,y):
    return [(x,y-32),(x+64,y),(x,y+32),(x-64,y)]

def main():
    width,height=1300,910
    canvas=Image.new("RGBA",(width,height),(230,234,226,255))
    d=ImageDraw.Draw(canvas)
    logs=[]
    for i,(label,kind,name,h,side) in enumerate(CASE):
        px=14+(i%4)*321
        py=12+(i//4)*442
        card=Image.new("RGBA",(312,425),(218,225,213,255))
        cd=ImageDraw.Draw(card)
        cd.rectangle((2,2,309,422),outline=(123,138,126),width=2)
        cd.text((10,12),label,fill=(28,53,47))
        # Sketch 4-way adjacency: water under relevant cliff face, grass
        # on top. Native cell dimensions, height offset and origin unchanged.
        x,y=156,140
        cd.polygon(diamond(x+64,y+32),fill=(38,124,154))
        cd.polygon(diamond(x-64,y+32),fill=(38,124,154))
        cd.polygon(diamond(x,y+64),fill=(34,116,148))
        cd.polygon(diamond(x,y-h*STEP),fill=(138,176,110))
        asset=Image.open(locate(kind,name)).convert("RGBA")
        if asset.size!=(128,64+h*STEP+2):raise AssertionError(name)
        card.alpha_composite(asset,(x-64,y-h*STEP-32))
        cd=ImageDraw.Draw(card)
        cd.text((10,315),name,fill=(30,55,50))
        cd.text((10,336),"No seam acceptance / no Android integration",
                fill=(103,76,61))
        cd.text((10,356),"Same 128×64 diamond, anchor (64,32)",
                fill=(54,78,67))
        canvas.alpha_composite(card,(px,py))
        logs.append({"label":label,"file":str(locate(kind,name).relative_to(ART)),
                     "height":h,"kind":kind,"visibleSide":side})
    canvas.convert("RGB").save(OUT,optimize=True)
    (P/"join_lab_report.json").write_text(json.dumps({
        "status":"PROCEDURAL ART DIAGNOSTIC; NOT HUMAN APPROVED",
        "caseCount":len(logs),"geometry":{"tileWidthPx":128,
          "tileHeightPx":64,"anchor":[64,32],"zoom":1.2,
          "heightStepPx":STEP},
        "cases":logs,
        "limitations":["Only 8 representative cases from 156 candidates",
          "Not an actual 32x32 map or Android renderer",
          "No proof of connected multi-cell seams or visual quality"]
    },indent=2)+"\n")
    print("PASS: 8 targeted cliff-water/mixed-corner diagnostic composites")

if __name__=="__main__":
    main()
