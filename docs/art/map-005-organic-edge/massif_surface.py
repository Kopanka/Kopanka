#!/usr/bin/env python3
"""Experimental massif-top surface painter; NOT production art or Android integration."""
from PIL import Image,ImageDraw
import math

def _noise(col,row,k):
    v=(col*92837111+row*689287499+k*283923481)&0xffffffff
    v^=v>>13
    v=(v*1274126177)&0xffffffff
    return ((v^(v>>16))&0xffff)/65535.

def draw_massif_surface(image,x,y,col,row,elevation,terrain):
    """Paint rock strata on the existing 128x64 top footprint only."""
    if elevation<=0 or terrain!="mountain":return False
    tile=Image.new("RGBA",(129,65))
    d=ImageDraw.Draw(tile,"RGBA")
    palette=[(125,130,117,195),(173,168,151,188),
             (110,120,110,206),(89,104,98,179)]
    for stripe in range(-4,12):
        k=(col-row)*.68+stripe*.82
        phase=(col+row)*.36
        pts=[]
        for j in range(19):
            xx=-14+j*9
            yy=27+stripe*6.2+math.sin(xx/25+phase)*3.7-xx*.17
            yy+=math.sin((xx+col*56+row*26)/15.+k)*1.6
            pts.append((xx,yy))
        d.line(pts,fill=palette[(stripe+col+row)%len(palette)],width=2)
    for i in range(7):
        n=_noise(col,row,i)
        xx=18+94*_noise(col,row,i+15)
        yy=7+50*_noise(col,row,i+30)
        w=7+13*n
        d.polygon([(xx-w,yy+1),(xx-w*.16,yy-4),
                   (xx+w,yy),(xx+w*.7,yy+3),(xx-w*.6,yy+4)],
                  fill=palette[(i+col*3+row)%len(palette)])
    for i in range(9):
        xx=15+98*_noise(col,row,80+i)
        yy=7+47*_noise(col,row,130+i)
        rx=2+4*_noise(col,row,210+i)
        d.ellipse((xx-rx,yy-rx*.55,xx+rx,yy+rx*.55),
                  fill=(116,150,104,156))
    mask=Image.new("L",tile.size,0)
    ImageDraw.Draw(mask).polygon([(64,0),(128,32),(64,64),(0,32)],fill=255)
    tile.putalpha(Image.composite(tile.getchannel("A"),
                                  Image.new("L",tile.size,0),mask))
    image.alpha_composite(tile,(x-64,y-32))
    return True

def massif_summary(data):
    heights=[c["elevation"] for row in data["cells"] for c in row]
    terrain=[c["terrain"] for row in data["cells"] for c in row]
    return {"mountainCells":terrain.count("mountain"),
            "elevatedCells":sum(x>0 for x in heights),
            "elevationSum":sum(heights),
            "authoredRiverCells":len(data["riverPath"]),
            "geometry":{"tileWidthPx":128,"tileHeightPx":64,
                        "anchor":[64,32],"zoom":1.2}}
