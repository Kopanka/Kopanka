#!/usr/bin/env python3
"""Integrity test of experimental height-aware E/S cliff PNGs."""
import json,hashlib
from pathlib import Path
from PIL import Image
from generate import paint
p=Path(__file__).resolve().parent
m=json.loads((p/'manifest.json').read_text())
assert len(m['assets'])==8
assert m['geometry']['heightStepPx']==13
assert m['geometry']['tileWidthPx']==128
assert m['geometry']['tileHeightPx']==64
assert m['geometry']['zoom']==1.2
seen=set()
for a in m['assets']:
    f=p/a['path'];png=Image.open(f)
    assert png.mode=='RGBA'
    assert png.size==(128,64+a['heightLevel']*13+2)
    assert (a['anchorX'],a['anchorY'])==(64,32)
    assert hashlib.sha256(f.read_bytes()).hexdigest()==a['sha256']
    assert png.tobytes()==paint(
        a['visibleSide'],a['heightLevel'],a['material']).tobytes()
    assert png.getchannel('A').getextrema()[0]==0
    assert png.getchannel('A').getextrema()[1]>0
    seen.add((a['visibleSide'],a['heightLevel'],a['material']))
assert len(seen)==8
print('PASS eight distinct height-aware deterministic RGBA faces')
