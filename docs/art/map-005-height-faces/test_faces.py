#!/usr/bin/env python3
"""Validate all heights (1-5), side faces and equal-height ES corners."""
import hashlib,json
from pathlib import Path
from PIL import Image
from generate import paint,STEP
p=Path(__file__).resolve().parent
m=json.loads((p/'manifest.json').read_text())
assert len(m['assets'])==30
assert m['geometry']['heightStepPx']==13
assert m['geometry']['tileWidthPx']==128
assert m['geometry']['tileHeightPx']==64
assert m['geometry']['tileAnchor']==[64,32]
assert m['geometry']['zoom']==1.2
seen=set()
for a in m['assets']:
    f=p/a['path'];png=Image.open(f)
    assert png.mode=='RGBA'
    assert a['heightLevel'] in range(1,6)
    assert png.size==(128,64+a['heightLevel']*STEP+2)
    assert (a['anchorX'],a['anchorY'])==(64,32)
    assert hashlib.sha256(f.read_bytes()).hexdigest()==a['sha256']
    side=a['visibleSide']
    assert side in ('E','S','ES')
    if side=='ES':
        assert a['junction']=='equal_height_E_S'
        expected=Image.alpha_composite(
            paint('S',a['heightLevel'],a['material']),
            paint('E',a['heightLevel'],a['material']))
        # Corner pixel is shared by both edges and MUST be non-transparent.
        # Neighbor faces from different heights are not implied compatible.
        assert png.getchannel('A').getpixel((64,64+6))>0
    else:
        assert 'junction' not in a
        expected=paint(side,a['heightLevel'],a['material'])
    assert png.tobytes()==expected.tobytes()
    assert png.getchannel('A').getextrema()[0]==0
    assert png.getchannel('A').getextrema()[1]>0
    seen.add((side,a['heightLevel'],a['material']))
assert len(seen)==30
assert len([a for a in m['assets'] if a['visibleSide']=='ES'])==10
print('PASS 30 deterministic RGBA cliff assets: 20 sides + 10 equal-height ES corners')
