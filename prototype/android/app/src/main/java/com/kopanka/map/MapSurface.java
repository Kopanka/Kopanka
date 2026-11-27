package com.kopanka.map;

import android.content.Context;
import android.content.SharedPreferences;
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
    private ElevationMap elevation;
    private final FogStore fog;
    private final SharedPreferences cameraPrefs;
    private static final String CAMERA_PREFS = "kopanka_map_camera_v1";
    private static final String CAMERA_COL = "center_col";
    private static final String CAMERA_ROW = "center_row";
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
    // Approved 2026-11-27: opaque graphite fog (#3B3F42) for every
    // unexplored map cell, including the out-of-world background.
    // Never read undiscovered terrain for fog.
    private static final int OUTSIDE_WORLD_COLOR = 0xFF3B3F42;
    private static final int UNEXPLORED_FOG_COLOR = 0xFF3B3F42;
    private final Path diamond = new Path();
    private final Path fogMask = new Path();
    private float downX, downY, lastX, lastY;
    private boolean moving;

    public MapSurface(Context context) {
        super(context);
        fog = new FogStore(context);
        cameraPrefs = context.getSharedPreferences(CAMERA_PREFS, Context.MODE_PRIVATE);
        if (cameraPrefs.contains(CAMERA_COL) && cameraPrefs.contains(CAMERA_ROW)) {
            camera.restoreCenter(cameraPrefs.getFloat(CAMERA_COL, 256f),
                                 cameraPrefs.getFloat(CAMERA_ROW, 254f));
        }
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
        elevation = new ElevationMap(world, demo);
        // Initial technical discovery, without introducing a hero or game mechanics.
        if (fog.reveal(256, 254, 10)) fog.save();
        setBackgroundColor(OUTSIDE_WORLD_COLOR);
    }
    @Override protected void onSizeChanged(int w, int h, int oldW, int oldH) {
        super.onSizeChanged(w, h, oldW, oldH);
        camera.constrainToViewport(w, h);
    }

    private void saveCamera() {
        cameraPrefs.edit().putFloat(CAMERA_COL, camera.centerCol())
                .putFloat(CAMERA_ROW, camera.centerRow()).apply();
    }

    @Override protected void onDetachedFromWindow() {
        saveCamera();
        super.onDetachedFromWindow();
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

        // MAP-004 fog + elevation safety underlay.
        // Raised tile tops leave portions of the original flat diamond
        // unoccupied, and opaque fog is still projected on that original
        // plane. Without the complete base layer those pixels show the
        // OUTSIDE_WORLD_COLOR (near-black), creating black seams around
        // purple fog and terraces. Cover EVERY in-world cell before any
        // elevated layer, using only exploration state for hidden cells.
        // This never reads or discloses unexplored geography.
        for (int sum=minX+minY;sum<=maxX+maxY;sum++) {
            for (int row=Math.max(minY,sum-maxX);row<=Math.min(maxY,sum-minX);row++) {
                int col=sum-row;
                float px=camera.screenX(col,row,w);
                float py=camera.screenY(col,row,h);
                if (fog.isExplored(col,row)) {
                    int kind=terrainAt(col,row);
                    int underlay=kind==WorldMap.SEA || kind==WorldMap.RIVER
                            ? 0xFF187B9A
                            : isMountainKind(kind) ? 0xFF827E6A : 0xFF91B366;
                    drawDiamond(canvas,px,py,underlay);
                }
                // Unexplored cells use the uniform graphite view background.
                // They are painted together in ONE foreground fog mask below.
            }
        }

        // Pass 1: ground + sea only for explored cells; never inspect hidden terrain.
        for(int sum=minX+minY;sum<=maxX+maxY;sum++) {
            for(int row=Math.max(minY,sum-maxX);row<=Math.min(maxY,sum-minX);row++) {
                int col=sum-row;
                if (!fog.isExplored(col,row)) continue;
                float px=camera.screenX(col,row,w), py=camera.screenY(col,row,h);
                DemoMap.Cell cell=demo == null ? null : demo.at(col,row);
                // The same PNG tiles render the entire 512x512 world, not
                // only the 32x32 hand-authored demo. No procedural grid.
                int kind=terrainAt(col,row);
                int level=elevation.at(col,row);
                float raisedY=py-level*ElevationMap.STEP_PX*IsoCamera.ZOOM;
                drawHeightWalls(canvas,px,raisedY,col,row,level);
                String base=baseTile(col,row,kind,cell);
                if (!drawSprite(canvas,base,px,raisedY))
                    drawDiamond(canvas,px,raisedY,kind==WorldMap.SEA?0xFF376F93:0xFFADC18C);
            }
        }

        // Pass 2: terrain overlays: slope -> coast -> river.
        for(int sum=minX+minY;sum<=maxX+maxY;sum++) {
            for(int row=Math.max(minY,sum-maxX);row<=Math.min(maxY,sum-minX);row++) {
                int col=sum-row;
                if (!fog.isExplored(col,row)) continue;
                DemoMap.Cell cell=demo==null?null:demo.at(col,row);
                int kind=terrainAt(col,row);
                float px=camera.screenX(col,row,w);
                float py=camera.screenY(col,row,h)-elevation.at(col,row)
                        *ElevationMap.STEP_PX*IsoCamera.ZOOM;
                // The old slope_*.png artwork is a flat tile-outline effect.
                // Its grey strokes drew long diagonal bars across raised hills
                // in v0.3.10. Do not render it over the MAP-004 height field.
                // Height-aware slope art will replace it after art QA.
                // An open-water procedural river tile must NEVER receive
                // the land/coast overlay. Previously each water tile saw
                // river neighbors and painted four sandy shore edges,
                // producing the regular yellow diamond lattice.
                boolean proceduralRiver = cell==null && kind==WorldMap.RIVER;
                if (kind!=WorldMap.SEA && !proceduralRiver) {
                    // Coast transitions border both sea and procedural
                    // wide river, but are painted on LAND cells only.
                    int coast=neighborMask(col,row,WorldMap.SEA);
                    if (demo==null || demo.at(col,row)==null) {
                        coast|=neighborMask(col,row,WorldMap.RIVER);
                    }
                    // The current shore sprites include bright cyan lines.
                    // They do not fit vertical cliffs: on elevated banks they
                    // appeared as parallel stripes floating above the river.
                    // Wait for elevation-specific coast assets before restoring.
                    if (coast!=0 && elevation.at(col,row)==0) {
                        drawSprite(canvas,maskId("coast",coast),px,py);
                        if (isSea(col+1,row-1) && !isSea(col,row-1) && !isSea(col+1,row))
                            drawSprite(canvas,"coast_corner_ne",px,py);
                        if (isSea(col-1,row-1) && !isSea(col,row-1) && !isSea(col-1,row))
                            drawSprite(canvas,"coast_corner_nw",px,py);
                        if (isSea(col+1,row+1) && !isSea(col,row+1) && !isSea(col+1,row))
                            drawSprite(canvas,"coast_corner_se",px,py);
                        if (isSea(col-1,row+1) && !isSea(col,row+1) && !isSea(col-1,row))
                            drawSprite(canvas,"coast_corner_sw",px,py);
                    }
                }
                // River segments from the 32x32 demo are composited once
                // as a continuous smoothed path after this terrain pass.
                // Outside the demo, river water is already filled in pass 1.
            }
        }

        drawDemoRiver(canvas,w,h);

        // Pass 3: tall scenery/structures, sorted by individual footprint depth.
        ArrayList<Sprite> scenery=new ArrayList<>();
        for(int sum=minX+minY;sum<=maxX+maxY;sum++) {
            for(int row=Math.max(minY,sum-maxX);row<=Math.min(maxY,sum-minX);row++) {
                int col=sum-row;
                if (!fog.isExplored(col,row)) continue;
                DemoMap.Cell cell=demo==null?null:demo.at(col,row);
                if (cell==null) {
                    String id=worldObject(col,row,world.terrain(col,row));
                    if (id!=null) addScenery(scenery,col,row,id,h);
                } else for (String id:cell.objects)
                    addScenery(scenery,col,row,id,h);
            }
        }
        Collections.sort(scenery,new Comparator<Sprite>() {
            @Override public int compare(Sprite a,Sprite b) {
                int byY=Float.compare(a.depth,b.depth);
                return byY!=0?byY:Integer.compare(a.col-a.row,b.col-b.row);
            }
        });
        for(Sprite item:scenery)
            drawSprite(canvas,item.id,camera.screenX(item.col,item.row,w),
                    camera.screenY(item.col,item.row,h)-elevation.at(item.col,item.row)
                            *ElevationMap.STEP_PX*IsoCamera.ZOOM);

        // Pass 4 ALWAYS last: a SINGLE opaque graphite path covers the
        // union of unexplored tile footprints. One fill operation eliminates
        // the internal AA seams of drawing hundreds of individual diamonds.
        fogMask.reset();
        fogMask.setFillType(Path.FillType.WINDING);
        for(int sum=minX+minY;sum<=maxX+maxY;sum++) {
            for(int row=Math.max(minY,sum-maxX);row<=Math.min(maxY,sum-minX);row++) {
                int col=sum-row;
                if (fog.isExplored(col,row)) continue;
                float px=camera.screenX(col,row,w),py=camera.screenY(col,row,h);
                addFogDiamond(px,py);
            }
        }
        paint.setStyle(Paint.Style.FILL);
        paint.setColor(UNEXPLORED_FOG_COLOR);
        paint.setAntiAlias(false);
        canvas.drawPath(fogMask,paint);
        paint.setAntiAlias(true);
    }

    /** Visible vertical faces on front-facing raised tile edges.
     *  The tile top is still a normal 128x64 PNG; these faces give actual
     *  terrain height at the approved camera angle, without adding a mesh. */
    private void drawHeightWalls(Canvas canvas,float x,float topY,int col,int row,int height) {
        if (height==0) return;
        float halfW=IsoCamera.TILE_WIDTH*IsoCamera.ZOOM/2f;
        float halfH=IsoCamera.TILE_HEIGHT*IsoCamera.ZOOM/2f;
        // A wall belongs to the transition between two cells, not to
        // either cell alone. Never draw it into an unexplored neighbor:
        // those cliff faces appeared as brown rims inside the fog.
        // The neighbor's elevation is consulted only when it is explored.
        int east=fog.isExplored(col+1,row)
                ? Math.max(0,height-elevation.at(col+1,row)) : 0;
        int south=fog.isExplored(col,row+1)
                ? Math.max(0,height-elevation.at(col,row+1)) : 0;
        paint.setStyle(Paint.Style.FILL);
        // One-level banks are a low, grass-tinted rise, not a thick
        // dark-grey platform edge. Steeper rock faces keep their separate
        // shaded material until height-aware cliff PNGs are delivered.
        boolean grassBank = !isMountainKind(terrainAt(col,row));
        if (east>0) {
            float drop=east*ElevationMap.STEP_PX*IsoCamera.ZOOM;
            diamond.reset();
            diamond.moveTo(x+halfW,topY);
            diamond.lineTo(x,topY+halfH);
            diamond.lineTo(x,topY+halfH+drop);
            diamond.lineTo(x+halfW,topY+drop);
            diamond.close();
            paint.setColor(east == 1 && grassBank ? 0xFF93AC7D
                    : east == 1 ? 0xFF9E9F8E : 0xFF827E6A);
            canvas.drawPath(diamond,paint);
        }
        if (south>0) {
            float drop=south*ElevationMap.STEP_PX*IsoCamera.ZOOM;
            diamond.reset();
            diamond.moveTo(x,topY+halfH);
            diamond.lineTo(x-halfW,topY);
            diamond.lineTo(x-halfW,topY+drop);
            diamond.lineTo(x,topY+halfH+drop);
            diamond.close();
            paint.setColor(south == 1 && grassBank ? 0xFF839E70
                    : south == 1 ? 0xFF858779 : 0xFF625F57);
            canvas.drawPath(diamond,paint);
        }
    }

    private static String maskId(String type,int bits) {
        return String.format(java.util.Locale.ROOT,"%s_mask_%02d",type,bits);
    }
    /** A shared terrain source allows artistic tiles to cross demo boundaries. */
    private int terrainAt(int col,int row) {
        DemoMap.Cell cell=demo==null?null:demo.at(col,row);
        if (cell==null) return world.terrain(col,row);
        if ("sea".equals(cell.terrain)) return WorldMap.SEA;
        if ("mountain".equals(cell.terrain)) return WorldMap.MOUNTAIN;
        if (cell.riverMask>0) return WorldMap.RIVER;
        return WorldMap.GRASS;
    }
    private static boolean isMountainKind(int kind) {
        return kind==WorldMap.MOUNTAIN || kind==WorldMap.MINE || kind==WorldMap.CAVE;
    }
    private boolean isMountain(int col,int row) {
        return world.inside(col,row) && isMountainKind(terrainAt(col,row));
    }
    private boolean isSea(int col,int row) {
        return world.inside(col,row) && terrainAt(col,row)==WorldMap.SEA;
    }
    private int neighborMask(int col,int row,int kind) {
        int mask=0;
        if (world.inside(col,row-1) && terrainAt(col,row-1)==kind) mask|=1;
        if (world.inside(col+1,row) && terrainAt(col+1,row)==kind) mask|=2;
        if (world.inside(col,row+1) && terrainAt(col,row+1)==kind) mask|=4;
        if (world.inside(col-1,row) && terrainAt(col-1,row)==kind) mask|=8;
        return mask;
    }
    private String baseTile(int col,int row,int kind,DemoMap.Cell cell) {
        // Multi-tile procedural channels need solid water, not line overlays.
        if (kind==WorldMap.SEA || (cell==null && kind==WorldMap.RIVER))
            return ((col+row)%3==0)?"water_sea_02":"water_sea_01";
        if (isMountainKind(kind)) return "ground_earth_01";
        if (kind==WorldMap.QUARRY) return "ground_sand_01";
        if (cell!=null && "meadow".equals(cell.terrain)) return "ground_meadow_01";
        int noise=(col*31+row*17+col*row*3)&0x7fffffff;
        if (kind==WorldMap.CONIFER || kind==WorldMap.DECIDUOUS)
            return noise%5==0?"ground_meadow_01":"ground_grass_01";

        return noise%11==0?"ground_grass_02":
               noise%17==0?"ground_grass_03":"ground_grass_01";
    }
    private String worldObject(int col,int row,int kind) {
        int n=col*0x45d9f3b ^ row*0x27d4eb2d ^ 0x9e3779b9;
        n^=n>>>16; n*=0x7feb352d;
        n^=n>>>15; n*=0x846ca68b;
        n=(n^(n>>>16))&0x7fffffff;
        switch(kind) {
            case WorldMap.MOUNTAIN:
                // Raised terrain carries the mass; sparse visible peaks avoid
                // the tiled wallpaper of mountain PNGs seen in Android 0.3.4.
                if (elevation.at(col,row)<3 || n%15!=0) return null;
                return n%2==0?"mountain_02":"mountain_01";
            case WorldMap.MINE:return "mine_mountain_small";
            case WorldMap.CAVE:return "cave_entrance_small";
            case WorldMap.CONIFER:return n%2==0?"forest_pine_01":"forest_pine_02";
            case WorldMap.DECIDUOUS:return n%2==0?"forest_deciduous_01":"forest_deciduous_02";
            case WorldMap.QUARRY:return "quarry_plain_01";
            case WorldMap.SETTLEMENT:return "settlement_hamlet_01";
            default:return null;
        }
    }
    private void addScenery(ArrayList<Sprite> scenery,int col,int row,String id,int h) {
        MapAssetCatalog.Entry e=art==null?null:art.entries().get(id);
        if(e==null) return;
        float depth=camera.screenY(col,row,h)-elevation.at(col,row)
                *ElevationMap.STEP_PX*IsoCamera.ZOOM
                +(e.sortFootY-e.anchorY)*IsoCamera.ZOOM;
        scenery.add(new Sprite(col,row,id,depth));
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
    /** Append one tile to the shared opaque graphite fog silhouette. */
    private void addFogDiamond(float x,float y) {
        float hw=IsoCamera.TILE_WIDTH*IsoCamera.ZOOM/2f + 0.65f;
        float hh=IsoCamera.TILE_HEIGHT*IsoCamera.ZOOM/2f + 0.65f;
        fogMask.moveTo(x,y-hh);
        fogMask.lineTo(x+hw,y);
        fogMask.lineTo(x,y+hh);
        fogMask.lineTo(x-hw,y);
        fogMask.close();
    }

    /** Continuous anti-aliased river path following the authored demo masks.
     *
     * Unlike the old river_mask_*.png segments, this is a single stroke:
     * no repeated pipe rims, sharp joints or unconnected estuary strips.
     * Height is read at discovered/rendered land, not hidden by fog.
     * The final opaque fog pass masks unexplored parts of the path.
     */
    private void drawDemoRiver(Canvas canvas,int w,int h) {
        if (demo==null) return;
        ArrayList<float[]> points=new ArrayList<>();
        int col=DemoMap.ORIGIN_COL+5, row=DemoMap.ORIGIN_ROW+3;
        int previousCol=Integer.MIN_VALUE, previousRow=Integer.MIN_VALUE;
        final int[] dc={0,1,0,-1}, dr={-1,0,1,0};
        final int[] mask={1,2,4,8}, opposite={4,8,1,2};
        for (int n=0;n<demo.width*demo.height;n++) {
            DemoMap.Cell c=demo.at(col,row);
            if(c==null || c.riverMask==0) break;
            float x=camera.screenX(col,row,w);
            float y=camera.screenY(col,row,h)
                    -elevation.at(col,row)*ElevationMap.STEP_PX*IsoCamera.ZOOM;
            points.add(new float[]{x,y});
            boolean advanced=false;
            for(int d=0;d<4;d++){
                if((c.riverMask&mask[d])==0) continue;
                int nc=col+dc[d],nr=row+dr[d];
                if(nc==previousCol && nr==previousRow) continue;
                DemoMap.Cell next=demo.at(nc,nr);
                if(next==null || (next.riverMask&opposite[d])==0) continue;
                previousCol=col;previousRow=row;col=nc;row=nr;
                advanced=true;break;
            }
            if(!advanced) break;
        }
        if(points.size()<2) return;
        Path water=new Path();
        float[] first=points.get(0);
        water.moveTo(first[0],first[1]);
        for(int i=1;i<points.size();i++){
            float[] a=points.get(i-1),b=points.get(i);
            water.quadTo(a[0],a[1],(a[0]+b[0])/2f,(a[1]+b[1])/2f);
        }
        float[] last=points.get(points.size()-1);
        water.lineTo(last[0],last[1]);

        paint.setStyle(Paint.Style.STROKE);
        paint.setStrokeCap(Paint.Cap.ROUND);
        paint.setStrokeJoin(Paint.Join.ROUND);
        paint.setAntiAlias(true);
        paint.setColor(0xFFC1B885);
        paint.setStrokeWidth(19f*IsoCamera.ZOOM);
        canvas.drawPath(water,paint);
        paint.setColor(0xFF187B9A);
        paint.setStrokeWidth(15f*IsoCamera.ZOOM);
        canvas.drawPath(water,paint);
        // Delicate central glint avoids a hard fake-pipe seam.
        paint.setColor(0x665FD3DA);
        paint.setStrokeWidth(1.6f*IsoCamera.ZOOM);
        canvas.drawPath(water,paint);
        paint.setStyle(Paint.Style.FILL);
        paint.setStrokeCap(Paint.Cap.BUTT);
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
                if(moving) saveCamera();
                if(!moving){
                    int col=Math.round(camera.colFromScreen(event.getX(),event.getY(),getWidth(),getHeight()));
                    int row=Math.round(camera.rowFromScreen(event.getX(),event.getY(),getWidth(),getHeight()));
                    if(world.inside(col,row)&&fog.reveal(col,row,5)){fog.save();invalidate();}
                    performClick();
                }
                return true;
            case MotionEvent.ACTION_CANCEL: if(moving) saveCamera(); return true;
            default:return true;
        }
    }
    @Override public boolean performClick(){super.performClick();return true;}
}
