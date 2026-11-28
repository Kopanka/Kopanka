#!/usr/bin/env python3
"""MAP-005 cliff-water integrity test: generated pixels/metadata/geometry."""
import hashlib,json
from pathlib import Path
from PIL import Image
from generate import shoreline,STEP
root=Path(__file__).resolve().parent
m=json.loads((root/"manifest.json").read_text())
assert len(m["assets"])==20
assert m["geometry"]=={
 "worldCols":512,"worldRows":512,"tileWidthPx":128,
 "tileHeightPx":64,"tileAnchor":[64,32],
 "cameraZoom":1.2,"heightStepPx":13}
seen=set()
for a in m["assets"]:
    combo=(a["side"],a["heightLevel"],a["material"])
    assert combo not in seen
    seen.add(combo)
    assert a["side"] in ("E","S")
    assert a["material"] in ("grass","rock")
    assert a["heightLevel"] in range(1,6)
    assert a["productionApproved"] is False
    assert a["layer"]=="cliff"
    p=root/a["path"]
    binary=p.read_bytes()
    assert hashlib.sha256(binary).hexdigest()==a["sha256"]
    im=Image.open(p)
    assert im.mode=="RGBA" and im.size==(128,64+a["heightLevel"]*STEP+2)
    assert (a["anchorX"],a["anchorY"])==(64,32)
    assert im.tobytes()==shoreline(*combo).tobytes()
    alpha=im.getchannel("A")
    assert alpha.getextrema()[0]==0
    assert alpha.getextrema()[1]>0
    assert alpha.getpixel((0,0))==0
    assert alpha.getpixel((127,0))==0
assert len(seen)==20
print("PASS 20 deterministic cliff-water assets, dimensions/anchor/SHA/alpha")
print("NOT VERIFIED: photo-realism, seamless cliff-water pixels, flood maps, Android")
