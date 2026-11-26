package com.kopanka.map;

import android.content.Context;
import android.content.SharedPreferences;
import android.util.Base64;
import java.util.BitSet;

/** 262,144 exploration bits, persisted as one versioned compact value. */
public final class FogStore {
    private static final String PREFS = "kopanka_map_002a";
    private static final String KEY = "explored_v1";
    private final SharedPreferences preferences;
    private final BitSet explored = new BitSet(WorldMap.SIZE * WorldMap.SIZE);

    public FogStore(Context context) {
        preferences = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE);
        String encoded = preferences.getString(KEY, "");
        if (!encoded.isEmpty()) {
            try {
                byte[] bytes = Base64.decode(encoded, Base64.NO_WRAP);
                if (bytes.length <= WorldMap.SIZE * WorldMap.SIZE / 8)
                    explored.or(BitSet.valueOf(bytes));
            } catch (IllegalArgumentException ignored) {
                // Corrupt or legacy save: keep an empty map, never crash.
            }
        }
    }
    public boolean isExplored(int col, int row) {
        return col >= 0 && row >= 0 && col < WorldMap.SIZE && row < WorldMap.SIZE
            && explored.get(row * WorldMap.SIZE + col);
    }
    public boolean reveal(int col, int row, int radius) {
        boolean changed = false;
        for (int dy = -radius; dy <= radius; dy++)
            for (int dx = -radius; dx <= radius; dx++) {
                if (dx * dx + dy * dy > radius * radius) continue;
                int x = col + dx, y = row + dy;
                if (x < 0 || y < 0 || x >= WorldMap.SIZE || y >= WorldMap.SIZE) continue;
                int index = y * WorldMap.SIZE + x;
                if (!explored.get(index)) { explored.set(index); changed = true; }
            }
        return changed;
    }
    public void save() {
        preferences.edit().putString(KEY, Base64.encodeToString(explored.toByteArray(), Base64.NO_WRAP)).apply();
    }
}
