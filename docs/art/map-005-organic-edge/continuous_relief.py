"""Experimental v9 visual mesh. Does not mutate authored geography."""
import math
from PIL import ImageDraw

def shared_height(cells, c, r):
    values=[]
    for y in (r-1,r):
        for x in (c-1,c):
            if 0<=y<len(cells) and 0<=x<len(cells[y]):
                cell=cells[y][x]
                if cell["terrain"]=="sea":
                    return 0.0
                values.append(cell["elevation"])
    return sum(values)/len(values) if values else 0.0

def draw_relief(image,cells,ox,oy,dx=64,dy=32,step=13):
    """Shared corners remove vertical tile walls; test-only visual surface."""
    d=ImageDraw.Draw(image)
    rows=len(cells); cols=len(cells[0])
    def vertex(c,r):
        return (ox+(c-r)*dx,oy+(c+r-1)*dy-shared_height(cells,c,r)*step)
    for level in range(rows+cols-1):
        for r in range(rows):
            c=level-r
            if not 0<=c<cols: continue
            cell=cells[r][c]
            if cell["terrain"]=="sea": continue
            a,b,e,f=vertex(c,r),vertex(c+1,r),vertex(c+1,r+1),vertex(c,r+1)
            z=cell["elevation"]
            peak=(ox+(c-r)*dx,oy+(c+r)*dy-z*step)
            mountain=cell["terrain"]=="mountain"
            base=(142,153,128) if mountain else (148,178,110)
            for i,(p,q) in enumerate(((a,b),(b,e),(e,f),(f,a))):
                # Derive shading from projected slope, not triangle index.
                # Flat triangles must have identical color.
                # Compare edge midpoint to the unraised center.
                midpoint_y=(p[1]+q[1])/2
                expected=(-dy/2,dy/2,dy/2,-dy/2)[i]
                slope=(midpoint_y-peak[1]-expected)/step
                shade=round(max(-12,min(12,slope*6)))
                d.polygon([p,q,peak],fill=tuple(max(0,min(255,v+shade)) for v in base)+(255,))
