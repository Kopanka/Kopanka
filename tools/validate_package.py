#!/usr/bin/env python3
"""Self-contained strict PNG structure and geographic topology validator."""
from pathlib import Path
import json, struct, zlib, sys
from PIL import Image
ROOT=Path(__file__).resolve().parent.parent
MAP=ROOT/'prototype/android/app/src/main/assets/map'
manifest=json.loads((MAP/'manifest.json').read_text(encoding='utf-8'))
assert manifest['schemaVersion']==1
assert manifest['geometry']=={'worldCols':512,'worldRows':512,'tileWidthPx':128,'tileHeightPx':64,'tileAnchor':[64,32],'cameraZoom':1.2}
assets=manifest['assets']; ids=set(); fails=[]
for a in assets:
 try:
  assert a['id'] not in ids
  ids.add(a['id'])
  rel=Path(a['path']); assert not rel.is_absolute() and '..' not in rel.parts
  path=MAP/rel; src=ROOT/'source_svg'/rel.with_suffix('.svg')
  assert path.is_file() and src.is_file()
  assert src.read_text().startswith('<svg')
  assert a['version'] and a['license']
  assert a['layer'] in {'ground','slope','coast','water','river','scenery','structure','fog'}
  assert all(type(a[k]) is int for k in ('widthPx','heightPx','anchorX','anchorY','footprintCols','footprintRows'))
  assert 0<=a['anchorX']<=a['widthPx'] and 0<=a['anchorY']<=a['heightPx']
  if a['layer']=='ground':assert (a['widthPx'],a['heightPx'],a['anchorX'],a['anchorY'])==(128,64,64,32)
  data=path.read_bytes();assert data[:8]==bytes.fromhex('89504e470d0a1a0a')
  i=8
  while i<len(data):
   ln=struct.unpack('>I',data[i:i+4])[0];chunk_type=data[i+4:i+8];d=data[i+8:i+8+ln];crc=struct.unpack('>I',data[i+8+ln:i+12+ln])[0]
   assert zlib.crc32(chunk_type+d)&0xffffffff==crc
   i+=12+ln
   if chunk_type==b'IEND':break
  assert i==len(data)
  with Image.open(path) as im:
   assert im.mode=='RGBA' and im.size==(a['widthPx'],a['heightPx'])
 except Exception as e:fails.append((a.get('id'),str(e)))
assert not fails, fails
assert all(f'river_mask_{m:02}' in ids and f'coast_mask_{m:02}' in ids for m in range(1,16))
assert all('coast_corner_'+d in ids for d in ('ne','se','sw','nw'))
scene=json.loads((ROOT/'demo/map_32x32.json').read_text())
assert scene['width']==scene['height']==32
cells=scene['cells'];assert len(cells)==32 and all(len(r)==32 for r in cells)
route=[(p['col'],p['row']) for p in scene['riverPath']];assert len(route)==len(set(route))
assert len(route)>20
bits={(0,-1):1,(1,0):2,(0,1):4,(-1,0):8}
for i,(c,r) in enumerate(route):
 expected=0
 for nc,nr in route[max(0,i-1):i]+route[i+1:i+2]:
  dc,dr=nc-c,nr-r
  assert (dc,dr) in bits
  expected|=bits[(dc,dr)]
 assert cells[r][c]['riverMask']==expected,('riverMask',c,r,expected,cells[r][c]['riverMask'])
for r,row in enumerate(cells):
 for c,cell in enumerate(row):
  assert cell['terrain'] in ('sea','mountain','grass','meadow')
  if cell['terrain']!='sea':
   expected=0
   for (dc,dr),bit in bits.items():
    nc,nr=c+dc,r+dr
    if 0<=nc<32 and 0<=nr<32 and cells[nr][nc]['terrain']=='sea':expected|=bit
   assert cell['coastMask']==expected
  for obj in cell['objects']:assert obj in ids
placements={(o['id']):(o['col'],o['row']) for o in scene['objects']}
assert cells[placements['mine_mountain_small'][1]][placements['mine_mountain_small'][0]]['terrain']=='mountain'
assert cells[placements['quarry_plain_01'][1]][placements['quarry_plain_01'][0]]['terrain']!='mountain'
print(f'PASS {len(assets)} PNG CRC + RGBA + SVG; footprint; 32x32 cells; {len(route)} connected river cells; mine mountain/quarry plain; cardinal shores; diagonal assets')
