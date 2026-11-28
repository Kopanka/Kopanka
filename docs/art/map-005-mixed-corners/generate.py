#!/usr/bin/env python3
"""MAP-005 experimental E/S corner compositions: mixed heights and materials.

Derived from the existing MAP-005 height-face generator. This covers
h_E,h_S=1..5, material_E,material_S in {grass,rock}, excluding the ten
equal-height/same-material pairs already provided by cliff_es_corner_*.
It does NOT certify visually seamless mixed-height corners or water cliffs.
"""
from __future__ import annotations
from pathlib import Path
import hashlib
import json
import sys
import importlib.util
from PIL import Image, ImageDraw

HERE=Path(__file__).resolve().parent
ART_ROOT=HERE.parent
# Both folders contain generate.py. Import via an explicit path to avoid
# a self-import when test_mixed.py loads this module named "generate".
SOURCE=ART_ROOT/"map-005-height-faces"/"generate.py"
spec=importlib.util.spec_from_file_location("map005_height_face_source",SOURCE)
height_face_module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(height_face_module)
paint=height_face_module.paint
STEP=height_face_module.STEP

MATERIALS=("grass","rock")
HEIGHTS=range(1,6)
SIZE_X=128
ANCHOR=(64,32)

def compose(e_height:int,s_height:int,e_material:str,s_material:str):
    if not (e_height in HEIGHTS and s_height in HEIGHTS):
        raise ValueError("supported range 1..5")
    if e_material not in MATERIALS or s_material not in MATERIALS:
        raise ValueError("unknown terrain")
    h=64+max(e_height,s_height)*STEP+2
    composite=Image.new("RGBA",(SIZE_X,h),(0,0,0,0))
    # E and S each occupy one of the two lower sides of the isometric
    # diamond. Same draw order as the previously approved *technical*
    # equal-height candidate, not an independent painterly art pass.
    for side,level,material in (
        ("S",s_height,s_material),("E",e_height,e_material)):
        image=paint(side,level,material)
        composite.alpha_composite(image,(0,0))
    return composite

def candidates():
    for eh in HEIGHTS:
        for sh in HEIGHTS:
            for em in MATERIALS:
                for sm in MATERIALS:
                    if eh==sh and em==sm:
                        continue
                    yield eh,sh,em,sm

def main():
    output=HERE/"corner_png"
    output.mkdir(parents=True,exist_ok=True)
    manifest={
        "schemaVersion":1,
        "family":"map005_mixed_cliff_corner_candidate_v1",
        "status":"EXPERIMENTAL TECHNICAL GEOMETRY; NOT ART APPROVED OR ANDROID ENABLED",
        "geometry":{
            "worldCols":512,"worldRows":512,
            "tileWidthPx":128,"tileHeightPx":64,
            "tileAnchor":[64,32],"zoom":1.2,"heightStepPx":STEP
        },
        "compositionOrder":["S","E"],
        "junctionRule":"use one combined corner asset instead of separately overlapping both faces",
        "limitations":[
            "mixed-height/material corners require human pixel-level seam approval",
            "no terrain top or natural vegetation feathering",
            "no coast/water-cliff transition or diagonal shore",
            "not evaluated for fog, scene occlusion or performance on Android"
        ],
        "assets":[]
    }
    cases=list(candidates())
    for eh,sh,em,sm in cases:
        image=compose(eh,sh,em,sm)
        name=f"cliff_es_he{eh}_{em}_hs{sh}_{sm}.png"
        path=output/name
        image.save(path,optimize=True)
        manifest["assets"].append({
            "id":path.stem,"path":str(path.relative_to(HERE)),
            "widthPx":image.width,"heightPx":image.height,
            "footprintCols":1,"footprintRows":1,
            "anchorX":64,"anchorY":32,
            "sortFootY":64+max(eh,sh)*STEP,
            "layer":"cliff",
            "eastHeight":eh,"southHeight":sh,
            "eastMaterial":em,"southMaterial":sm,
            "heightMax":max(eh,sh),
            "junction":"mixed_height_or_material_E_S",
            "productionApproved":False,
            "sha256":hashlib.sha256(path.read_bytes()).hexdigest()
        })
    (HERE/"manifest.json").write_text(
        json.dumps(manifest,indent=2,ensure_ascii=False)+"\n",encoding="utf8")
    # Preview only a representative 4x4 cross-section. All 90 PNGs are in CI.
    samples=[(1,2,"grass","grass"),(2,1,"grass","grass"),
             (1,5,"grass","rock"),(5,1,"rock","grass"),
             (1,1,"grass","rock"),(2,2,"rock","grass"),
             (4,3,"grass","rock"),(3,4,"rock","grass"),
             (5,2,"rock","rock"),(2,5,"rock","rock"),
             (4,5,"grass","grass"),(5,4,"grass","grass"),
             (3,5,"rock","grass"),(5,3,"grass","rock"),
             (1,4,"grass","rock"),(4,1,"rock","grass")]
    sheet=Image.new("RGB",(960,900),(229,233,225))
    for i,case in enumerate(samples):
        img=compose(*case)
        x=18+(i%4)*238
        y=10+(i//4)*222
        panel=Image.new("RGBA",(225,215),(222,226,218,255))
        ground=Image.new("RGBA",(128,64))
        ImageDraw.Draw(ground).polygon(
            [(64,0),(128,32),(64,64),(0,32)],fill=(150,182,122,255))
        panel.alpha_composite(ground,(46,20))
        panel.alpha_composite(img,(46,20))
        ImageDraw.Draw(panel).text(
            (9,190),f"E{case[0]}-{case[2]} / S{case[1]}-{case[3]}",
            fill=(28,48,36,255))
        sheet.paste(panel.convert("RGB"),(x,y))
    sheet.save(HERE/"preview_16_mixed.png")
    print(f"Generated {len(cases)} mixed corner candidates; NOT approved")

if __name__=="__main__":
    main()
