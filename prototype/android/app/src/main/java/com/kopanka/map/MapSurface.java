package com.kopanka.map;

import android.content.Context;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.graphics.Path;
import android.view.MotionEvent;
import android.view.View;

/** First Android map renderer. Draws ONLY exposed viewport cells; no PNG assets yet. */
public final class MapSurface extends View {
    private final WorldMap world = new WorldMap();
    private final IsoCamera camera = new IsoCamera();
    private final FogStore fog;
    private final Paint paint = new Paint(Paint.ANTI_ALIAS_FLAG);
    // MAP-002A diagnostic palette: unexplored map cells are purple;
    // the area outside the 512x512 world remains dark teal.
    // These colors are temporary and do not disclose hidden geography.
    private static final int OUTSIDE_WORLD_COLOR = 0xFF142021;
    private static final int UNEXPLORED_FOG_COLOR = 0xFF51435F;
    private final Path diamond = new Path();
    private float downX, downY, lastX, lastY;
    private boolean moving;

    public MapSurface(Context context) {
        super(context);
        fog = new FogStore(context);
        // Initial technical discovery, without introducing a hero or game mechanics.
        if (fog.reveal(256, 254, 10)) fog.save();
        setBackgroundColor(OUTSIDE_WORLD_COLOR);
    }
    @Override protected void onSizeChanged(int w, int h, int oldW, int oldH) {
        super.onSizeChanged(w, h, oldW, oldH);
        camera.constrainToViewport(w, h);
    }

    @Override protected void onDraw(Canvas canvas) {
        super.onDraw(canvas);
        int w = getWidth(), h = getHeight();
        if (w == 0 || h == 0) return;
        // Inverse projection of viewport corners + margin for tall scenery.
        float[] sx = {-150, w+150, -150, w+150};
        float[] sy = {-220, -220, h+220, h+220};
        int minX=WorldMap.SIZE-1,maxX=0,minY=WorldMap.SIZE-1,maxY=0;
        for(int i=0;i<4;i++) {
            float col=camera.colFromScreen(sx[i],sy[i],w,h);
            float row=camera.rowFromScreen(sx[i],sy[i],w,h);
            minX=Math.min(minX,(int)Math.floor(col)-2);
            maxX=Math.max(maxX,(int)Math.ceil(col)+2);
            minY=Math.min(minY,(int)Math.floor(row)-2);
            maxY=Math.max(maxY,(int)Math.ceil(row)+2);
        }
        minX=Math.max(0,minX); minY=Math.max(0,minY);
        maxX=Math.min(WorldMap.SIZE-1,maxX);maxY=Math.min(WorldMap.SIZE-1,maxY);
        if (minX > maxX || minY > maxY) return;
        // Painter's order by footprint depth. No full-map loop in onDraw.
        for(int sum=minX+minY;sum<=maxX+maxY;sum++) {
            for(int y=Math.max(minY,sum-maxX);y<=Math.min(maxY,sum-minX);y++) {
                int x=sum-y;
                float px=camera.screenX(x,y,w);
                float py=camera.screenY(x,y,h);
                if (!fog.isExplored(x,y)) {
                    // Opaque diagnostic fog over the logical cell footprint.
                    // Do not call terrain() or draw features for unexplored cells.
                    drawDiamond(canvas,px,py,UNEXPLORED_FOG_COLOR);
                    continue;
                }
                int type=world.terrain(x,y);
                drawGround(canvas,px,py,type);
                drawFeature(canvas,px,py,type);
            }
        }
    }
    private void drawDiamond(Canvas canvas, float x, float y, int color) {
        float hw=IsoCamera.TILE_WIDTH*IsoCamera.ZOOM/2f;
        float hh=IsoCamera.TILE_HEIGHT*IsoCamera.ZOOM/2f;
        diamond.reset();
        diamond.moveTo(x,y-hh);
        diamond.lineTo(x+hw,y);
        diamond.lineTo(x,y+hh);
        diamond.lineTo(x-hw,y);
        diamond.close();
        paint.setStyle(Paint.Style.FILL);
        paint.setColor(color);
        canvas.drawPath(diamond,paint);
    }
    private void drawGround(Canvas canvas,float x,float y,int kind) {
        int color;
        switch(kind){
            case WorldMap.RIVER: color=0xFF5592A7;break;
            case WorldMap.SEA: color=0xFF376F93;break;
            case WorldMap.MOUNTAIN:case WorldMap.MINE:case WorldMap.CAVE:color=0xFF989788;break;
            case WorldMap.CONIFER:color=0xFF7BA47A;break;
            case WorldMap.DECIDUOUS:color=0xFF9EB57C;break;
            default:color=0xFFADC18C;
        }
        drawDiamond(canvas,x,y,color);
    }
    private void drawFeature(Canvas canvas,float x,float y,int kind) {
        float s=IsoCamera.ZOOM;
        paint.setStyle(Paint.Style.FILL);
        if(kind==WorldMap.MOUNTAIN||kind==WorldMap.MINE||kind==WorldMap.CAVE){
            Path peak=new Path();
            peak.moveTo(x-37*s,y+6*s);
            peak.lineTo(x-3*s,y-48*s);
            peak.lineTo(x+34*s,y+6*s);
            peak.close();
            paint.setColor(0xFF5C6463);canvas.drawPath(peak,paint);
            if(kind==WorldMap.MINE||kind==WorldMap.CAVE){
                paint.setColor(0xFF292F30);
                canvas.drawOval(x-11*s,y-13*s,x+12*s,y+7*s,paint);
                if(kind==WorldMap.MINE){
                    paint.setColor(0xFFBB8A4F);
                    canvas.drawRect(x-13*s,y-15*s,x-10*s,y+7*s,paint);
                    canvas.drawRect(x+11*s,y-15*s,x+14*s,y+7*s,paint);
                }
            }
        } else if(kind==WorldMap.CONIFER||kind==WorldMap.DECIDUOUS){
            paint.setColor(0xFF3A6347);
            if(kind==WorldMap.CONIFER){
                Path tree=new Path();tree.moveTo(x,y-39*s);
                tree.lineTo(x-19*s,y+3*s);tree.lineTo(x+19*s,y+3*s);tree.close();
                canvas.drawPath(tree,paint);
            }else{
                canvas.drawCircle(x,y-14*s,19*s,paint);
            }
        }else if(kind==WorldMap.QUARRY){
            paint.setColor(0xFF8B826A);
            canvas.drawOval(x-25*s,y-10*s,x+25*s,y+10*s,paint);
            paint.setColor(0xFF66665F);
            canvas.drawOval(x-15*s,y-6*s,x+15*s,y+4*s,paint);
        }else if(kind==WorldMap.SETTLEMENT){
            paint.setColor(0xFF926543);
            canvas.drawRect(x-17*s,y-24*s,x+17*s,y+5*s,paint);
            Path roof=new Path();roof.moveTo(x-24*s,y-24*s);
            roof.lineTo(x,y-42*s);roof.lineTo(x+24*s,y-24*s);roof.close();
            paint.setColor(0xFFAE5B40);canvas.drawPath(roof,paint);
        }
    }
    @Override public boolean onTouchEvent(MotionEvent event) {
        switch(event.getActionMasked()){
            case MotionEvent.ACTION_DOWN:
                downX=lastX=event.getX();downY=lastY=event.getY();moving=false;return true;
            case MotionEvent.ACTION_MOVE:
                if(event.getPointerCount()!=1)return true;
                float x=event.getX(),y=event.getY();
                if(Math.hypot(x-downX,y-downY)>12*getResources().getDisplayMetrics().density)moving=true;
                if(moving){camera.drag(x-lastX,y-lastY,getWidth(),getHeight());invalidate();}
                lastX=x;lastY=y;return true;
            case MotionEvent.ACTION_UP:
                if(!moving){
                    int col=Math.round(camera.colFromScreen(event.getX(),event.getY(),getWidth(),getHeight()));
                    int row=Math.round(camera.rowFromScreen(event.getX(),event.getY(),getWidth(),getHeight()));
                    if(world.inside(col,row)&&fog.reveal(col,row,5)){fog.save();invalidate();}
                    performClick();
                }
                return true;
            case MotionEvent.ACTION_CANCEL:return true;
            default:return true;
        }
    }
    @Override public boolean performClick(){super.performClick();return true;}
}
