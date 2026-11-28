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
    /**
     * Keep the FULL rectangular viewport inside the diamond-shaped world.
     * The inverse-isometric projection maps screen corners to a col/row
     * margin of halfWidth/(zoom*tileWidth) + halfHeight/(zoom*tileHeight).
     * Clamping only the camera center to 0..511 leaves most of the screen
     * outside the world near its corners; clamp by the viewport margin instead.
     */
    public void constrainToViewport(int width, int height) {
        if (width <= 0 || height <= 0) return;
        float margin = width / (2f * ZOOM * TILE_WIDTH)
                     + height / (2f * ZOOM * TILE_HEIGHT);
        float min = margin;
        float max = WorldMap.SIZE - 1f - margin;
        if (min > max) {
            centerX = centerY = (WorldMap.SIZE - 1f) / 2f;
            return;
        }
        centerX = Math.max(min, Math.min(max, centerX));
        centerY = Math.max(min, Math.min(max, centerY));
    }

    public void drag(float dxScreen, float dyScreen, int width, int height) {
        float dx = dxScreen / ZOOM, dy = dyScreen / ZOOM;
        centerX -= dx / TILE_WIDTH + dy / TILE_HEIGHT;
        centerY -= dy / TILE_HEIGHT - dx / TILE_WIDTH;
        constrainToViewport(width, height);
    }
    /** Restore a saved position; viewport bounds are applied on size change. */
    public void restoreCenter(float col, float row) {
        if (Float.isNaN(col) || Float.isInfinite(col) ||
            Float.isNaN(row) || Float.isInfinite(row)) return;
        centerX = Math.max(0f, Math.min(WorldMap.SIZE - 1f, col));
        centerY = Math.max(0f, Math.min(WorldMap.SIZE - 1f, row));
    }
    public float centerCol() { return centerX; }
    public float centerRow() { return centerY; }
}
