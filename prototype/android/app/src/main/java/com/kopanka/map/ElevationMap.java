package com.kopanka.map;

/**
 * MAP-004: stable, bounded height field for the 512x512 isometric preview.
 *
 * Height is in logical steps, not geometry mesh pixels. The artist-authored
 * 32x32 demo owns its elevations (0..2); procedural mountain areas use a
 * deterministic coarse value field (no per-frame random, no saved array).
 * This is a height/rendering prototype, not the final authored world geography.
 */
public final class ElevationMap {
    public static final int MAX_LEVEL = 5;
    public static final float STEP_PX = 13f;

    private final WorldMap world;
    private final DemoMap demo;
    // 262,144 bytes of lazy terrain heights rather than re-scanning a
    // seven-by-seven water neighborhood on every Android frame.
    // 0 = uncached, height is stored as (1 + level) for mountain cells.
    private final byte[] heightCache = new byte[WorldMap.SIZE * WorldMap.SIZE];

    public ElevationMap(WorldMap world, DemoMap demo) {
        this.world = world;
        this.demo = demo;
    }

    private static float smooth(float t) {
        return t * t * (3f - 2f * t);
    }

    private static float hash(int x, int y) {
        int n = x * 374761393 + y * 668265263 + 1442695041;
        n = (n ^ (n >>> 13)) * 1274126177;
        n ^= n >>> 16;
        return (n & 0x7fffffff) / 2147483647f;
    }

    private static float valueNoise(int x, int y, int spacing) {
        // Math.floorDiv/floorMod are unavailable on some minSdk=23 devices.
        int ix = (int) Math.floor(x / (double) spacing);
        int iy = (int) Math.floor(y / (double) spacing);
        float u = smooth((x - ix * spacing) / (float) spacing);
        float v = smooth((y - iy * spacing) / (float) spacing);
        float n00 = hash(ix, iy), n10 = hash(ix + 1, iy);
        float n01 = hash(ix, iy + 1), n11 = hash(ix + 1, iy + 1);
        float a = n00 + (n10 - n00) * u;
        float b = n01 + (n11 - n01) * u;
        return a + (b - a) * v;
    }

    public int at(int col, int row) {
        if (!world.inside(col, row)) return 0;
        DemoMap.Cell c = demo == null ? null : demo.at(col, row);
        if (c != null)
            return Math.max(0, Math.min(MAX_LEVEL, c.elevation));
        int kind = world.terrain(col, row);
        if (kind != WorldMap.MOUNTAIN && kind != WorldMap.MINE
                && kind != WorldMap.CAVE) return 0;
        int index = row * WorldMap.SIZE + col;
        if (heightCache[index] != 0) return heightCache[index] - 1;

        // A combination of broad mountain ridges and smaller foothills.
        // All cells of a ridge share the same smooth spatial height field.
        float broad = valueNoise(col, row, 23);
        float detail = valueNoise(col + 113, row - 79, 9);
        float ridge = (float) Math.pow(1f - Math.abs(broad * 2f - 1f), 1.35);
        float field = 0.58f * ridge + 0.42f * detail;
        int h = 1 + Math.round(field * 4f);

        // Procedural canyon transition: high land must not jump straight
        // from a level-5 cliff to level-0 water. In a 3-cell river corridor,
        // clamp the bank to a graded height field (1,2,3), rising inland.
        // Do NOT modify the authored 32x32 demo elevations.
        int nearestWater = 4;
        for (int dy = -3; dy <= 3; dy++) {
            for (int dx = -3; dx <= 3; dx++) {
                int radius = Math.max(Math.abs(dx), Math.abs(dy));
                if (radius >= nearestWater) continue;
                int nx = col + dx, ny = row + dy;
                if (!world.inside(nx, ny)) continue;
                // Respect authored terrain within the demo region, even
                // when the procedural height field extends near its edge.
                DemoMap.Cell near = demo == null ? null : demo.at(nx, ny);
                int nextKind;
                if (near != null) {
                    nextKind = "sea".equals(near.terrain) ? WorldMap.SEA
                            : near.riverMask > 0 ? WorldMap.RIVER : WorldMap.GRASS;
                } else nextKind = world.terrain(nx, ny);
                if (nextKind == WorldMap.SEA || nextKind == WorldMap.RIVER)
                    nearestWater = radius;
            }
        }
        if (nearestWater < 4) h = Math.min(h, 1 + nearestWater);
        h = Math.max(1, Math.min(MAX_LEVEL, h));
        heightCache[index] = (byte) (h + 1);
        return h;
    }
}
