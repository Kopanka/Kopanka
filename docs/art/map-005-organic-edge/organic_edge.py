#!/usr/bin/env python3
"""Experimental organic 2.5D height-edge painting for MAP-005 scene v7.

Unlike the 156 face sprites in the v6 technical library, this draws terrain
transitions as *tapered rocky and grassy terrain shoulders*, with irregular
foot silhouettes and broken strata. Not production art or Android integration.
No changes to land geometry, height values, anchors or zoom are allowed.
"""
from PIL import Image,ImageDraw,ImageFilter
import math,random

STEP=13
HALF_W=64
HALF_H=32

def _edge(x,y,side):
    if side=="E":return ((x+HALF_W,y),(x,y+HALF_H))
    if side=="S":return ((x,y+HALF_H),(x-HALF_W,y))
    raise ValueError(side)

def _hash(col,row,side,idx=0):
    return random.Random(col*73856093+row*19349663+(1 if side=="E" else 2)*83492791+idx*179)

def _curve(a,b,t):
    return (a[0]*(1-t)+b[0]*t,a[1]*(1-t)+b[1]*t)

def paint_face(image,x,y,side,levels,material,col,row,water=False):
    """Draw a single exposed side; NO flat parallelogram fill.

    Irregular bottom edge is deterministic, with two end positions
    pinned to exact base elevation for repeatable cell joins.
    """
    if not 1<=levels<=5:raise ValueError(levels)
    (a,b)=_edge(x,y,side)
    dy=STEP*levels
    rnd=_hash(col,row,side)
    rock=(103,112,102,255) if material=="rock" else (111,131,91,255)
    soil=(94,99,83,255) if material=="rock" else (97,117,75,255)
    light=(162,158,137,255) if material=="rock" else (145,155,105,255)
    shadow=(78,85,76,255) if material=="rock" else (82,108,67,255)
    points=[]
    for i in range(17):
        t=i/16
        px,py=_curve(a,b,t)
        envelope=math.sin(math.pi*t)
        delta=envelope*(2.8*math.sin(t*math.pi*5.5+col*.5)+
                        2.2*math.sin(t*math.pi*10.5+row*.35))
        points.append((round(px),round(py+dy+delta)))
    # Preserve top tile contour, but break bottom geology into ridges.
    poly=[a,b]+list(reversed(points))
    d=ImageDraw.Draw(image,"RGBA")
    d.polygon(poly,fill=rock)
    # Small rock faces, anchored to the exposed face, not long bars.
    for j in range(31):
        r=_hash(col,row,side,j+101)
        t=r.uniform(.04,.96)
        fx,fy=_curve(a,b,t)
        hh=r.uniform(.18,.88)*dy
        w=r.uniform(2,6+levels)
        d.polygon([(fx-w,fy+hh*.42),(fx+w*.5,fy+hh*.18),
                   (fx+w*.94,fy+hh),(fx-w*.45,fy+hh*1.03)],
                  fill=r.choice((soil,light,shadow)))
    # Organic talus at the foot. Rock chips spill into the adjacent
    # lower level, with no rectangular / uniform-base stripe.
    for j in range(24):
        r=_hash(col,row,side,j+211)
        t=r.uniform(.08,.92)
        fx,fy=_curve(a,b,t)
        fx+=r.uniform(-5,5)
        fy+=dy+r.uniform(-1.5,7)
        rw=r.uniform(1,6)
        rh=r.uniform(.75,4)
        d.ellipse((fx-rw,fy-rh,fx+rw,fy+rh),
                  fill=r.choice((soil,light,shadow)))
    if water:
        for j in range(16):
            r=_hash(col,row,side,j+401)
            t=r.uniform(.05,.95)
            fx,fy=_curve(a,b,t)
            fy+=dy+r.uniform(2,6)
            d.arc((fx-8,fy-3,fx+8,fy+3),160,355,
                  fill=(210,221,194,r.randint(90,180)),width=1)

def paint_lip(image,x,y,side,levels,material,col,row):
    """Broken vegetation/stone shoulder *on top* of elevated ground.
    This removes the razor-straight top transition with deterministic
    local patches. Each patch remains inside the upper diamond.
    """
    (a,b)=_edge(x,y,side)
    rnd=_hash(col,row,side,321)
    d=ImageDraw.Draw(image,"RGBA")
    for j in range(53):
        t=rnd.uniform(.06,.94)
        cx,cy=_curve(a,b,t)
        # Offset inside top diamond (toward its center at x,y).
        vx,vy=(x-cx),(y-cy)
        norm=max(1,math.hypot(vx,vy))
        inward=rnd.uniform(1.5,12.5)
        px=cx+inward*vx/norm
        py=cy+inward*vy/norm
        rr=rnd.uniform(.9,3.3)
        if material=="rock":
            palette=((147,150,129,235),(113,126,103,210),
                     (166,166,139,215),(97,117,88,200))
        else:
            palette=((112,141,84,230),(129,161,91,214),
                     (147,151,101,212),(102,133,75,210))
        d.ellipse((px-rr,py-rr*.5,px+rr,py+rr*.5),
                  fill=rnd.choice(palette))
    # Rounded specks soften the edge rather than a continuous stroke.
    for j in range(13):
        t=rnd.uniform(.1,.9)
        px,py=_curve(a,b,t)
        rad=rnd.uniform(1.2,3.3)
        d.ellipse((px-rad,py-rad*.7,px+rad,py+rad*.7),
                  fill=(115,136,93,155))
