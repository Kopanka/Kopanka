import os,json,math,random,zipfile,shutil,sys
from pathlib import Path
from PIL import Image,ImageDraw,ImageEnhance
import cairosvg
ROOT=Path('/mnt/data/MAP-003-asset-pack-v1.3')
MAP=ROOT/'prototype/android/app/src/main/assets/map'
SRC=ROOT/'source_svg'; DEMO=ROOT/'demo'
for d in (MAP,SRC,DEMO): d.mkdir(parents=True,exist_ok=True)
assets=[]
random.seed(19)
DEF='''<defs>
<linearGradient id="grass" x1="0" y1="0" x2=".8" y2="1"><stop stop-color="#b2cc72"/><stop offset=".5" stop-color="#8eaf55"/><stop offset="1" stop-color="#70944a"/></linearGradient>
<linearGradient id="earth" x1="0" y1="0" x2=".8" y2="1"><stop stop-color="#c6ae72"/><stop offset="1" stop-color="#9f8355"/></linearGradient>
<linearGradient id="rock" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#cfccc0"/><stop offset=".5" stop-color="#8f9287"/><stop offset="1" stop-color="#555e5e"/></linearGradient>
<linearGradient id="sea" x1="0" y1="0" x2=".9" y2="1"><stop stop-color="#299eae"/><stop offset=".6" stop-color="#166d94"/><stop offset="1" stop-color="#125276"/></linearGradient>
<linearGradient id="river" x1="0" y1="0" x2="1" y2=".8"><stop stop-color="#55c5d3"/><stop offset=".7" stop-color="#268bac"/><stop offset="1" stop-color="#136282"/></linearGradient>
<clipPath id="diamond"><path d="M 64,0 L128,32 64,64 0,32Z"/></clipPath>
</defs>'''
def svg(w,h,body,extra=''):
 return f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">{DEF}{extra}{body}</svg>'
def save(id,category,body,w=128,h=64,ax=64,ay=32,layer='ground',mask='',variant='01',extra='',notes=''):
 content=svg(w,h,body,extra)
 folder=category; fname=id+'.png'; rel=f'{folder}/{fname}'
 (MAP/folder).mkdir(parents=True,exist_ok=True);(SRC/folder).mkdir(parents=True,exist_ok=True)
 (SRC/folder/(id+'.svg')).write_text(content,encoding='utf-8')
 cairosvg.svg2png(bytestring=content.encode(),write_to=str(MAP/rel),output_width=w,output_height=h)
 assets.append(dict(id=id,path=rel,widthPx=w,heightPx=h,footprintCols=1,footprintRows=1,anchorX=ax,anchorY=ay,layer=layer,sortFootY=ay,adjacencyMask=mask,variant=variant,version='1.3.0',license='Original work for KOPANKA; project use, modification and distribution permitted',notes=notes))
 return id
D='M64 -1L130 32 64 65 -2 32Z'
seed=lambda v: random.Random(v)
def specks(v, color='#58793b', n=18):
 r=seed(v); out=[]
 for _ in range(n):
  x=r.uniform(18,110); y=r.uniform(16,48)
  if abs(x-64)/64+abs(y-32)/32 > .72: continue
  a=r.choice([.3,.45,.6]); out.append(f'<path d="M{x:.1f} {y:.1f} l{r.uniform(1,3):.1f} {-r.uniform(.3,1.3):.1f}" stroke="{color}" opacity="{a}" stroke-width=".8" stroke-linecap="round"/>')
 return ''.join(out)
base_grass=f'<path d="{D}" fill="url(#grass)"/>'
for kind,clr in [('grass','#9dbb68'),('grass_light','#b5c985'),('meadow','#91b05a'),('earth','#ac965f'),('sand','#d8bd82')]:
 fill={'grass':'#91b366','grass_light':'#91b366','meadow':'#91b366','earth':'#91b366','sand':'#d4bd8b'}[kind]
 for v in range(1,4 if kind=='grass' else 2):
  pattern=f'<path d="{D}" fill="{fill}"/>' + ('<ellipse cx="69" cy="33" rx="41" ry="17" fill="#ad9e78" opacity=".65"/><ellipse cx="54" cy="27" rx="21" ry="9" fill="#c1ab86" opacity=".45"/>' if kind=='earth' else '')+specks(kind+str(v), '#416f35' if kind in ('grass','meadow','grass_light') else '#8e7750',27)
  if kind in ('grass','grass_light','meadow'):
   rr=seed(kind+str(v))
   for i in range(9):
    x=rr.uniform(24,103); y=rr.uniform(19,45)
    if abs(x-64)/64+abs(y-32)/32<.7:
     pattern+=f'<circle cx="{x:.1f}" cy="{y:.1f}" r=".8" fill="{rr.choice(["#e3d69c","#d9e5ac","#f1e6c6"])}" opacity=".75"/>'
  save(f'ground_{kind}_{v:02}', 'ground', pattern,layer='ground',variant=f'{v:02}')
# water tiles
for v in (1,2):
 body=f'<path d="{D}" fill="#187b9a"/>'
 r=seed('sea'+str(v))
 for i in range(15):
  x=r.randint(21,100); y=r.randint(19,46)
  if abs(x-64)/64+abs(y-32)/32<.77:
   body+=f'<path d="M{x} {y}q5 -1 10 0" fill="none" stroke="#b0e4db" stroke-width=".8" opacity=".38"/>'
 save(f'water_sea_{v:02}','water',body,layer='water',variant=f'{v:02}')
# Smooth topological river strips. Identical tangent, colour and width at both ends of each shared edge.
edge={'N':(96,16),'E':(96,48),'S':(32,48),'W':(32,16)}
def linegeom(a,b):
 x1,y1=edge[a]; x2,y2=edge[b]
 dx=x2-x1; dy=y2-y1
 # Bézier through the footprint center, softens right angle without offsetting shared-edge landings.
 return (f'M{x1} {y1} C{round(x1+(64-x1)*.72,2)} {round(y1+(32-y1)*.72,2)} '
         f'{round(x2+(64-x2)*.72,2)} {round(y2+(32-y2)*.72,2)} {x2} {y2}')
def river_path(mask):
 dirs=[k for i,k in enumerate('NESW') if mask&(1<<i)]
 if len(dirs)==1:
  x,y=edge[dirs[0]]; return f'M{x} {y} Q64 32 64 32'
 if len(dirs)==2:return linegeom(dirs[0],dirs[1])
 return ' '.join(f'M{x} {y} Q64 32 64 32' for k in dirs for x,y in [edge[k]])
for mask in range(1,16):
 dirs=''.join(k for i,k in enumerate('NESW') if mask&(1<<i))
 geom=river_path(mask)
 # Unbroken river banks and translucent strokes remain clipped to footprint.
 body=(f'<path d="{geom}" stroke="#bdc596" stroke-width="20" stroke-linejoin="round" stroke-linecap="round" fill="none"/>'
       f'<path d="{geom}" stroke="#257b9e" stroke-width="16" stroke-linejoin="round" stroke-linecap="round" fill="none"/>'
       f'<path d="{geom}" stroke="#54afc5" stroke-width="5" opacity=".45" stroke-linejoin="round" stroke-linecap="round" fill="none"/>')
 if len(dirs)>=3:body+='<circle cx="64" cy="32" r="9" fill="#2b8eaa"/>'
 save(f'river_mask_{mask:02}','river',f'<g clip-path="url(#diamond)">{body}</g>',layer='river',mask=dirs,variant=f'{mask:02}',notes='N=1 E=2 S=4 W=8; smooth Bézier centerline with fixed shared edge endpoints')
save('river_source','river','<g clip-path="url(#diamond)"><path d="M32 48 Q48 37 64 32" stroke="#bdc596" stroke-width="19" fill="none"/><path d="M32 48 Q48 37 64 32" stroke="#2987a6" stroke-width="13" fill="none"/><ellipse cx="64" cy="32" rx="8" ry="5" fill="#63bcce"/></g>',layer='river',mask='S',notes='Headwater endpoint; position relative to chosen outbound edge')
save('river_estuary','river','<g clip-path="url(#diamond)"><path d="M32 16 Q47 26 64 32" stroke="#c6c696" stroke-width="22" fill="none"/><path d="M32 16 Q47 26 64 32" stroke="#318ba7" stroke-width="16" fill="none"/><ellipse cx="64" cy="32" rx="16" ry="8" fill="#2a91ab" opacity=".8"/></g>',layer='river',mask='W',notes='Estuary overlay; should match actual incoming edge of river scene')
# coast masks: draw water wedge from each edge into interior; coast line smooth, edges constant at shared endpoint
for mask in range(1,16):
 dirs=''.join(k for i,k in enumerate('NESW') if mask&(1<<i))
 body=''
 for k in dirs:
  x,y=edge[k]
   # Continuous water strip along the shared diamond edge (same colour as sea ground).
  # A curved sand transition lies on the inland side; avoids a hard blue wedge.
  corners={'N':((64,0),(128,32)),'E':((128,32),(64,64)),
           'S':((64,64),(0,32)),'W':((0,32),(64,0))}
  a,b=corners[k]
  def pull(p,t): return (round(p[0]*(1-t)+64*t,2), round(p[1]*(1-t)+32*t,2))
  a1,b1=pull(a,.30),pull(b,.30)
  a2,b2=pull(a,.19),pull(b,.19)
  outline=lambda q:f'{q[0]} {q[1]}'
  body+=f'<polygon points="{outline(a)} {outline(b)} {outline(b1)} {outline(a1)}" fill="#d3c28e"/>'
  body+=f'<polygon points="{outline(a)} {outline(b)} {outline(b2)} {outline(a2)}" fill="#187b9a"/>'
  body+=f'<path d="M{outline(a2)} Q{outline(pull(a,.23))} {outline(pull(b,.18))}" stroke="#e6eee0" fill="none" stroke-width=".75" opacity=".35"/>'
 save(f'coast_mask_{mask:02}','coast',f'<g clip-path="url(#diamond)">{body}</g>',layer='coast',mask=dirs,variant=f'{mask:02}',notes='Coast sea-neighbor mask; corners require diagonal neighbor handling')
# Diagonal shore/corner inserts for island and cove transitions.
# These do not replace orthogonal coast masks; the Android renderer chooses them
# only if the diagonal neighbor is sea and both corresponding edge-neighbors land.
for name,pt in {'NE':(128,32),'SE':(64,64),'SW':(0,32),'NW':(64,0)}.items():
 x,y=pt
 cx,cy=64,32
 tipx=x*.75+cx*.25; tipy=y*.75+cy*.25
 body=(f'<g clip-path="url(#diamond)"><ellipse cx="{x}" cy="{y}" rx="23" ry="12" fill="#d3c28e" opacity=".9"/>'
       f'<ellipse cx="{x}" cy="{y}" rx="17" ry="8" fill="#187b9a"/>'
       f'<path d="M{tipx} {tipy} L{x} {y}" stroke="#dfebde" opacity=".6" stroke-width="1"/></g>')
 save('coast_corner_'+name.lower(),'coast',body,layer='coast',mask=name,variant='corner',notes='Diagonal sea-neighbor only; do not stack with sea along either adjacent cardinal edge')
# slope graphic overlay 128x64
for direction in ['N','E','S','W']:
 path={'N':'M64 2 104 21 64 38 24 21Z','E':'M124 32 84 13 55 31 84 49Z','S':'M64 62 24 43 64 25 104 43Z','W':'M4 32 44 13 73 31 44 49Z'}[direction]
 body=f'<path d="{path}" fill="#8f947d" opacity=".75"/><path d="{path}" fill="none" stroke="#b9b6a1" stroke-width="1.4" opacity=".7"/>'
 save(f'slope_{direction.lower()}','slope',body,layer='slope',mask=direction)
# sprites - arbitrary canvas sized; footpoint anchor always centered footprint world spot
# centered at lower sprite position (for mountain w=192 h=170 anchor 96,145)
def sprite(id,category,w,h,footx,footy,body,layer='scenery',notes=''):
 return save(id,category,body,w,h,footx,footy,layer,notes=notes)
def mountain(v=1):
 shift=5 if v==2 else 0
 return f'''<ellipse cx="96" cy="147" rx="71" ry="14" fill="#314c37" opacity=".24"/>
 <path d="M15 144 L28 117 37 119 57 67 66 72 76 {30+shift} 91 60 104 89 114 77 130 {44+shift} 142 70 153 69 171 111 186 145 165 154 141 148 119 155 96 147 72 153 45 144Z" fill="#686e6c"/>
 <path d="M15 144 L37 119 57 67 76 {30+shift} 86 70 104 89 95 125 99 150 61 151Z" fill="#959b91"/>
 <path d="M55 143 L76 {30+shift} 84 67 99 87 90 151Z" fill="#c4c1b2"/>
 <path d="M96 147 L114 77 130 {44+shift} 145 76 166 154Z" fill="#6d7777"/>
 <path d="M120 147 L130 {44+shift} 142 75 151 71 186 145 163 151Z" fill="#505e62"/>
 <path d="M59 71 L76 {30+shift} 91 60 88 67 79 60 73 69 68 59Z" fill="#f7f4e8"/>
 <path d="M116 77 L130 {44+shift} 146 77 137 70 132 65 127 70 123 65Z" fill="#e8e8df"/>
 <path d="M35 124L58 78 53 99 64 89 58 120 45 140Z" fill="#e0d7c2" opacity=".75"/>
 <path d="M147 90L165 116 171 143 150 135 158 128Z" fill="#9b9c91" opacity=".8"/>
 <path d="M46 139L67 102 62 130M73 80L84 110 78 142M104 116L113 96 110 141M135 83L144 112 138 145M157 112L165 138" fill="none" stroke="#495557" stroke-width="2" opacity=".63"/>
 <path d="M38 143q14 -10 24 -3m42 8q12 -6 24 -2m16 0q17 -9 28 -2" fill="none" stroke="#49774b" stroke-width="5" opacity=".84"/>
 <path d="M57 128l7 -7m54 16l8 -11m27 11l-8 -9" fill="none" stroke="#e1dcca" stroke-width="2" opacity=".7"/>
 '''
for i in (1,2): sprite(f'mountain_{i:02}','scenery',192,170,96,145,mountain(i))
# small cliffs
sprite('rock_cluster_01','scenery',128,90,64,68,'''<ellipse cx="65" cy="68" rx="42" ry="12" fill="#556447" opacity=".2"/><path d="M24 65L37 30 67 20 80 66Z" fill="url(#rock)"/><path d="M67 20L89 33 101 67 80 66Z" fill="#69716b"/><path d="M37 30L67 20 57 33 49 39Z" fill="#d9d6c7"/><path d="M84 68L100 46 115 67Z" fill="#959b92"/>''')
def pine(x,y,s=1):
 return f'''<ellipse cx="{x}" cy="{y+4*s}" rx="{12*s}" ry="{4*s}" fill="#274b39" opacity=".24"/>
 <path d="M{x} {y-60*s}L{x} {y+2*s}" stroke="#745a38" stroke-width="{3.3*s}"/>
 <path d="M{x} {y-64*s}Q{x-6*s} {y-46*s} {x-11*s} {y-36*s} L{x-4*s} {y-38*s} Q{x-14*s} {y-23*s} {x-21*s} {y-14*s}L{x-11*s} {y-17*s}Q{x-19*s} {y-6*s} {x-26*s} {y-1*s}Q{x-6*s} {y-8*s} {x} {y-6*s}Q{x+7*s} {y-9*s} {x+26*s} {y-1*s}L{x+12*s} {y-18*s}L{x+21*s} {y-14*s}L{x+5*s} {y-38*s}L{x+12*s} {y-36*s}Z" fill="#174a3d"/>
 <path d="M{x} {y-59*s}Q{x-5*s} {y-41*s} {x-9*s} {y-36*s}M{x-3*s} {y-40*s}Q{x-11*s} {y-23*s} {x-15*s} {y-18*s}M{x-1*s} {y-24*s}Q{x-14*s} {y-8*s} {x-19*s} {y-7*s}" stroke="#6da06c" stroke-width="{2.6*s}" opacity=".8" fill="none"/>
 <path d="M{x+2*s} {y-54*s} Q{x+8*s} {y-26*s} {x+18*s} {y-17*s} M{x+2*s} {y-26*s}Q{x+15*s} {y-8*s} {x+20*s} {y-5*s}" stroke="#0e362e" stroke-width="{2*s}" opacity=".65" fill="none"/>
 '''
def decid(x,y,s=1):
 return f'''<ellipse cx="{x}" cy="{y+4*s}" rx="{15*s}" ry="{5*s}" fill="#31533a" opacity=".25"/>
 <path d="M{x} {y-42*s}V{y+2*s} M{x} {y-20*s}L{x-13*s} {y-38*s}M{x} {y-25*s}L{x+13*s} {y-43*s}" stroke="#72543c" stroke-width="{3.8*s}" fill="none"/>
 <path d="M{x-30*s} {y-37*s}Q{x-36*s} {y-51*s} {x-21*s} {y-57*s}Q{x-23*s} {y-73*s} {x-4*s} {y-70*s}Q{x+7*s} {y-83*s} {x+21*s} {y-68*s}Q{x+39*s} {y-66*s} {x+31*s} {y-48*s}Q{x+37*s} {y-32*s} {x+19*s} {y-30*s}Q{x+5*s} {y-23*s} {x-4*s} {y-30*s}Q{x-21*s} {y-24*s} {x-30*s} {y-37*s}Z" fill="#4c833c"/>
 <path d="M{x-28*s} {y-48*s}Q{x-28*s} {y-61*s} {x-12*s} {y-60*s}Q{x-10*s} {y-74*s} {x+3*s} {y-69*s}Q{x+16*s} {y-74*s} {x+21*s} {y-60*s}Q{x+32*s} {y-55*s} {x+24*s} {y-45*s}Q{x+16*s} {y-37*s} {x+5*s} {y-40*s}Q{x-14*s} {y-33*s} {x-28*s} {y-48*s}Z" fill="#79a64c"/>
 <path d="M{x-19*s} {y-51*s}Q{x-14*s} {y-62*s} {x-5*s} {y-59*s}M{x+5*s} {y-59*s}Q{x+14*s} {y-64*s} {x+19*s} {y-53*s}" stroke="#b2c873" stroke-width="{4*s}" opacity=".73" fill="none"/>
 <path d="M{x-25*s} {y-40*s}Q{x-16*s} {y-31*s} {x-5*s} {y-36*s}" stroke="#315f35" stroke-width="{3*s}" opacity=".7" fill="none"/>
 '''
for ty in ['pine','deciduous']:
 for v in (1,2):
  r=seed(ty+str(v)); fn=pine if ty=='pine' else decid
  body=''.join(fn(x,y,s) for x,y,s in [(48,111,.75),(90,118,.8),(68,106,1.0)] if True)
  if v==2: body=''.join(fn(x,y,s) for x,y,s in [(39,116,.82),(83,115,1.06),(66,127,.62)])
  sprite(f'forest_{ty}_{v:02}','scenery',144,150,72,121,body,notes='Forest clump: sort from footprint below canopy')
# mountain mine entrance 20% visually smaller than initial direction: structure small footprint centered
body='''<ellipse cx="90" cy="114" rx="36" ry="10" fill="#413c30" opacity=".21"/>
<path d="M46 101L61 56 102 45 135 82 129 111 66 122Z" fill="#83857d"/>
<path d="M60 102L75 70 107 66 124 86 122 111 68 115Z" fill="#4d5959"/>
<path d="M75 107L77 80Q92 60 109 78L111 111Z" fill="#282e2c"/>
<path d="M73 109L75 78 84 69 105 69 113 79 114 111" fill="none" stroke="#875b33" stroke-width="8"/>
<path d="M76 78L111 78M82 75L82 108M105 75L105 108" stroke="#d4a05e" stroke-width="3"/>
<path d="M86 111L97 143M106 111L117 143" stroke="#7d704d" stroke-width="2.3"/>
<path d="M87 116L107 116M93 123L111 123M97 132L115 132" stroke="#806643" stroke-width="2.2"/>
<path d="M53 117l13 -6 7 7z" fill="#b8b1a0"/>'''
sprite('mine_mountain_small','structure',176,150,88,120,body,layer='structure',notes='Art-approved mine opening target scale 80% of initial visual reference; anchor footpoint fixed')
# cave deliberately small
body='''<ellipse cx="87" cy="107" rx="29" ry="8" fill="#344837" opacity=".22"/>
<path d="M50 103L60 77 79 63 104 70 126 89 121 108 76 116Z" fill="#727b76" stroke="#5c6561" stroke-width="2"/>
<path d="M70 108Q70 81 90 78Q110 79 114 109Z" fill="#273338"/>
<path d="M73 104Q80 86 93 83" fill="none" stroke="#455659" stroke-width="4"/>
<path d="M50 103L68 93 63 111M112 85l14 14-3 10" fill="none" stroke="#a5a79a" stroke-width="5"/>
<path d="M62 116l12 -4 14 4" fill="#8f917f"/>'''
sprite('cave_entrance_small','structure',160,136,80,111,body,layer='structure',notes='Art-approved cave entrance visually 20% smaller than initial reference')
# Quarry in grassland
body='''<ellipse cx="120" cy="107" rx="85" ry="26" fill="#6f704c" opacity=".2"/>
<path d="M25 89L67 48 144 40 216 78 175 120 68 127Z" fill="#c6aa70" stroke="#9f8659" stroke-width="2"/>
<path d="M52 88L83 62 142 59 185 81 155 106 90 111Z" fill="#847b68"/>
<path d="M52 88L90 111 155 106 185 81 185 97 152 119 85 123 52 100Z" fill="#a69676"/>
<path d="M82 63L143 59 161 69 101 75Z" fill="#ded1b5"/>
<path d="M103 81L167 81 148 95 107 98Z" fill="#c5b69a"/>
<path d="M185 81L216 78 195 99 172 101Z" fill="#b8a07a"/>
<path d="M31 108l14 -9 15 8-7 12Z" fill="#9a9787"/><path d="M197 114l12 -10 13 9-5 10Z" fill="#c9bd9d"/>
<path d="M185 57l25 10v18l-25 -9Z" fill="#ad7e41"/><path d="M181 55l20 -15 32 17-22 13Z" fill="#8d5b32"/><path d="M198 69v23M222 63v21" stroke="#674e35" stroke-width="3"/>'''
sprite('quarry_plain_01','structure',240,150,120,113,body,layer='structure',notes='Flatland quarry: surrounding raised edges and visible extraction pit')
# village
body='''<ellipse cx="107" cy="109" rx="80" ry="16" fill="#4f5f35" opacity=".16"/>
<path d="M32 80L64 63 92 78 60 96Z" fill="#94582f"/><path d="M38 81L38 106 61 118 61 96Z" fill="#d4c09a"/><path d="M61 96L88 81 88 104 61 118Z" fill="#b49d71"/>
<path d="M28 79L60 52 97 76 61 101Z" fill="#a75c32" stroke="#75492c" stroke-width="2"/>
<path d="M110 69L138 51 166 68 139 85Z" fill="#a35c36"/><path d="M113 70L113 102 139 115 139 85Z" fill="#e0c59b"/><path d="M139 85L163 72 163 103 139 115Z" fill="#b8a37f"/>
<path d="M105 68L138 41 174 67 139 90Z" fill="#a86939" stroke="#754b31" stroke-width="2"/>
<path d="M145 53v-30h22v38" fill="#cbb58a"/><path d="M140 25h32l-16 -19Z" fill="#ab613b"/><path d="M150 36h10v11h-10Z" fill="#4b6b61"/>
<path d="M48 98v11M69 99v11M126 91v11" stroke="#695238" stroke-width="3"/>
<path d="M80 116q10 -8 22 -4" stroke="#a58e5a" fill="none" stroke-width="3"/>'''
sprite('settlement_hamlet_01','structure',200,145,100,116,body,layer='structure',notes='Decorative map settlement only; no gameplay/interactions')
# islet on sea
body='''<ellipse cx="83" cy="88" rx="57" ry="18" fill="#115675" opacity=".2"/>
<path d="M29 88L46 76 76 65 123 75 139 90 116 104 66 106Z" fill="#d7c68f"/>
<path d="M41 83L66 65 117 74 127 87 103 100 66 99Z" fill="#89aa56"/>
<path d="M45 85L69 74 75 97" fill="#a6b96b"/>
<path d="M26 97q23 7 44 5 M103 104q22 0 38 -11" stroke="#d7f4e5" fill="none" stroke-width="2.5" opacity=".7"/>'''+pine(85,86,.48)+pine(105,87,.41)
sprite('island_small_01','scenery',166,130,83,92,body)
# opaque fog base
save('fog_unexplored_01','fog',f'<path d="{D}" fill="#21292b" opacity="1"/>',layer='fog',notes='Render last; opaque over terrain and tall sprites')
# manifest
manifest={'schemaVersion':1,'assetPack':'KOPANKA-MAP-003','version':'1.3.0-art-technical-candidate','geometry':{'worldCols':512,'worldRows':512,'tileWidthPx':128,'tileHeightPx':64,'tileAnchor':[64,32],'cameraZoom':1.2},'edgeBits':{'N':1,'E':2,'S':4,'W':8},'assets':assets}
(MAP/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
# model/demo 32x32 tile topology in coord space
SIZE=32
r=seed('topology-map003-32')
model=[[{'terrain':'grass','elevation':0,'riverMask':0,'coastMask':0,'objects':[]} for c in range(SIZE)] for rr in range(SIZE)]
# ocean toward bottom-right with irregular coastline
for row in range(SIZE):
 for col in range(SIZE):
  water = (col+row > 43+int(2*math.sin(col*.45)))
  m=model[row][col]
  if water: m['terrain']='sea'
  elif (row<9 and col<13): m['terrain']='mountain';m['elevation']=2
  elif (row<14 and col<16): m['terrain']='grass';m['elevation']=1
  elif r.random()<.16: m['terrain']='meadow'
# explicit winding river from headwaters to estuary (only cardinal neighbors)
# Less frequent turns: runs of 3-4 cells instead of a stair-step at every cell.
waypoints=[(5,3),(5,6),(8,6),(8,9),(12,9),(12,12),(16,12),(16,15),(20,15),(20,18),(24,18),(24,20)]
route=[waypoints[0]]
for (x0,y0),(x1,y1) in zip(waypoints,waypoints[1:]):
 dx=(x1>x0)-(x1<x0);dy=(y1>y0)-(y1<y0)
 for j in range(abs(x1-x0)+abs(y1-y0)):route.append((route[-1][0]+dx,route[-1][1]+dy))

# above reaches sea? col + row 49 at last (sea); yes
bits={(0,-1):1,(1,0):2,(0,1):4,(-1,0):8}
for i,(col,row) in enumerate(route):
 if i<len(route)-1 and model[row][col]['terrain']=='sea': model[row][col]['terrain']='grass'
 if i==len(route)-1: model[row][col]['terrain']='sea'
 dirs=[]
 for other in [route[i-1]] if i else []:
  dx,dy=other[0]-col,other[1]-row
  if (dx,dy) in bits: dirs.append(bits[(dx,dy)])
 for other in [route[i+1]] if i+1<len(route) else []:
  dx,dy=other[0]-col,other[1]-row
  if (dx,dy) in bits: dirs.append(bits[(dx,dy)])
 model[row][col]['riverMask']=sum(dirs)
 if model[row][col]['terrain']=='mountain':model[row][col]['terrain']='grass'; model[row][col]['elevation']=1
# coast masks of shore cells next to sea
for row in range(SIZE):
 for col in range(SIZE):
  if model[row][col]['terrain']=='sea':continue
  mask=0
  for (dx,dy),flag in bits.items():
   x,y=col+dx,row+dy
   if 0<=x<SIZE and 0<=y<SIZE and model[y][x]['terrain']=='sea':mask|=flag
  model[row][col]['coastMask']=mask
# explicitly placed objects
coords={'mine_mountain_small':(8,3),'cave_entrance_small':(3,12),'quarry_plain_01':(24,7),'settlement_hamlet_01':(8,22),'island_small_01':(29,24)}
for name,(col,row) in coords.items():
 model[row][col]['objects'].append(name)
for col,row in [(2,1),(4,2),(8,2),(11,4),(2,5),(12,6),(6,8),(10,8)]:model[row][col]['objects'].append('mountain_01' if (col+row)%2 else 'mountain_02')
for col,row in [(4,9),(12,12),(15,17),(17,19),(7,25),(8,27),(5,19),(20,5),(22,7),(25,11),(12,24)]:model[row][col]['objects'].append('forest_pine_01' if (col+row)%2 else 'forest_deciduous_01')
for col,row in [(10,14),(16,14),(21,10),(9,17),(16,7),(14,21),(19,23)]:model[row][col]['objects'].append('forest_deciduous_02')
for col,row in [(5,17),(6,17),(7,16),(11,19),(12,20),(13,19),(16,20),(17,21),(18,20),(19,22),(20,24),(21,23),(9,11),(10,10),(11,10),(13,13),(14,12),(25,10),(26,10),(27,11),(22,11),(23,12),(20,17),(21,18),(10,25),(11,25),(5,25),(5,26),(4,25),(17,6),(18,6),(19,5),(17,8),(18,9),(19,8),(12,4),(13,4)]:
 if model[row][col]['terrain']!='sea' and not model[row][col]['riverMask'] and not model[row][col]['objects']:
  model[row][col]['objects'].append('forest_deciduous_01' if (row*3+col)%4 else 'forest_pine_02')
# compositing with footprint world anchor; negative canvas offset
lookup={a['id']:a for a in assets}
CACHE={a['id']:Image.open(MAP/a['path']).convert('RGBA') for a in assets}
W=4200;H=2280;origx=2100;origy=45
canvas=Image.new('RGBA',(W,H),(0,0,0,0))
placements=[]
for row in range(SIZE):
 for col in range(SIZE):
  x=origx+(col-row)*64;y=origy+(col+row)*32
  m=model[row][col]
  if m['terrain']=='sea': ground='water_sea_01' if (col+row)%2 else 'water_sea_02'
  elif m['terrain']=='mountain':ground='ground_earth_01'
  else:ground='ground_meadow_01' if m['terrain']=='meadow' else ('ground_grass_01' if (col*7+row)%3 else 'ground_grass_02')
  placements.append((0,y,x,ground))
  if m['coastMask']:placements.append((1,y,x,f"coast_mask_{m['coastMask']:02}"))
  if m['riverMask']:
   placements.append((2,y,x,f"river_mask_{m['riverMask']:02}"))
  for a in m['objects']: placements.append((3 if lookup[a]['layer']=='scenery' else 4,y,x,a))
placements.sort(key=lambda z:(z[0],z[1],z[2]))
for _,y,x,id in placements:
 a=lookup[id];p=CACHE[id]; px=int(x-a['anchorX']);py=int(y-a['anchorY'])
 canvas.alpha_composite(p,(px,py))
bbox=canvas.getbbox();assert bbox
scene=canvas.crop((bbox[0],bbox[1],bbox[2],bbox[3]))
scene.save(DEMO/'map_32x32_full.png',optimize=True)
scene.thumbnail((1680,1000),Image.Resampling.LANCZOS)
bg=Image.new('RGB',scene.size,(38,68,64)); bg.paste(scene,(0,0),scene)
bg.save(DEMO/'map_32x32_preview.jpg',quality=93,optimize=True)
# tiny asset contact sheet
selected=['ground_grass_01','ground_earth_01','ground_sand_01','water_sea_01','river_mask_05','river_mask_10','coast_mask_04','coast_mask_08','mountain_01','forest_pine_01','forest_deciduous_01','mine_mountain_small','cave_entrance_small','quarry_plain_01','settlement_hamlet_01','island_small_01']
thumb=Image.new('RGB',(1000,800),(236,233,216));dr=ImageDraw.Draw(thumb)
for i,id in enumerate(selected):
 x=25+(i%4)*245; y=25+(i//4)*195;p=CACHE[id].copy();p.thumbnail((220,142),Image.Resampling.LANCZOS)
 thumb.paste(p,(x+(220-p.width)//2,y),p)
 dr.text((x,y+151),id,fill=(31,54,45))
thumb.save(DEMO/'asset_contact_sheet.png')
# model with positions, graph
scenejson={'width':32,'height':32,'worldOrigin':'col=0,row=0','riverPath':[{'col':x,'row':y} for x,y in route],'objects':[{'id':k,'col':v[0],'row':v[1]} for k,v in coords.items()],'cells':model}
(DEMO/'map_32x32.json').write_text(json.dumps(scenejson,ensure_ascii=False,indent=1))
# doc
(ROOT/'README.md').write_text('''# KOPANKA MAP-003 — ассети v1.3 (кандидат для художнього приймання)

**Статус:** виробничий комплект PNG+SVG створено локально. Художню композицію раніше погоджено; однак Android-інтеграція, шви на пристрої, FPS/RAM і фінальне приймання координатором **ще не виконані**. Це авторські SVG-ассети в стилізованій мальованій манері, не піксельно точне витягування об’єктів із раніше затвердженої цілісної ілюстрації.

## Структура
- `prototype/android/app/src/main/assets/map/manifest.json` — контракт schemaVersion=1; PNG згідно з каталогами
- `source_svg/` — **редаговані** SVG у відповідних папках; експорт CairoSVG у нативному масштабі
- `demo/map_32x32.json` — логічна тестова ділянка 32×32 і зв’язний граф річки
- `demo/map_32x32_full.png`, `map_32x32_preview.jpg` — лише контрольна композиція, **НЕ** один ігровий фон
- `demo/asset_contact_sheet.png` — огляд PNG

## Геометрія та anchor
512×512 клітин, footprint ромб 128×64 px, опорна точка `(64,32)` для ground. Формули при 1×: `x=(col-row)*64`, `y=(col+row)*32`; камера Android масштабує рівно 1,2×. Для високих SVG/PNG `anchorX,anchorY` задані в manifest і означають **позицію footprint у пікселях зображення**, не геометричний центр спрайта.

## Порядок рендерингу
`ground` → `slope` → `water/coast` → `river` → `scenery` → `structure` → `fog` (fog повністю перекриває недосліджене). При панорамуванні відмальовувати тільки видимі клітини плюс halo. Високі об'єкти сортувати за footprint Y, а не за верхнім краєм PNG.

## Річки
`N=1,E=2,S=4,W=8`; маски 01…15 задають відводи до центрів ребер ромба. Маршрут у JSON дає суміжні клітини з кроком рівно 1; витік і гирло — окремі спрайти. Через межі чанків використовувати глобальні координати (не обривати маску). Компоновщик демонстрації — опорний приклад, а не фінальний Android-рендер.

## Береги
`coast_mask_01…15` — вода з боку сусідньої морської клітини, за N/E/S/W. Діагональні випадки/внутрішні кути перед Android-прийманням потребують перевірки з padding/extrusion, щоб не виникали шви при 1,2×. Перший комплект покриває ортогональні маски 01–15 (00 = без переходу) та чотири окремі діагональні corner overlays NE/SE/SW/NW; які саме комбінації накладати на Android, підтвердити на стикових тестах.

## Ліцензія
SVG і похідні PNG створено для KOPANKA, дозволено використання, зміна, копіювання та поширення у складі проєкту; зовнішніх графічних бібліотек/чужих мальованих ассетів у складі не використано. Генерація відбувалася програмним формуванням SVG.

## Відкриті ризики
Стикування water/river/coast на відрізках сусідніх тайлів і alpha bleed на мобільному фільтруванні **не підтверджені Android-тестом**; це не релізний комплект. Під час інтеграції порівняти зі схваленим painterly референсом; стилістика поточних SVG дещо більш векторна. Шахта і печера намальовані у зменшеному на 20% художньому масштабі щодо початкового вигляду.
''',encoding='utf-8')
(ROOT/'LICENSE_ASSETS.md').write_text('''# Права на графічні матеріали MAP-003
Цей комплект SVG і відповідних PNG створено з нуля для проєкту KOPANKA в межах цього завдання. Програмні SVG-ілюстрації є оригінальними робочими матеріалами; сторонні зображення чи чужі текстури не копіювалися. Дозволене використання, редагування та поширення в продукті KOPANKA. Художнє приймання і перевірка сторонніх прав перед публічним релізом залишаються за власником проєкту.
''',encoding='utf-8')
print('Generated',len(assets),'PNG and SVG; scene',bbox, 'preview',bg.size)
