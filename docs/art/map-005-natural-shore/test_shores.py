#!/usr/bin/env python3
"""Strict deterministic geometry QA for 16 MAP-005 shoreline PNG candidates."""
from pathlib import Path
import json,hashlib
from PIL import Image
from generate import paint

ROOT=Path(__file__).resolve().parent

def main():
    m=json.loads((ROOT/'manifest.json').read_text())
    assert len(m['assets'])==16
    assert m['geometry']=={
        'tileWidthPx':128,'tileHeightPx':64,'tileAnchor':[64,32],
        'worldCols':512,'worldRows':512,'cameraZoom':1.2}
    unique=set()
    for i,a in enumerate(m['assets']):
        assert a['adjacencyMask']==i
        path=ROOT/a['path']
        binary=path.read_bytes()
        assert hashlib.sha256(binary).hexdigest()==a['sha256']
        unique.add(binary)
        im=Image.open(path)
        assert im.mode=='RGBA' and im.size==(128,64)
        assert im.tobytes()==paint(i).tobytes(),f'not deterministic: {i}'
        alpha=im.getchannel('A')
        vmin,vmax=alpha.getextrema()
        assert vmin==0
        assert vmax==(0 if i==0 else 255), (i,vmax)
        assert alpha.getpixel((64,32))==0
        for y in range(64):
            for x in range(128):
                if abs(x-64)/64+abs(y-32)/32>1.08:
                    assert alpha.getpixel((x,y))==0,(i,x,y)
    assert len(unique)==16
    print('PASS: 16 distinct transparent deterministic iso masks, SHA256 and no outer bleed')
if __name__=='__main__':
    main()
