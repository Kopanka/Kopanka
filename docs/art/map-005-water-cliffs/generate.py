#!/usr/bin/env python3
"""MAP-005: exploratory cliff-to-water variants with shoreline at the foot.
20 transparent RGBA candidates: east/south x 1..5 elevations x grass/rock.
These are 2.5D art test images, NOT seamless-accepted Android game assets.
"""
from pathlib import Path
from PIL import Image,ImageDraw,ImageChops
import importlib.util,hashlib,json,math,random

ROOT=Path(__file__).resolve().parent
HEIGHT_SOURCE=ROOT.parent/"map-005-height-faces"/"generate.py"
spec=importlib.util.spec_from_file_location("map005_face_source",HEIGHT_SOURCE)
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
STEP=mod.STEP
SIDES=("E","S")
MATERIALS=("grass","rock")
V=mod.V

def shoreline(side,level,material):
    im=mod.paint(side,level,material)
    w,h=im.size
    scale=4
    overlay=Image.new("RGBA",(w*scale,h*scale))
    draw=ImageDraw.Draw(overlay)
    (ax,ay),(bx,by)=V[side]
    depth=level*STEP
    seed=7919+level*101+int(side=="S")*1229+int(material=="rock")*461
    rng=random.Random(seed)
    # Narrow foam rim at the bottom of the exposed face, not a new
    # pseudo-ground diamond. Endpoint offsets are zero: adjoining
    # tile corners continue at exact 128x64 geometric anchors.
    pts=[]
    for i in range(65):
        t=i/64
        x=ax+(bx-ax)*t
        wobble=math.sin(math.pi*t)*(1.25*math.sin(t*math.pi*7+.5)
                                     +.55*math.sin(t*math.pi*13))
        y=ay+(by-ay)*t+depth+wobble
        pts.append((round(x*scale),round(y*scale)))
    draw.line(pts,fill=(214,226,208,205),width=8)
    draw.line([(x,y+3) for x,y in pts],fill=(159,204,192,106),width=12)
    for j in range(12):
        t=rng.uniform(.07,.93)
        i=round(t*64)
        x,y=pts[i]
        rx=rng.randint(2,5)*scale//3
        ry=rng.randint(1,2)*scale//2
        draw.ellipse((x-rx,y-ry,x+rx,y+ry),
                     fill=(216,225,206,rng.randint(90,170)))
    # Composition over an original face; the shore is translucent,
    # keeping all pixels outside the cliff-face bounds transparent.
    rim=overlay.resize((w,h),Image.Resampling.LANCZOS)
    combined=Image.alpha_composite(im,rim)
    return combined

def main():
    out=ROOT/"water_cliff_png"
    out.mkdir(exist_ok=True)
    manifest={
        "schemaVersion":1,"family":"map005_cliff_water_intersection_v1",
        "status":"TECHNICAL ART CANDIDATE; NOT SEAMLESS OR ANDROID APPROVED",
        "geometry":{"worldCols":512,"worldRows":512,"tileWidthPx":128,
                    "tileHeightPx":64,"tileAnchor":[64,32],
                    "cameraZoom":1.2,"heightStepPx":STEP},
        "layerOrder":["ground","water","cliff","scenery","fog"],
        "rules":["Only side E/S with a water neighbor; cliff height 1..5",
                 "Do not overlay a second ordinary E/S face",
                 "Foam is a visual candidate, not a collision/water simulation",
                 "Clip in Android against the full fog outline"],
        "limitations":["No mixed cliff-water E/S corners",
                       "No diagonal water neighbors or estuary confluence",
                       "No human visual seamless approval"],"assets":[]
    }
    sheet=Image.new("RGB",(960,1260),(228,233,224))
    for i,(side,level,material) in enumerate(
        (s,l,m) for s in SIDES for l in range(1,6) for m in MATERIALS):
        png=shoreline(side,level,material)
        name=f"cliff_water_{side.lower()}_h{level}_{material}.png"
        file=out/name
        png.save(file,optimize=True)
        manifest["assets"].append({
            "id":file.stem,"path":str(file.relative_to(ROOT)),
            "widthPx":png.width,"heightPx":png.height,
            "anchorX":64,"anchorY":32,
            "heightLevel":level,"heightStepPx":STEP,
            "footprintCols":1,"footprintRows":1,
            "side":side,"material":material,"neighborType":"water",
            "sortFootY":64+STEP*level,"layer":"cliff",
            "productionApproved":False,
            "sha256":hashlib.sha256(file.read_bytes()).hexdigest()
        })
        x=16+(i%4)*237
        y=12+(i//4)*244
        panel=Image.new("RGBA",(222,226),(221,230,223,255))
        d=ImageDraw.Draw(panel)
        d.polygon([(110,32),(175,65),(110,97),(45,65)],
                  fill=(132,177,112,255))
        d.polygon([(110,97),(175,65),(175,100),(110,134)],
                  fill=(33,133,157,255))
        panel.alpha_composite(png,(44,32))
        d.text((10,194),name.replace(".png",""),fill=(39,51,46,255))
        sheet.paste(panel.convert("RGB"),(x,y))
    (ROOT/"manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
    sheet.save(ROOT/"preview_20_water_cliffs.png")
    print("20 water-cliff candidates generated; artistic seamless QA pending")

if __name__=="__main__":
    main()
