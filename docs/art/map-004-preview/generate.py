from pathlib import Path
from PIL import Image, ImageDraw
import cairosvg, random, json, hashlib, zipfile

ROOT = Path(__file__).resolve().parent
SVG = ROOT / "source_svg"
PNG = ROOT / "png"
SVG.mkdir(exist_ok=True)
PNG.mkdir(exist_ok=True)
assets = []
LICENSE = "Original artwork for KOPANKA, created for this project; project use, modification and distribution permitted"

def save(asset_id, svg, layer, anchor=(64, 32), foot=32, mask="", notes=""):
    source = asset_id + ".svg"
    (SVG / source).write_text(svg, encoding="utf8")
    png = asset_id + ".png"
    cairosvg.svg2png(bytestring=svg.encode(), write_to=str(PNG / png))
    im = Image.open(PNG / png)
    assert im.mode == "RGBA" and im.getbbox(), asset_id
    w, h = im.size
    assets.append(dict(id=asset_id, path="png/" + png, widthPx=w,
        heightPx=h, footprintCols=1, footprintRows=1,
        anchorX=anchor[0], anchorY=anchor[1], layer=layer,
        sortFootY=foot, adjacencyMask=mask, variant=asset_id.split("_")[-1],
        version="0.1.0-preview", license=LICENSE, notes=notes,
        editableSource="source_svg/" + source,
        sha256=hashlib.sha256((PNG / png).read_bytes()).hexdigest()))

def svg0(w, h, inner):
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">{inner}</svg>'

for key, points, mask in [
    ("n", "64,0 128,32 64,64 0,32", "N"),
    ("e", "128,32 64,64 64,75 128,43", "E"),
    ("s", "64,64 0,32 0,43 64,75", "S"),
    ("w", "0,32 64,0 64,13 0,45", "W"),
]:
    for variant in (1, 2):
        rng = random.Random(500 + variant*17 + ord(key))
        c = "#80966a" if variant == 1 else "#9b9d75"
        base = f'<polygon points="{points}" fill="{c}" opacity="0.9"/>'
        for _ in range(18):
            x, y = rng.uniform(8,119), rng.uniform(15,62)
            rx, ry = rng.uniform(2,9), rng.uniform(.45,2.2)
            color = rng.choice(("#5f7650","#bac092","#d1bd90"))
            base += f'<ellipse cx="{x:.1f}" cy="{y:.1f}" rx="{rx:.1f}" ry="{ry:.1f}" fill="{color}" opacity="{rng.uniform(.11,.31):.2f}"/>'
        save(f"hill_{key}_{variant:02d}", svg0(128,80,base), "slope",
             (64,32), 32, mask, "Low-gradient artist-preview; requires Android seam QA")

for direction in ("e", "s"):
    for level in (1,2):
        depth = level*13
        for variant in (1,2):
            rng = random.Random(ord(direction)*181+level*33+variant)
            if direction == "e":
                top = [(128,32),(64,64)]
                bottom = [(128,32+depth),(64,64+depth)]
                base = "#978978" if variant == 1 else "#858d80"
            else:
                top = [(64,64),(0,32)]
                bottom = [(64,64+depth),(0,32+depth)]
                base = "#7e6e62" if variant == 1 else "#718073"
            poly = " ".join(f"{x},{y}" for x,y in top+bottom[::-1])
            inner = f'<polygon points="{poly}" fill="{base}"/>'
            inner += f'<defs><clipPath id="cl"><polygon points="{poly}"/></clipPath></defs><g clip-path="url(#cl)">'
            for _ in range(26):
                x, y = rng.uniform(-8,140), (32+depth/2)+rng.uniform(-17,40)
                length = rng.uniform(5,22)
                stroke = rng.choice(("#d8c3a4","#4d5b53","#c5c0a7","#74675d"))
                inner += f'<path d="M{x:.1f},{y:.1f} l{length:.1f},-{length*rng.uniform(.14,.32):.1f}" stroke="{stroke}" stroke-opacity="{rng.uniform(.14,.48):.2f}" stroke-width="{rng.uniform(.4,1.4):.1f}" fill="none"/>'
            inner += "</g>"
            save(f"cliff_{direction}_h{level}_{variant:02d}",
                 svg0(128,86,inner), "cliff", (64,32), 32, direction.upper(),
                 f"Front-facing {direction} cliff, visual depth {depth}px at 1x; no device acceptance")

peaks = [(46,64,37),(56,37,44),(63,51,25),(41,33,59),(58,69,28),(33,50,65)]
for vi, (left, middle, right) in enumerate(peaks,1):
    rng = random.Random(1245+vi*113)
    center = 64+rng.randrange(-8,9)
    footy = 119
    top = footy-max(left,middle,right)-rng.randrange(3,12)
    side1 = "#a3a79e" if vi%2 else "#939a99"
    side2 = "#4c6462" if vi%2 else "#50696b"
    pts = [(center-52,footy-6),(center-21,footy-middle),
           (center-7,footy-28),(center+6,top),(center+21,footy-right),
           (center+36,footy-28),(center+53,footy-3)]
    p = " ".join(f"{x},{y}" for x,y in pts)
    main = f'<ellipse cx="{center}" cy="{footy-3}" rx="49" ry="8" fill="#476c53" opacity=".19"/>'
    main += f'<polygon points="{p} {center+42},{footy} {center-39},{footy}" fill="{side1}"/>'
    main += f'<polygon points="{center+6},{top} {center+21},{footy-right} {center+53},{footy-3} {center+42},{footy} {center+1},{footy-5}" fill="{side2}"/>'
    main += f'<polygon points="{center-21},{footy-middle} {center-27},{footy-middle+19} {center-13},{footy-middle+10} {center-8},{footy-middle+23}" fill="#e2e3d9" opacity=".85"/>'
    main += f'<polygon points="{center+6},{top} {center-7},{top+20} {center+3},{top+16} {center+10},{top+29} {center+21},{top+24}" fill="#e8e7db"/>'
    main += f'<path d="M{center-35} {footy-5} L{center-20} {footy-middle+23} M{center+31} {footy-11} L{center+18} {footy-right+18}" stroke="#d3d0c2" stroke-width="1.4" stroke-opacity=".55" fill="none"/>'
    for _ in range(19):
        x, y = rng.randrange(center-43,center+40), rng.randrange(footy-45,footy)
        color = rng.choice(("#506a5f","#edeee2","#879890"))
        main += f'<circle cx="{x}" cy="{y}" r="{rng.uniform(.35,1.5):.1f}" fill="{color}" opacity=".45"/>'
    save(f"ridge_peak_{vi:02d}", svg0(128,132,main),
         "scenery", (64,119), 119, "", f"Variable mountain silhouette {vi}, artist preview")

for direction in ("e","s"):
    for variant in (1,2):
        if direction == "e":
            points, a = "128,32 64,64 64,78 128,46", (101,53)
        else:
            points, a = "0,32 64,64 64,78 0,46", (27,53)
        color = ("#b2ad87","#a6a786")[variant-1]
        base = f'<polygon points="{points}" fill="{color}" opacity=".85"/>'
        base += f'<path d="M{a[0]-19},{a[1]-4} Q{a[0]},{a[1]-9} {a[0]+19},{a[1]-3}" stroke="#c3bca0" stroke-width="2.6" stroke-opacity=".45" fill="none"/>'
        save(f"shore_{direction}_{variant:02d}", svg0(128,86,base),
             "coast", (64,32),32,direction.upper(),
             "Prototype water/land transition; 16 masks and corner variants still required")

manifest = {"schemaVersion":1, "assetPack":"KOPANKA-MAP-004-ART-PREVIEW",
    "version":"0.1.0-preview",
    "geometry":{"worldCols":512,"worldRows":512,"tileWidthPx":128,
                "tileHeightPx":64,"tileAnchor":[64,32],
                "cameraZoom":1.2,"heightStepPx":13},
    "licensing":LICENSE,"status":"visual candidate; not integrated, not QA approved",
    "assets":assets}
(ROOT / "manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf8")
thumb_w, thumb_h = 244,205
sheet = Image.new("RGB",(thumb_w*5,thumb_h*6),"#e9ede6")
d = ImageDraw.Draw(sheet)
for i,a in enumerate(assets):
    cx,cy=i%5,i//5
    x,y=cx*thumb_w,cy*thumb_h
    for gy in range(y+7,y+158,14):
        for gx in range(x+7,x+thumb_w-7,14):
            d.rectangle((gx,gy,gx+13,gy+13),
                fill="#e3e5de" if (gx+gy)//14%2 else "#f6f7f3")
    im=Image.open(PNG/(a["id"]+".png"))
    fac=min(1.85,190/max(im.size))
    im=im.resize((round(im.width*fac),round(im.height*fac)),
                 Image.Resampling.LANCZOS)
    sheet.paste(im,(x+(thumb_w-im.width)//2,y+9+(145-im.height)//2),im)
    d.text((x+12,y+161),a["id"],fill="#243138")
    d.text((x+12,y+180),
           f'{a["widthPx"]}x{a["heightPx"]} anchor {a["anchorX"]},{a["anchorY"]}',
           fill="#596769")
sheet.save(ROOT/"contact_sheet.png")
with zipfile.ZipFile(ROOT/"MAP-004-art-preview-v0.1.zip","w",zipfile.ZIP_DEFLATED) as z:
    for p in [*SVG.glob("*.svg"),*PNG.glob("*.png"),
              ROOT/"manifest.json",ROOT/"contact_sheet.png"]:
        z.write(p,p.relative_to(ROOT))
print("Generated",len(assets),"original PNG + SVG previews")
