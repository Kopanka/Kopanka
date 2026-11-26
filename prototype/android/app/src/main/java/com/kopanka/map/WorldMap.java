package com.kopanka.map;

/** Deterministic logical 512x512 world. Graphics are placeholders, not final art. */
public final class WorldMap {
    public static final int SIZE = 512;
    public static final int CHUNK_SIZE = 32;
    public static final int GRASS = 0, MOUNTAIN = 1, RIVER = 2, SEA = 3;
    public static final int CONIFER = 4, DECIDUOUS = 5, QUARRY = 6, MINE = 7;
    public static final int CAVE = 8, SETTLEMENT = 9;
    public static final int DEMO_MIN = 240, DEMO_MAX = 271;
    public boolean inside(int x, int y) {
        return x >= 0 && y >= 0 && x < SIZE && y < SIZE;
    }
    public int terrain(int x, int y) {
        if (!inside(x, y)) return SEA;
        // A deliberately compact 32x32 geography test: mountain -> river -> sea.
        if (x >= DEMO_MIN && x <= DEMO_MAX && y >= DEMO_MIN && y <= DEMO_MAX) {
            if (y >= 266 + (int)Math.round(1.5 * Math.sin(x * .35))) return SEA;
            int riverX = 255 + (int)Math.round(2.0 * Math.sin((y - 240) * .26));
            if (Math.abs(x - riverX) <= 1) return RIVER;
            if (y <= 247 && x >= 245 && x <= 266) {
                if (x == 250 && y == 244) return MINE;
                if (x == 262 && y == 245) return CAVE;
                return MOUNTAIN;
            }
            if (x == 244 && y == 260) return QUARRY;
            if (x == 266 && y == 260) return SETTLEMENT;
            if (x < 252 && y >= 249 && y <= 258) return CONIFER;
            if (x > 258 && y >= 250 && y <= 261) return DECIDUOUS;
            return GRASS;
        }
        // Outside the showcase: stable inexpensive terrain without storing 262k objects.
        int coastline = 459 + (int)Math.round(8 * Math.sin(x * .027));
        if (y >= coastline) return SEA;
        int riverX = 255 + (int)Math.round(7 * Math.sin(y * .032));
        if (Math.abs(x - riverX) <= 1) return RIVER;
        if (y < 148 && x > 130 && x < 385) return MOUNTAIN;
        int noise = Math.abs((x * 73 + y * 131 + (x * y) % 31) % 101);
        if (noise < 7 && y > 170 && y < 400) return CONIFER;
        if (noise < 14 && y > 170 && y < 400) return DECIDUOUS;
        return GRASS;
    }
    public static int chunk(int coordinate) {
        return coordinate / CHUNK_SIZE;
    }
}
