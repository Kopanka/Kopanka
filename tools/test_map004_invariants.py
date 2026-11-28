#!/usr/bin/env python3
"""MAP-004 regression invariants: run without Android SDK or extra dependencies."""
from __future__ import annotations

import json
import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "prototype/android/app/src/main/java/com/kopanka/map"
DEMO = ROOT / "prototype/android/app/src/main/assets/map/demo/map_32x32.json"


class Map004Invariants(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(DEMO.read_text(encoding="utf-8"))
        cls.renderer = (SRC / "MapSurface.java").read_text(encoding="utf-8")
        cls.camera = (SRC / "IsoCamera.java").read_text(encoding="utf-8")
        cls.fog = (SRC / "FogStore.java").read_text(encoding="utf-8")
        cls.gradle = (ROOT / "prototype/android/app/build.gradle").read_text(encoding="utf-8")

    def test_fixed_world_geometry_and_identity(self):
        self.assertIn("TILE_WIDTH = 128f, TILE_HEIGHT = 64f, ZOOM = 1.2f", self.camera)
        self.assertIn("public static final int SIZE = 512", (SRC / "WorldMap.java").read_text())
        self.assertIn("applicationId 'com.kopanka.maptest.stable'", self.gradle)
        self.assertIn("versionCode 19", self.gradle)

    def test_demo_river_is_one_continuous_connected_path(self):
        cells = self.data["cells"]
        self.assertEqual((self.data["width"], self.data["height"]), (32, 32))
        masks = (1, 2, 4, 8)
        opposite = (4, 8, 1, 2)
        dx, dy = (0, 1, 0, -1), (-1, 0, 1, 0)
        x, y, px, py = 5, 3, -1, -1
        route = []
        for _ in range(1024):
            cell = cells[y][x]
            self.assertTrue(cell["riverMask"])
            self.assertNotIn((x, y), route, "River route has a cycle")
            route.append((x, y))
            candidates = []
            for d, mask in enumerate(masks):
                if not (cell["riverMask"] & mask):
                    continue
                nx, ny = x + dx[d], y + dy[d]
                self.assertTrue(0 <= nx < 32 and 0 <= ny < 32)
                self.assertTrue(cells[ny][nx]["riverMask"] & opposite[d])
                if (nx, ny) != (px, py):
                    candidates.append((nx, ny))
            self.assertLessEqual(len(candidates), 1, "Route branches or doubles back")
            if not candidates:
                break
            px, py, (x, y) = x, y, candidates[0]
        self.assertEqual(route[0], (5, 3))
        self.assertEqual(route[-1], (24, 20))
        self.assertEqual(cells[y][x]["terrain"], "sea")
        self.assertEqual(len(route), 37)
        elevations = [cells[r][c]["elevation"] for c, r in route]
        self.assertTrue(all(a >= b for a, b in zip(elevations, elevations[1:])))

    def test_single_fog_pass_after_scenery(self):
        src = self.renderer
        self.assertIn("fogMask.reset()", src)
        self.assertIn("fogMask.setFillType(Path.FillType.WINDING)", src)
        self.assertIn("canvas.drawPath(fogMask,paint)", src)
        self.assertGreater(src.index("canvas.drawPath(fogMask,paint)"),
                           src.index("for(Sprite item:scenery)"))
        self.assertNotIn("drawFogDiamond(", src)
        self.assertIn("UNEXPLORED_FOG_COLOR = 0xFF3B3F42", src)
        self.assertIn("OUTSIDE_WORLD_COLOR = 0xFF3B3F42", src)
        # Terrain and scenery passes must check the exploration state first.
        self.assertGreaterEqual(src.count("if (!fog.isExplored(col,row)) continue;"), 3)
        self.assertIn("explored_v1", self.fog)

    def test_procedural_riverbank_height_grading_and_cache(self):
        elevation = (SRC / "ElevationMap.java").read_text(encoding="utf-8")
        self.assertIn("private final byte[] heightCache", elevation)
        self.assertIn("if (heightCache[index] != 0)", elevation)
        self.assertIn("heightCache[index] = (byte) (h + 1)", elevation)
        self.assertIn("if (nearestWater < 4) h = Math.min(h, 1 + nearestWater)", elevation)
        self.assertIn('DemoMap.Cell near = demo == null ? null : demo.at(nx, ny)', elevation)
        # The original, artist-authored demo heights must be returned unchanged.
        self.assertLess(elevation.index("if (c != null)"),
                        elevation.index("if (nearestWater < 4)"))

    def test_small_grass_banks_are_not_drawn_as_dark_cliffs(self):
        src = self.renderer
        faces = (SRC / "NaturalCliffFaces.java").read_text(encoding="utf-8")
        self.assertIn("boolean mountain = isMountainKind(terrainAt(col,row))", src)
        self.assertIn("if (east>0) naturalCliffs.draw(", src)
        self.assertIn("if (south>0) naturalCliffs.draw(", src)
        self.assertIn("faceColor=mountain", faces)
        self.assertIn("canvas.clipPath(face);", faces)

    def test_legacy_segment_seams_and_slope_bars_are_not_drawn(self):
        src = self.renderer
        self.assertNotIn('drawSprite(canvas,"slope_', src)
        self.assertNotIn('drawSprite(canvas,maskId("river"', src)
        self.assertIn("drawDemoRiver(canvas,w,h)", src)
        self.assertIn("paint.setStrokeJoin(Paint.Join.ROUND)", src)
        self.assertIn("Path water=new Path()", src)
        self.assertIn("if (coast!=0 && elevation.at(col,row)==0)", src)


if __name__ == "__main__":
    unittest.main()
