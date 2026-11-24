#!/usr/bin/env python3
"""Validate MAP-003 PNG handoff before Android integration. Python stdlib only."""
import json
import struct
import sys
from pathlib import Path

PNG_SIGNATURE = bytes.fromhex("89504e470d0a1a0a")
FIELDS = ("id", "path", "widthPx", "heightPx", "anchorX", "anchorY",
          "footprintCols", "footprintRows", "layer", "sortFootY", "version", "license")
LAYERS = {"ground", "slope", "coast", "water", "river", "scenery", "structure", "fog"}


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
            with image.open("rb") as png:
                header = png.read(26)
            if len(header) < 26 or header[:8] != PNG_SIGNATURE or header[12:16] != b"IHDR":
                raise ValueError("invalid PNG header")
            if struct.unpack(">I", header[8:12])[0] != 13:
                raise ValueError("invalid IHDR length")
            if struct.unpack(">II", header[16:24]) != (w, h):
                raise ValueError("PNG size and manifest dimensions disagree")
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
