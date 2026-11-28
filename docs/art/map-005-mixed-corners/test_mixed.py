#!/usr/bin/env python3
"""MAP-005: deterministic exact verification of 90 mixed E/S corners."""
import hashlib
import json
from pathlib import Path
from PIL import Image
from generate import compose,candidates,STEP
p=Path(__file__).resolve().parent
m=json.loads((p/"manifest.json").read_text())
expected=list(candidates())
assert len(expected)==90,len(expected)
assert len(m["assets"])==90,len(m["assets"])
assert m["geometry"]=={
    "worldCols":512,"worldRows":512,
    "tileWidthPx":128,"tileHeightPx":64,
    "tileAnchor":[64,32],"zoom":1.2,"heightStepPx":13
}
observed=set()
for a in m["assets"]:
    eh,sh=a["eastHeight"],a["southHeight"]
    em,sm=a["eastMaterial"],a["southMaterial"]
    combo=(eh,sh,em,sm)
    assert combo not in observed,combo
    observed.add(combo)
    assert combo in expected
    assert eh!=sh or em!=sm
    file=p/a["path"]
    raw=file.read_bytes()
    assert hashlib.sha256(raw).hexdigest()==a["sha256"],combo
    image=Image.open(file)
    assert image.mode=="RGBA"
    assert image.size==(128,64+max(eh,sh)*STEP+2)
    assert (a["anchorX"],a["anchorY"])==(64,32)
    assert a["layer"]=="cliff"
    assert a["productionApproved"] is False
    assert image.tobytes()==compose(*combo).tobytes(),combo
    assert image.getchannel("A").getextrema()[0]==0
    assert image.getchannel("A").getextrema()[1]>0
    assert image.getchannel("A").getpixel((0,0))==0
    assert image.getchannel("A").getpixel((127,0))==0
assert observed==set(expected)
print("PASS: 90 unique, deterministic mixed corners; SHA256, geometry, transparency")
print("ART QA PENDING: mixed-height shared edges and material transitions are not certified seamless")
