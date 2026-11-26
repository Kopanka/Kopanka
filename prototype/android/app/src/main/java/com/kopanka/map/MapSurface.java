package com.kopanka.map;

import android.content.Context;
import android.graphics.Canvas;
import android.graphics.Bitmap;
import android.graphics.RectF;
import android.util.Log;
import android.util.LruCache;
import java.io.IOException;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.HashSet;
import java.util.Set;
import android.graphics.Color;
import android.graphics.Paint;
import android.graphics.Path;
import android.view.MotionEvent;
import android.view.View;

/** MAP-003: viewport-only isometric preview with real art PNGs and persisted opaque fog. */
public final class MapSurface extends View {
    private final WorldMap world = new WorldMap();
    private final IsoCamera camera = new IsoCamera();
    private final FogStore fog;
    private final MapAssetCatalog art;
    private final DemoMap demo;
    private final RectF spriteBounds = new RectF();
    private final LruCache<String, Bitmap> bitmapCache =
            new LruCache<String, Bitmap>(16 * 1024 * 1024) {
                @Override protected int sizeOf(String key, Bitmap value) {
                    return value.getByteCount();
                }
            };
    private final Set<String> failedAssets = new HashSet<>();
    private static final class Sprite {
        final int col, row;
        final String id;
        final float depth;
        Sprite(int col, int row, String id, float depth) {
            this.col = col; this.row = row; this.id = id; this.depth = depth;
        }
    }

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
        MapAssetCatalog catalog = null;
        DemoMap example = null;
        try {
            catalog = MapAssetCatalog.load(context.getAssets());
            if (!catalog.isEmpty()) example = DemoMap.load(context.getAssets());
        } catch (IOException badAssets) {
            Log.e("KOPANKA_MAP", "MAP-003 art manifest/demo invalid", badAssets);
        }
        art = catalog;
        demo = example;
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
        // Inverse projection of visible corners; modest halo includes high sprites.
        float[] sx = {-200, w + 200, -200, w + 200};
        float[] sy = {-260, -260, h + 260, h + 260};
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
        maxX=Math.min(WorldMap.SIZE-1,maxX); maxY=Math.min(WorldMap.SIZE-1,maxY);
        if (minX>maxX || minY>maxY) return;

        // Pass 1: ground + sea only for explored cells; never inspect hidden terrain.
        for(int sum=minX+minY;sum<=maxX+maxY;sum++) {
            for(int row=Math.max(minY,sum-maxX);row<=Math.min(maxY,sum-minX);row++) {
                int col=sum-row;
                if (!fog.isExplored(col,row)) continue;
                float px=camera.screenX(col,row,w), py=camera.screenY(col,row,h);
                DemoMap.Cell cell=demo == null ? null : demo.at(col,row);
                if (cell == null) {
                    int kind=world.terrain(col,row);
                    drawGround(canvas,px,py,kind);
                } else {
                    String base = "sea".equals(cell.terrain)
                        ? ((col+row)%3==0 ? "water_sea_02":"water_sea_01")
                        : "mountain".equals(cell.terrain) ? "ground_earth_01"
                        : "meadow".equals(cell.terrain) ? "ground_meadow_01"
                        : (col*7+row*11)%9==0 ? "ground_grass_02":"ground_grass_01";
                    if (!drawSprite(canvas,base,px,py)) drawGround(canvas,px,py,WorldMap.PLAIN);
                }
            }
        }

        // Pass 2: terrain overlays: slope -> coast -> river.
        for(int sum=minX+minY;sum<=maxX+maxY;sum++) {
            for(int row=Math.max(minY,sum-maxX);row<=Math.min(maxY,sum-minX);row++) {
                int col=sum-row;
                if (!fog.isExplored(col,row) || demo==null) continue;
                DemoMap.Cell cell=demo.at(col,row);
                if (cell==null) continue;
                float px=camera.screenX(col,row,w),py=camera.screenY(col,row,h);
                if ("mountain".equals(cell.terrain)) {
                    if (!isMountain(col,row-1)) drawSprite(canvas,"slope_n",px,py);
                    if (!isMountain(col+1,row)) drawSprite(canvas,"slope_e",px,py);
                    if (!isMountain(col,row+1)) drawSprite(canvas,"slope_s",px,py);
                    if (!isMountain(col-1,row)) drawSprite(canvas,"slope_w",px,py);
                }
                if (cell.coastMask>0 && cell.coastMask<=15)
                    drawSprite(canvas,maskId("coast",cell.coastMask),px,py);
                // Diagonal shore corners are independent of N/E/S/W edge mask.
                if (!"sea".equals(cell.terrain) && cell.coastMask>0) {
                    if (demo.sea(col+1,row-1) && !demo.sea(col,row-1) && !demo.sea(col+1,row))
                        drawSprite(canvas,"coast_corner_ne",px,py);
                    if (demo.sea(col-1,row-1) && !demo.sea(col,row-1) && !demo.sea(col-1,row))
                        drawSprite(canvas,"coast_corner_nw",px,py);
                    if (demo.sea(col+1,row+1) && !demo.sea(col,row+1) && !demo.sea(col+1,row))
                        drawSprite(canvas,"coast_corner_se",px,py);
                    if (demo.sea(col-1,row+1) && !demo.sea(col,row+1) && !demo.sea(col-1,row))
                        drawSprite(canvas,"coast_corner_sw",px,py);
                }
                if (cell.riverMask>0 && cell.riverMask<=15) {
                    String id = col==DemoMap.ORIGIN_COL+5 && row==DemoMap.ORIGIN_ROW+3
                            ? "river_source"
                            : col==DemoMap.ORIGIN_COL+24 && row==DemoMap.ORIGIN_ROW+20
                            ? "river_estuary" : maskId("river",cell.riverMask);
                    drawSprite(canvas,id,px,py);
                }
            }
        }

        // Pass 3: tall scenery/structures, sorted by individual footprint depth.
        ArrayList<Sprite> scenery=new ArrayList<>();
        for(int sum=minX+minY;sum<=maxX+maxY;sum++) {
            for(int row=Math.max(minY,sum-maxX);row<=Math.min(maxY,sum-minX);row++) {
                int col=sum-row;
                if (!fog.isExplored(col,row)) continue;
                DemoMap.Cell cell=demo==null?null:demo.at(col,row);
                if (cell==null) {
                    float px=camera.screenX(col,row,w),py=camera.screenY(col,row,h);
                    drawFeature(canvas,px,py,world.terrain(col,row));
                } else for (String id:cell.objects) {
                    MapAssetCatalog.Entry e=art==null?null:art.entries().get(id);
                    if (e==null) continue;
                    // sortFootY is a pixel position in sprite space; offset by anchor.
                    float depth=camera.screenY(col,row,h)+(e.sortFootY-e.anchorY)*IsoCamera.ZOOM;
                    scenery.add(new Sprite(col,row,id,depth));
                }
            }
        }
        Collections.sort(scenery,new Comparator<Sprite>() {
            @Override public int compare(Sprite a,Sprite b) {
                int byY=Float.compare(a.depth,b.depth);
                return byY!=0?byY:Integer.compare(a.col-b.row,b.col-a.row);
            }
        });
        for(Sprite item:scenery)
            drawSprite(canvas,item.id,camera.screenX(item.col,item.row,w),
                    camera.screenY(item.col,item.row,h));

        // Pass 4 ALWAYS last: covers unexplored terrain and tall sprite overlap.
        for(int sum=minX+minY;sum<=maxX+maxY;sum++) {
            for(int row=Math.max(minY,sum-maxX);row<=Math.min(maxY,sum-minX);row++) {
                int col=sum-row;
                if (fog.isExplored(col,row)) continue;
                float px=camera.screenX(col,row,w),py=camera.screenY(col,row,h);
                drawDiamond(canvas,px,py,UNEXPLORED_FOG_COLOR);
                if (demo!=null && demo.at(col,row)!=null)
                    drawSprite(canvas,"fog_unexplored_01",px,py);
            }
        }
    }

    private static String maskId(String type,int bits) {
        return String.format(java.util.Locale.ROOT,"%s_mask_%02d",type,bits);
    }
    private boolean isMountain(int col,int row) {
        DemoMap.Cell c=demo==null?null:demo.at(col,row);
        return c!=null && "mountain".equals(c.terrain);
    }
    private boolean drawSprite(Canvas canvas,String id,float x,float y) {
        if(art==null || failedAssets.contains(id)) return false;
        MapAssetCatalog.Entry e=art.entries().get(id);
        if(e==null) return false;
        Bitmap bmp=bitmapCache.get(id);
        if(bmp==null) {
            try {
                bmp=art.decode(id);
                bitmapCache.put(id,bmp);
            } catch(IOException err) {
                failedAssets.add(id);
                Log.w("KOPANKA_MAP","PNG decode failed: "+id,err);
                return false;
            }
        }
        float z=IsoCamera.ZOOM;
        spriteBounds.set(x-e.anchorX*z,y-e.anchorY*z,
                         x+(e.widthPx-e.anchorX)*z,y+(e.heightPx-e.anchorY)*z);
        paint.setColor(Color.WHITE);
        paint.setStyle(Paint.Style.FILL);
        paint.setFilterBitmap(true);
        canvas.drawBitmap(bmp,null,spriteBounds,paint);
        return true;
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
