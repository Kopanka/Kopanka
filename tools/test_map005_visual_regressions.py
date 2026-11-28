#!/usr/bin/env python3
"""MAP-005 regression guards for Android 0.3.14 visual fixes.
Source-structure checks catch accidental reintroduction of the old visual bugs;
they are NOT a substitute for raster or on-device acceptance.
"""
from __future__ import annotations
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/"prototype/android/app/src/main/java/com/kopanka/map"
ASSETS=ROOT/"prototype/android/app/src/main/assets/map"

class Map005VisualRegressions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source=(SRC/"MapSurface.java").read_text(encoding="utf8")
        cls.demo=json.loads((ASSETS/"demo/map_32x32.json").read_text(encoding="utf8"))
        cls.version=(ROOT/"prototype/android/app/build.gradle").read_text(encoding="utf8")

    def test_estuary_is_authored_sea_cell(self):
        end=self.demo["riverPath"][-1]
        self.assertEqual(end,{"col":24,"row":20})
        cell=self.demo["cells"][end["row"]][end["col"]]
        self.assertEqual(cell["terrain"],"sea")
        self.assertIn("Path mouth=new Path();",self.source)
        self.assertIn("canvas.drawPath(mouth,paint);",self.source)
        self.assertIn("float reach=36.0f*IsoCamera.ZOOM;",self.source)
        self.assertIn("paint.setStrokeCap(Paint.Cap.BUTT);",self.source)

    def test_low_banks_use_terrain_tints_not_platform_gray(self):
        self.assertIn("east == 1 && grassBank ? 0xFF9BB783",self.source)
        self.assertIn("south == 1 && grassBank ? 0xFF91AD7C",self.source)
        self.assertNotIn("east == 1 && grassBank ? 0xFF93AC7D",self.source)
        self.assertNotIn("south == 1 && grassBank ? 0xFF839E70",self.source)

    def test_fog_stays_opaque_and_macro_sprites_wait_for_exploration(self):
        self.assertIn("UNEXPLORED_FOG_COLOR",self.source)
        self.assertIn("canvas.drawPath(fogMask,paint);",self.source)
        self.assertIn("if (!world.inside(col+dx,row+dy)",self.source)
        self.assertIn("|| !fog.isExplored(col+dx,row+dy))",self.source)
        self.assertIn("map005PreviewObject(col,row,id)",self.source)

    def test_fixed_contract_and_version(self):
        camera=(SRC/"IsoCamera.java").read_text()
        self.assertIn("TILE_WIDTH = 128f, TILE_HEIGHT = 64f, ZOOM = 1.2f",camera)
        self.assertIn("versionCode 18",self.version)
        self.assertIn("0.3.14-map005-estuary-grading",self.version)

if __name__=="__main__":
    unittest.main(verbosity=2)
