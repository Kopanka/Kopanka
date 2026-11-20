package com.kopanka.map;

/** Immutable zoom, no rotation. Positions use float until draw time. */
public final class IsoCamera {
    public static final float TILE_WIDTH = 128f, TILE_HEIGHT = 64f, ZOOM = 1.2f;
    private float centerX = 256f, centerY = 254f;

    public float worldX(float col, float row) { return (col - row) * TILE_WIDTH / 2f; }
    public float worldY(float col, float row) { return (col + row) * TILE_HEIGHT / 2f; }
    public float screenX(float col, float row, int width) {
        return width / 2f + (worldX(col, row) - worldX(centerX, centerY)) * ZOOM;
    }
    public float screenY(float col, float row, int height) {
        return height / 2f + (worldY(col, row) - worldY(centerX, centerY)) * ZOOM;
    }
    public float colFromScreen(float sx, float sy, int width, int height) {
        float a = (sx - width / 2f) / ZOOM + worldX(centerX, centerY);
        float b = (sy - height / 2f) / ZOOM + worldY(centerX, centerY);
        return a / TILE_WIDTH + b / TILE_HEIGHT;
    }
    public float rowFromScreen(float sx, float sy, int width, int height) {
        float a = (sx - width / 2f) / ZOOM + worldX(centerX, centerY);
        float b = (sy - height / 2f) / ZOOM + worldY(centerX, centerY);
        return b / TILE_HEIGHT - a / TILE_WIDTH;
    }
    public void drag(float dxScreen, float dyScreen) {
        float dx = dxScreen / ZOOM, dy = dyScreen / ZOOM;
        centerX -= dx / TILE_WIDTH + dy / TILE_HEIGHT;
        centerY -= dy / TILE_HEIGHT - dx / TILE_WIDTH;
        centerX = Math.max(0, Math.min(WorldMap.SIZE - 1, centerX));
        centerY = Math.max(0, Math.min(WorldMap.SIZE - 1, centerY));
    }
    public float centerCol() { return centerX; }
    public float centerRow() { return centerY; }
}
