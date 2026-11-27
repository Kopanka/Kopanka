#!/usr/bin/env python3
"""KOPANKA MAP-005: validate an external approved-style PNG macro art ZIP.

Usage: python3 tools/validate_map005_art_zip.py /path/to/KOPANKA_MAP005_art_handoff.zip
This does NOT declare the sprites production-ready or seamless. Art ingestion
must preserve the approved 512x512, 128x64, fixed 1.2x geometry contract.
"""
import hashlib
import io
import json
import pathlib
import sys
import zipfile
from PIL import Image

EXPECTED={"slope_grass_01","slope_rock_01","riverbank_curve_01",
          "coast_rock_01","mountain_range_01","ridge_low_01",
          "natural_cave_02","forest_mix_01"}
def validate(archive):
    with zipfile.ZipFile(archive) as z:
        files=set(z.namelist())
        assert "manifest.json" in files, "missing manifest"
        m=json.loads(z.read("manifest.json"))
        g=m["geometry"]
        assert (g["worldCols"],g["worldRows"])==(512,512)
        assert (g["tileWidthPx"],g["tileHeightPx"])==(128,64)
        assert g["tileAnchor"]==[64,32]
        assert g["cameraZoom"]==1.2
        assert g["worldRotation"] is False
        assert len(m["assets"])==8
        assert {a["id"] for a in m["assets"]}==EXPECTED
        for a in m["assets"]:
            path=a["path"]
            assert not pathlib.PurePosixPath(path).is_absolute()
            assert ".." not in pathlib.PurePosixPath(path).parts
            assert path in files, (a["id"],"not in ZIP")
            binary=z.read(path)
            assert hashlib.sha256(binary).hexdigest()==a["sha256"],a["id"]
            im=Image.open(io.BytesIO(binary))
            assert im.mode=="RGBA" and im.size==(a["widthPx"],a["heightPx"])
            assert im.getchannel("A").getextrema()==(0,255),a["id"]
            assert 0<=a["anchorX"]<=im.width
            assert 0<=a["anchorY"]<=im.height
            assert a["footprintCols"]>=1 and a["footprintRows"]>=1
            # High-resolution, self-contained objects are NEVER interchangeable
            # with 128x64 terrain and cannot be repeated without seam analysis.
            assert a["seamlessTile"] is False
            assert a["productionApproved"] is False
            assert a["approvedVisualStyle"] is True
            assert a["anchorVerifiedOnAndroid"] is False
    return m
if __name__=="__main__":
    if len(sys.argv)!=2:
        sys.exit("Usage: validate_map005_art_zip.py <zip-path>")
    m=validate(sys.argv[1])
    print("PASS:",len(m["assets"]),"approved-style RGBA macros; geometry, SHA256, transparency")
    print("BLOCKED: no seamless terrain/height-aware coast nor physical Android art approval")
