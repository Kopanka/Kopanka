#!/usr/bin/env python3
"""MAP-004: validate candidate sprites and assemble a small seam diagnostic.

This is a development-only diagnostic, NOT the final 512x512 terrain renderer,
NOT a claim that 16 connectivity masks or natural terrain were delivered.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
from PIL import Image, ImageDraw

ROOT=Path(__file__).resolve().parent
DATA=json.loads((ROOT/"manifest.json").read_text(encoding="utf-8"))
ASSETS=DATA["assets"]
IDS={a["id"]:a for a in ASSETS}
WIDTH,HEIGHT=128,64
STEP=13

def check():
    assert len(IDS)==len(ASSETS), "duplicate asset id"
    assert DATA["geometry"]["worldCols"]==DATA["geometry"]["worldRows"]==512
    assert (DATA["geometry"]["tileWidthPx"],DATA["geometry"]["tileHeightPx"])==(WIDTH,HEIGHT)
    assert DATA["geometry"]["tileAnchor"]==[64,32]
    assert DATA["geometry"]["cameraZoom"]==1.2
    assert DATA["geometry"]["heightStepPx"]==STEP
    counts={}
    for a in ASSETS:
        p=ROOT/a["path"]
        svg=ROOT/a["editableSource"]
        assert p.is_file() and svg.is_file(),a["id"]
        assert p.resolve().is_relative_to(ROOT.resolve())
        assert svg.resolve().is_relative_to(ROOT.resolve())
        im=Image.open(p)
        assert im.mode=="RGBA",a["id"]
        assert im.size==(a["widthPx"],a["heightPx"]),a["id"]
        assert 0<=a["anchorX"]<=im.width and 0<=a["anchorY"]<=im.height
        assert im.getchannel("A").getextrema()[0]==0
        assert im.getchannel("A").getextrema()[1]>0
        assert hashlib.sha256(p.read_bytes()).hexdigest()==a["sha256"]
        assert a["license"].strip()
        counts[a["layer"]]=counts.get(a["layer"],0)+1
    assert len(ASSETS)==27, f"unexpected count: {len(ASSETS)}"
    required=["hill_n_01","hill_e_01","hill_s_01","hill_w_01",
              "cliff_e_h1_01","cliff_s_h1_01","shore_e_01","shore_s_01",
              "ridge_peak_01","ridge_peak_06","natural_cave_01"]
    assert all(x in IDS for x in required)
    return counts

def render():
    # Showing adjacent anchored tiles makes layering, contours, and spacing
    # inspectable in one composite. It is NOT a seamless-world acceptance test.
    S=1.2
    canvas=Image.new("RGBA",(1500,1100),"#DCE6D5")
    draw=ImageDraw.Draw(canvas)
    tw,th=WIDTH*S,HEIGHT*S
    ox,oy=750,125

    def xy(c,r):
        return round(ox+(c-r)*tw/2),round(oy+(c+r)*th/2)

    # Base isometric checker for a 10x10 composition.
    for row in range(10):
        for col in range(10):
            x,y=xy(col,row)
            tone="#9DBE79" if (col+row)%3 else "#A5C683"
            draw.polygon([(x,y-th/2),(x+tw/2,y),(x,y+th/2),(x-tw/2,y)],
                         fill=tone)
    # Visible raised hill strips and individual cliffs along southeast.
    def sprite(sprite_id,c,r,y_shift=0):
        a=IDS[sprite_id]
        im=Image.open(ROOT/a["path"])
        im=im.resize((round(im.width*S),round(im.height*S)),Image.Resampling.LANCZOS)
        x,y=xy(c,r)
        left=round(x-a["anchorX"]*S)
        top=round(y-a["anchorY"]*S-y_shift*S)
        canvas.alpha_composite(im,(left,top))

    # The design candidates should align at identical anchors in this montage.
    for col in range(1,7):
        sprite(f"cliff_s_h1_{1+(col%2):02d}",col,2)
        sprite(f"hill_s_{1+(col%2):02d}",col,2)
    for row in range(3,8):
        sprite(f"cliff_e_h1_{1+(row%2):02d}",7,row)
        sprite(f"hill_e_{1+(row%2):02d}",7,row)
    for col in range(1,7):
        sprite(f"shore_s_{1+(col%2):02d}",col,8)
    for i,(col,row) in enumerate([(2,1),(4,1),(6,2),(2,4),(5,5),(4,7)],1):
        sprite(f"ridge_peak_{i:02d}",col,row)

    d=ImageDraw.Draw(canvas)
    d.rectangle((10,10,640,63),fill="#F4F6F1")
    d.text((22,22),"KOPANKA MAP-004 | 1.2x anchor & seam diagnostic",fill="#263332")
    d.text((22,42),"Preview ONLY — not a final natural 2.5D terrain or approved art.",fill="#687474")
    canvas.convert("RGB").save(ROOT/"tile_join_diagnostic.png",quality=94)

if __name__=="__main__":
    counts=check()
    render()
    mask_groups={
        "hill": sorted(k for k in IDS if k.startswith("hill_")),
        "cliff": sorted(k for k in IDS if k.startswith("cliff_")),
        "shore": sorted(k for k in IDS if k.startswith("shore_")),
        "mountains": sorted(k for k in IDS if k.startswith("ridge_peak_")),
        "naturalCave": sorted(k for k in IDS if k.startswith("natural_cave_")),
    }
    report={
        "assetCount":len(ASSETS),
        "countsByLayer":counts,
        "missingForProduction":[
            "Full 16-direction coastline/river connectivity variants",
            "All elevated corner and diagonal hill/cliff transitions",
            "Natural height-aware river estuary and source graphics",
            "Multiple connected mountain range groups and valleys",
            "Physical Android stitching and occlusion verification",
        ],
        "status":"TECHNICAL PREVIEW ONLY, NOT APPROVED",
        "assetGroups":{k:len(v) for k,v in mask_groups.items()},
    }
    (ROOT/"validation_report.json").write_text(
        json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print("PASS: 27 RGBA, source SVG, anchor, geometry, hash and alpha checks")
    print("Preview generated:",ROOT/"tile_join_diagnostic.png")
