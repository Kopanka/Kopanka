#!/usr/bin/env python3
"""MAP-005: stage 8 visually approved macro sprite PNGs for Android.

Does not switch on their rendering. The natural artwork is NOT a seamless
terrain atlas, and must not replace 128x64 ground/coast tiles before art QA.

Usage:
 python3 tools/stage_map005_macros.py /path/to/KOPANKA_MAP005_art_handoff.zip \
     prototype/android/app/src/main/assets/map
"""
from __future__ import annotations
import hashlib
import io
import json
import pathlib
import shutil
import sys
import zipfile
from PIL import Image

EXPECTED={"slope_grass_01","slope_rock_01","riverbank_curve_01",
          "coast_rock_01","mountain_range_01","ridge_low_01",
          "natural_cave_02","forest_mix_01"}

def stage(archive, asset_root):
    root=pathlib.Path(asset_root)
    manifest_file=root/"manifest.json"
    current=json.loads(manifest_file.read_text(encoding="utf-8"))
    assert current["schemaVersion"]==1
    assert current["geometry"]["worldCols"]==512
    assert current["geometry"]["worldRows"]==512
    assert current["geometry"]["tileWidthPx"]==128
    assert current["geometry"]["tileHeightPx"]==64
    assert current["geometry"]["tileAnchor"]==[64,32]
    assert current["geometry"]["cameraZoom"]==1.2
    with zipfile.ZipFile(archive) as z:
        incoming=json.loads(z.read("manifest.json"))
        g=incoming["geometry"]
        assert (g["worldCols"],g["worldRows"])==(512,512)
        assert (g["tileWidthPx"],g["tileHeightPx"])==(128,64)
        assert g["tileAnchor"]==[64,32]
        assert g["cameraZoom"]==1.2 and g["worldRotation"] is False
        entries=incoming["assets"]
        assert len(entries)==8 and {a["id"] for a in entries}==EXPECTED
        index={}
        data={}
        for a in entries:
            aid=a["id"]
            name=a["path"]
            p=pathlib.PurePosixPath(name)
            assert not p.is_absolute() and ".." not in p.parts
            blob=z.read(name)
            assert hashlib.sha256(blob).hexdigest()==a["sha256"]
            im=Image.open(io.BytesIO(blob))
            assert im.mode=="RGBA" and im.size==(a["widthPx"],a["heightPx"])
            assert im.getchannel("A").getextrema()==(0,255)
            assert a["approvedVisualStyle"] is True
            assert a["productionApproved"] is False
            assert a["seamlessTile"] is False
            assert a["anchorVerifiedOnAndroid"] is False
            assert 0<=a["anchorX"]<=im.width
            assert 0<=a["anchorY"]<=im.height
            assert 1<=a["footprintCols"]<=4 and 1<=a["footprintRows"]<=4
            # An explicit macro prefix prevents accidental replacement of
            # the stable MAP-003 ground / coast / cave asset identifiers.
            new_id="map005_"+aid
            data[aid]=blob
            index[aid]={"id":new_id,
                        "path":"map005_macro/"+aid+".png",
                        "widthPx":a["widthPx"],"heightPx":a["heightPx"],
                        "footprintCols":a["footprintCols"],
                        "footprintRows":a["footprintRows"],
                        "anchorX":a["anchorX"],"anchorY":a["anchorY"],
                        # Macro landscape decals are scenery, NEVER 'ground'.
                        "layer":"scenery","sortFootY":a["sortFootY"],
                        "adjacencyMask":"","variant":a["variant"],
                        "version":a["version"],"license":a["license"]}
        previous={a["id"] for a in current["assets"]}
        assert not any(entry["id"] in previous for entry in index.values())
        # All source checks happen before the first write.
        dst=root/"map005_macro"
        dst.mkdir(parents=True,exist_ok=True)
        for aid,blob in data.items():
            (dst/(aid+".png")).write_bytes(blob)
        current["assets"].extend(index.values())
        current.setdefault("extensions",{})["map005_macros"]={
            "status":"STAGED ONLY; NOT SEAMLESS OR PHYSICALLY ART-APPROVED",
            "sourceSha256":hashlib.sha256(pathlib.Path(archive).read_bytes()).hexdigest(),
            "count":len(index)}
        manifest_file.write_text(json.dumps(current,ensure_ascii=False,indent=2)+"\n",
                                 encoding="utf-8")
        (root/"map005_macro_staging_report.json").write_text(
            json.dumps({"staged":sorted(index),"stagedAssetIds":sorted(x["id"] for x in index.values()),
                        "enabledInMapSurface":False,
                        "pending":["height-aware shoreline/cliffs",
                                   "artist 32x32 composition signoff",
                                   "Android fog/Y-sort/performance QA"]},
                        ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        print("PASS: staged",len(index),"validated macro sprites; rendering is NOT enabled")

if __name__=="__main__":
    if len(sys.argv)!=3:
        sys.exit("Usage: stage_map005_macros.py SOURCE_ZIP TARGET_MAP_ASSET_DIRECTORY")
    stage(sys.argv[1],sys.argv[2])
