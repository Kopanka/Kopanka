#!/usr/bin/env python3
"""Validate MAP-003 PNG handoff before Android integration. Python stdlib only."""
import json
import struct
import zlib
import sys
from pathlib import Path

PNG_SIGNATURE = bytes.fromhex("89504e470d0a1a0a")
FIELDS = ("id", "path", "widthPx", "heightPx", "anchorX", "anchorY",
          "footprintCols", "footprintRows", "layer", "sortFootY", "version", "license")
LAYERS = {"ground", "slope", "coast", "water", "river", "scenery", "structure", "fog"}
MAX_PNG_BYTES = 64 * 1024 * 1024
MAX_CHUNK_BYTES = 32 * 1024 * 1024


def check_png(image, expected_width, expected_height):
    """Validate PNG chunk structure + CRC without loading full pixel data in memory."""
    if image.stat().st_size > MAX_PNG_BYTES:
        raise ValueError("PNG exceeds 64 MiB")
    with image.open("rb") as png:
        if png.read(8) != PNG_SIGNATURE:
            raise ValueError("invalid PNG signature")
        seen_ihdr = seen_idat = seen_iend = False
        while True:
            raw_length = png.read(4)
            if len(raw_length) != 4:
                raise ValueError("truncated PNG (missing IEND)")
            (length,) = struct.unpack(">I", raw_length)
            kind = png.read(4)
            if len(kind) != 4 or length > MAX_CHUNK_BYTES:
                raise ValueError("invalid PNG chunk header or length")
            if not seen_ihdr and (kind != b"IHDR" or length != 13):
                raise ValueError("PNG must begin with 13-byte IHDR")
            if kind == b"IHDR":
                if seen_ihdr or length != 13:
                    raise ValueError("duplicate or malformed IHDR")
                seen_ihdr = True
            if kind == b"IDAT":
                seen_idat = True
            if kind == b"IEND":
                if length != 0 or seen_iend or not seen_idat:
                    raise ValueError("invalid PNG IEND or missing IDAT")
                seen_iend = True
            checksum = zlib.crc32(kind)
            first_bytes = bytearray()
            remaining = length
            while remaining:
                data = png.read(min(remaining, 65536))
                if not data:
                    raise ValueError("truncated PNG chunk")
                checksum = zlib.crc32(data, checksum)
                if kind == b"IHDR":
                    first_bytes.extend(data)
                remaining -= len(data)
            stored_crc = png.read(4)
            if len(stored_crc) != 4 or struct.unpack(">I", stored_crc)[0] != checksum & 0xFFFFFFFF:
                raise ValueError("PNG chunk CRC mismatch")
            if kind == b"IHDR":
                width, height = struct.unpack(">II", first_bytes[:8])
                if (width, height) != (expected_width, expected_height):
                    raise ValueError("PNG size and manifest dimensions disagree")
                bit_depth, color_type, compression, filtering, interlace = first_bytes[8:]
                if (bit_depth, color_type) not in ((8, 2), (8, 6), (8, 0), (8, 4),
                                                    (16, 2), (16, 6), (16, 0), (16, 4), (8, 3)):
                    raise ValueError("unsupported PNG color format")
                if compression != 0 or filtering != 0 or interlace not in (0, 1):
                    raise ValueError("unsupported PNG header options")
            if seen_iend:
                if png.read(1):
                    raise ValueError("unexpected data after IEND")
                return





def number(asset, field, minimum, maximum):
    value = asset[field]
    if type(value) is not int or not minimum <= value <= maximum:
        raise ValueError(f"{field} must be an integer in [{minimum}, {maximum}]")
    return value


def check(path):
    root = path.resolve().parent
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if type(manifest) is not dict or manifest.get("schemaVersion") != 1:
        raise ValueError("schemaVersion must equal 1")
    assets = manifest.get("assets")
    if type(assets) is not list or not 0 < len(assets) <= 4096:
        raise ValueError("assets must be a nonempty list of at most 4096 entries")
    seen = set()
    for idx, asset in enumerate(assets):
        try:
            if type(asset) is not dict:
                raise ValueError("not an object")
            for field in FIELDS:
                if field not in asset:
                    raise ValueError(f"missing {field}")
            identity = asset["id"]
            if type(identity) is not str or not identity.strip() or identity in seen:
                raise ValueError("empty or duplicate asset id")
            seen.add(identity)
            filename = asset["path"]
            if type(filename) is not str or not filename.endswith(".png"):
                raise ValueError("path must be a PNG")
            if filename.startswith("/") or "\\" in filename or ":" in filename:
                raise ValueError("unsafe asset path")
            relative = Path(filename)
            if ".." in relative.parts or "." in relative.parts:
                raise ValueError("unsafe path segment")
            image = (root / relative).resolve()
            if not image.is_relative_to(root) or not image.is_file():
                raise ValueError("PNG missing or outside the map asset directory")
            w, h = number(asset, "widthPx", 1, 8192), number(asset, "heightPx", 1, 8192)
            ax, ay = number(asset, "anchorX", 0, w), number(asset, "anchorY", 0, h)
            cw, ch = number(asset, "footprintCols", 1, 64), number(asset, "footprintRows", 1, 64)
            layer = asset["layer"]
            if type(layer) is not str or layer not in LAYERS:
                raise ValueError("unrecognized layer")
            if layer == "ground" and (cw, ch) == (1, 1) and (w, h, ax, ay) != (128, 64, 64, 32):
                raise ValueError("ground 1x1 must be 128x64, anchor (64,32)")
            for field in ("version", "license"):
                if type(asset[field]) is not str or not asset[field].strip():
                    raise ValueError(f"missing {field}")
            y = asset["sortFootY"]
            if type(y) not in (int, float) or not -1000000 <= y <= 1000000:
                raise ValueError("invalid sortFootY")
            for optional in ("variant", "adjacencyMask"):
                if optional in asset and type(asset[optional]) is not str:
                    raise ValueError(f"{optional} must be a string")
            check_png(image, w, h)
        except (ValueError, OSError, TypeError) as e:
            raise ValueError(f"assets[{idx}]: {e}") from e
    return len(assets)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: validate_map_assets.py <path/to/map/manifest.json>", file=sys.stderr)
        sys.exit(2)
    try:
        count = check(Path(sys.argv[1]))
        print(f"MAP-003: validated {count} asset entries")
    except (ValueError, OSError, json.JSONDecodeError) as e:
        print(f"MAP-003 validation FAILED: {e}", file=sys.stderr)
        sys.exit(1)
