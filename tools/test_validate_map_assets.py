#!/usr/bin/env python3
"""MAP-003 validator regression tests using tiny generated PNG headers."""
import json
import struct
import zlib
import tempfile
import unittest
from pathlib import Path
from validate_map_assets import check, PNG_SIGNATURE


class ManifestTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "ground").mkdir()
        self.png = self.root / "ground" / "grass.png"
        header = struct.pack(">IIBBBBB", 128, 64, 8, 6, 0, 0, 0)
        pixels = (b"\\x00" + b"\\x00" * (128 * 4)) * 64
        def chunk(kind, body):
            checksum = zlib.crc32(body, zlib.crc32(kind)) & 0xffffffff
            return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", checksum)
        self.png.write_bytes(PNG_SIGNATURE + chunk(b"IHDR", header)
                             + chunk(b"IDAT", zlib.compress(pixels))
                             + chunk(b"IEND", b""))
        self.asset = dict(id="grass", path="ground/grass.png", widthPx=128, heightPx=64,
                          footprintCols=1, footprintRows=1, anchorX=64, anchorY=32,
                          layer="ground", sortFootY=32, version="1", license="artist-test")
        self.manifest = self.root / "manifest.json"

    def verify(self):
        self.manifest.write_text(json.dumps({"schemaVersion": 1, "assets": [self.asset]}))
        return check(self.manifest)

    def test_valid(self):
        self.assertEqual(self.verify(), 1)

    def test_bad_anchor(self):
        self.asset["anchorX"] = 60
        with self.assertRaisesRegex(ValueError, "128x64"):
            self.verify()

    def test_bad_dimensions(self):
        self.asset["widthPx"] = 129
        self.asset["layer"] = "scenery"
        with self.assertRaisesRegex(ValueError, "dimensions disagree"):
            self.verify()

    def test_missing_png(self):
        self.asset["path"] = "ground/missing.png"
        with self.assertRaisesRegex(ValueError, "PNG missing"):
            self.verify()

    def test_path_escape(self):
        self.asset["path"] = "../evil.png"
        with self.assertRaisesRegex(ValueError, "unsafe path"):
            self.verify()

    def test_corrupt_png_crc(self):
        payload = bytearray(self.png.read_bytes())
        payload[29] ^= 1  # corrupt IHDR checksum
        self.png.write_bytes(payload)
        with self.assertRaisesRegex(ValueError, "CRC mismatch"):
            self.verify()

    def test_truncated_png(self):
        self.png.write_bytes(self.png.read_bytes()[:-12])  # remove IEND
        with self.assertRaisesRegex(ValueError, "IEND"):
            self.verify()

    def test_invalid_layer(self):
        self.asset["layer"] = "unapproved"
        with self.assertRaisesRegex(ValueError, "unrecognized layer"):
            self.verify()

    def test_fractional_anchor(self):
        self.asset["anchorX"] = 64.5
        with self.assertRaisesRegex(ValueError, "must be an integer"):
            self.verify()

    def test_duplicate_id(self):
        self.manifest.write_text(json.dumps({"schemaVersion": 1,
                                             "assets": [self.asset, self.asset]}))
        with self.assertRaisesRegex(ValueError, "duplicate asset id"):
            check(self.manifest)

    def test_wrong_schema(self):
        self.manifest.write_text(json.dumps({"schemaVersion": 2, "assets": [self.asset]}))
        with self.assertRaisesRegex(ValueError, "schemaVersion"):
            check(self.manifest)


if __name__ == "__main__":
    unittest.main()
