#!/usr/bin/env python3
"""Unit test MAP-005 optional intake: 8 macro PNGs never replace terrain.
Runs with Pillow and temporary test artwork, no real user art is required.
"""
from __future__ import annotations
import hashlib
import io
import json
import pathlib
import tempfile
import zipfile
from PIL import Image
from stage_map005_macros import stage

IDS=["slope_grass_01","slope_rock_01","riverbank_curve_01",
     "coast_rock_01","mountain_range_01","ridge_low_01",
     "natural_cave_02","forest_mix_01"]

def test_stage():
    with tempfile.TemporaryDirectory() as base:
        base=pathlib.Path(base)
        target=base/"map";target.mkdir()
        original={"schemaVersion":1,
            "geometry":{"worldCols":512,"worldRows":512,
                        "tileWidthPx":128,"tileHeightPx":64,
                        "tileAnchor":[64,32],"cameraZoom":1.2},
            "assets":[{"id":"ground_grass_01","path":"ground/ground_grass_01.png"}]}
        (target/"manifest.json").write_text(json.dumps(original))
        zip_path=base/"input.zip"
        meta={"geometry":{"worldCols":512,"worldRows":512,
             "tileWidthPx":128,"tileHeightPx":64,"tileAnchor":[64,32],
             "cameraZoom":1.2,"worldRotation":False},"assets":[]}
        with zipfile.ZipFile(zip_path,"w") as z:
            for i,aid in enumerate(IDS):
                im=Image.new("RGBA",(10+i,12+i),(0,0,0,0))
                im.putpixel((4,4),(100,130,80,255))
                b=io.BytesIO()
                im.save(b,format="PNG")
                buf=b.getvalue()
                path="sprites/"+aid+".png"
                z.writestr(path,buf)
                meta["assets"].append({
                    "id":aid,"path":path,"widthPx":im.width,
                    "heightPx":im.height,"anchorX":4,"anchorY":8,
                    "footprintCols":2,"footprintRows":2,"sortFootY":8,
                    "approvedVisualStyle":True,"productionApproved":False,
                    "seamlessTile":False,"anchorVerifiedOnAndroid":False,
                    "version":"test","variant":"01","license":"original for KOPANKA",
                    "sha256":hashlib.sha256(buf).hexdigest()})
            z.writestr("manifest.json",json.dumps(meta))
        stage(zip_path,target)
        after=json.loads((target/"manifest.json").read_text())
        assert len(after["assets"])==9
        assert after["assets"][0]==original["assets"][0]
        assert {x["id"] for x in after["assets"][1:]}=={"map005_"+i for i in IDS}
        assert all(x["layer"]=="scenery" for x in after["assets"][1:])
        for aid in IDS:
            assert (target/"map005_macro"/(aid+".png")).is_file()
        rep=json.loads((target/"map005_macro_staging_report.json").read_text())
        assert rep["enabledInMapSurface"] is False
        # Safety: reject a zip that silently declares unfinished sprites as finished.
        bad=base/"bad.zip"
        with zipfile.ZipFile(zip_path) as zin,zipfile.ZipFile(bad,"w") as zout:
            for name in zin.namelist():
                if name=="manifest.json":
                    badmeta=json.loads(zin.read(name))
                    badmeta["assets"][0]["productionApproved"]=True
                    zout.writestr(name,json.dumps(badmeta))
                else:
                    zout.writestr(name,zin.read(name))
        invalid=base/"bad_target"; invalid.mkdir()
        (invalid/"manifest.json").write_text(json.dumps(original))
        try:
            stage(bad,invalid)
        except AssertionError:
            pass
        else:
            raise AssertionError("Unapproved macro package passed intake")
        assert not (invalid/"map005_macro").exists()
        print("PASS MAP-005 intake: 8 PNG, geometry, SHA256, safe fallback, invalid-package rejection")

if __name__=="__main__":
    test_stage()
