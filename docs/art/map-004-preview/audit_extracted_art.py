#!/usr/bin/env python3
"""Validate that extracted art candidates are not mistaken for seamless tile sprites.
Usage: python3 audit_extracted_art.py /path/to/art_candidates
This audit is intentionally separate from validated SVG preview CI; the eight
approved-style candidate PNGs must be physically supplied before running it.
"""
from pathlib import Path
import hashlib
import json
import sys
from PIL import Image

def audit(directory):
    root=Path(directory)
    m=json.loads((root/"manifest.json").read_text(encoding="utf8"))
    assert m["geometry"]["tileWidthPx"]==128
    assert m["geometry"]["tileHeightPx"]==64
    assert m["geometry"]["anchor"]==[64,32]
    assert m["geometry"]["scale"]==1.2
    assert len(m["assets"])==8
    out=[]
    for a in m["assets"]:
        im=Image.open(root/a["path"]).convert("RGBA")
        alpha=im.getchannel("A")
        w,h=im.size
        assert (w,h)==(a["widthPx"],a["heightPx"])
        assert alpha.getextrema()==(0,255)
        assert hashlib.sha256((root/a["path"]).read_bytes()).hexdigest()==a["sha256"]
        bbox=alpha.getbbox()
        # A scene sprite is not a terrain tile merely because its metadata
        # claims one footprint. Exact neighboring-edge pixel correspondence
        # must be proven independently for every adjacency mask and height.
        flag=("needs tile-to-tile adjacency variants" if
              a["layer"]=="landscape" else
              "requires footprint/Y-sort and occlusion verification")
        assert a["pixelGeometryApproved"] is False
        assert a["requiresSeamQA"] is True
        out.append(dict(id=a["id"],nativeSize=[w,h],
                        alphaBBox=list(bbox),anchor=[a["anchorX"],a["anchorY"]],
                        status="NOT PRODUCTION-READY",reason=flag))
    return {"count":len(out),"approvedArtDirection":True,
            "approvedGameplayPixelGeometry":False,
            "allAssets":[*out],
            "blockers":["N/E/S/W slopes and cliff side/corner masks",
                        "16-way coast/water + height transitions",
                        "terrain ground seamless tiling and river source/estuary",
                        "object footprint occlusion and fixed 1.2x Android verification"]}

if __name__=="__main__":
    folder=Path(sys.argv[1]) if len(sys.argv)>1 else Path(".")
    result=audit(folder)
    dest=folder/"production_readiness_audit.json"
    dest.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf8")
    print("PASS art candidate integrity. Production readiness: BLOCKED")
    print(dest)
