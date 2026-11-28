"""Experimental v10 texture, preserving v9 mesh silhouette and object anchors."""
from PIL import Image, ImageFilter, ImageChops
import random

def texture_relief(image):
    rgb=image.convert("RGB")
    mask=Image.new("L",image.size)
    # Exact v9 land colors; exclude water and background.
    for color in ((142,153,128),(148,178,110)):
        diff=ImageChops.difference(rgb,Image.new("RGB",image.size,color))
        r,g,b=diff.split()
        exact=ImageChops.lighter(ImageChops.lighter(r,g),b).point(lambda x:255 if x==0 else 0)
        mask=ImageChops.lighter(mask,exact)
    rng=random.Random(10510)
    def noise(w,h):
        n=Image.new("L",(w,h))
        n.putdata([rng.randrange(256) for _ in range(w*h)])
        return n.resize(image.size,Image.Resampling.BICUBIC)
    broad=noise(45,25)
    fine=noise(650,365)
    delta=ImageChops.blend(broad,fine,.35).point(lambda x: int(x*.12)+112)
    bands=[ImageChops.add(b,delta,scale=1,offset=-127) for b in rgb.split()]
    textured=Image.merge("RGB",bands).convert("RGBA")
    image.paste(textured,(0,0),mask)
