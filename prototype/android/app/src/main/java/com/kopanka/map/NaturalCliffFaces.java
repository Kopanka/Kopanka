package com.kopanka.map;

import android.graphics.Canvas;
import android.graphics.Paint;
import android.graphics.Path;

/**
 * MAP-005 natural terrain-face prototype. Draws only a visible height
 * difference between two discovered neighbors, never an unexplored edge.
 *
 * Tile tops are rendered afterwards, preserving existing pixel geometry
 * (128x64, fixed 1.2x). The contour has irregular stone/vegetation facets
 * rather than a solid straight horizontal platform wall.
 *
 * Not a replacement for the approved artist's height-aware PNG atlas.
 */
final class NaturalCliffFaces {
    private static final int SEGMENTS = 8;
    private static final float STEP = ElevationMap.STEP_PX * IsoCamera.ZOOM;
    private final Paint paint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Path face = new Path();
    private final Path facet = new Path();

    private static float rand(int col, int row, int side, int n) {
        int k=col*73471 ^ row*17389 ^ side*6673 ^ n*18439;
        k^=k>>>16;
        k*=0x7feb352d;
        k^=k>>>15;
        return (k & 0xffff)/65535f;
    }

    void draw(Canvas canvas, float x, float topY, float halfW, float halfH,
              int col, int row, int side, int dropLevels, boolean mountain) {
        if (dropLevels<=0) return;
        // East = upper-right -> lower-centre; south = lower-centre -> upper-left.
        final float ax=side==0?x+halfW:x;
        final float ay=side==0?topY:topY+halfH;
        final float bx=side==0?x:x-halfW;
        final float by=side==0?topY+halfH:topY;
        final float dy=dropLevels*STEP;
        final int faceColor=mountain
                ? (side==0?0xff888f7e:0xff737e72)
                : (side==0?0xff98b184:0xff8da77b);

        // Irregular lower boundary is seeded per logical cell, not per frame.
        // Both endpoints return to the exact height to avoid a tile-size gap.
        face.reset();
        face.moveTo(ax,ay);
        face.lineTo(bx,by);
        for (int i=SEGMENTS;i>=0;i--) {
            float t=i/(float)SEGMENTS;
            float weight=(float)Math.sin(Math.PI*t);
            float offset=(rand(col,row,side,i)-.5f)*STEP*.35f*weight;
            face.lineTo(ax+(bx-ax)*t,ay+(by-ay)*t+dy+offset);
        }
        face.close();
        paint.setStyle(Paint.Style.FILL);
        paint.setColor(faceColor);
        canvas.drawPath(face,paint);

        // Deterministic short facets: they never traverse the whole cliff
        // and are clipped to the irregular height face.
        canvas.save();
        canvas.clipPath(face);
        int count=Math.max(2,Math.min(7,dropLevels*2+1));
        for(int i=0;i<count;i++){
            float t=.12f+.76f*rand(col,row,side,20+i);
            float px=ax+(bx-ax)*t;
            float py=ay+(by-ay)*t;
            float shift=(rand(col,row,side,50+i)-.5f)*STEP*.7f;
            float l=Math.min(dy*.68f,(.25f+.32f*rand(col,row,side,70+i))*dy);
            float width=3.3f+2.7f*rand(col,row,side,90+i);
            facet.reset();
            facet.moveTo(px-width,py+shift+2);
            facet.lineTo(px+width*.35f,py+shift+3);
            facet.lineTo(px+width*.7f,py+shift+l);
            facet.close();
            paint.setColor((i%3)==0
                    ? (mountain?0x709ba29a:0x6088ab77)
                    : (mountain?0x60616861:0x5d6d9466));
            canvas.drawPath(facet,paint);
        }
        canvas.restore();
    }
}
