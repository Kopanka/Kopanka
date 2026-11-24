package com.kopanka.map;

import android.content.res.AssetManager;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;
import java.io.ByteArrayOutputStream;
import java.io.FileNotFoundException;
import java.io.IOException;
import java.io.InputStream;
import java.util.Collections;
import java.util.HashSet;
import java.util.Set;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * MAP-003: read and validate artist-supplied assets; not yet connected to rendering.
 * Assets belong in app/src/main/assets/map/; PNGs are never density scaled.
 */
public final class MapAssetCatalog {
    public static final String ROOT = "map/";
    private static final int MAX_ENTRIES = 4096;
    private static final Set<String> LAYERS;
    static {
        Set<String> names = new HashSet<>();
        Collections.addAll(names, "ground", "slope", "coast", "water", "river",
                           "scenery", "structure", "fog");
        LAYERS = Collections.unmodifiableSet(names);
    }
    private final AssetManager assetManager;
    private final Map<String, Entry> entries;

    public static final class Entry {
        public final String id, path, layer, version, license, variant, adjacencyMask;
        public final int widthPx, heightPx, anchorX, anchorY;
        public final int footprintCols, footprintRows;
        public final float sortFootY;

        private Entry(JSONObject json) throws JSONException, IOException {
            id = required(json, "id");
            path = required(json, "path");
            layer = required(json, "layer");
            if (!LAYERS.contains(layer)) throw new IOException("Invalid layer: " + layer);
            version = required(json, "version");
            license = required(json, "license");
            widthPx = strictInteger(json, "widthPx");
            heightPx = strictInteger(json, "heightPx");
            anchorX = strictInteger(json, "anchorX");
            anchorY = strictInteger(json, "anchorY");
            footprintCols = strictInteger(json, "footprintCols");
            footprintRows = strictInteger(json, "footprintRows");
            sortFootY = (float)json.getDouble("sortFootY");
            variant = optionalString(json, "variant");
            adjacencyMask = optionalString(json, "adjacencyMask");
            if (widthPx < 1 || heightPx < 1 || widthPx > 8192 || heightPx > 8192)
                throw new IOException("Invalid dimensions: " + id);
            if (footprintCols < 1 || footprintRows < 1 || footprintCols > 64 || footprintRows > 64)
                throw new IOException("Invalid footprint: " + id);
            if (anchorX < 0 || anchorX > widthPx || anchorY < 0 || anchorY > heightPx)
                throw new IOException("Invalid anchor: " + id);
            if (Float.isNaN(sortFootY) || Float.isInfinite(sortFootY))
                throw new IOException("Invalid sortFootY: " + id);
            if (!path.endsWith(".png") || path.startsWith("/") || path.contains("..")
                    || path.contains("\\") || path.indexOf(':') >= 0)
                throw new IOException("Invalid PNG path: " + id);
            if ("ground".equals(layer) && footprintCols == 1 && footprintRows == 1
                    && (widthPx != 128 || heightPx != 64 || anchorX != 64 || anchorY != 32))
                throw new IOException("Base ground tile must be 128x64 anchor (64,32): " + id);
        }
    }

    private static String required(JSONObject json, String name) throws JSONException, IOException {
        String value = json.getString(name);
        if (value.trim().isEmpty()) throw new IOException("Empty field: " + name);
        return value;
    }

    private static int strictInteger(JSONObject json, String name)
            throws JSONException, IOException {
        Object value = json.get(name);
        if (!(value instanceof Integer) && !(value instanceof Long))
            throw new IOException("Non-integer field: " + name);
        long n = ((Number)value).longValue();
        if (n < Integer.MIN_VALUE || n > Integer.MAX_VALUE)
            throw new IOException("Integer out of range: " + name);
        return (int)n;
    }

    private static String optionalString(JSONObject json, String name)
            throws JSONException, IOException {
        if (!json.has(name)) return "";
        Object value = json.get(name);
        if (!(value instanceof String))
            throw new IOException("Non-string field: " + name);
        return (String)value;
    }

    private MapAssetCatalog(AssetManager manager, Map<String, Entry> entries) {
        this.assetManager = manager;
        this.entries = Collections.unmodifiableMap(entries);
    }

    /** Missing manifest is expected until approved art is delivered. */
    public static MapAssetCatalog load(AssetManager manager) throws IOException {
        InputStream opened;
        try {
            opened = manager.open(ROOT + "manifest.json");
        } catch (FileNotFoundException missing) {
            return new MapAssetCatalog(manager, new LinkedHashMap<String, Entry>());
        }
        try (InputStream input = opened) {
            ByteArrayOutputStream out = new ByteArrayOutputStream();
            byte[] buffer = new byte[4096];
            int count;
            while ((count = input.read(buffer)) != -1) {
                if (out.size() + count > 1048576) throw new IOException("Manifest too large");
                out.write(buffer, 0, count);
            }
            JSONObject json = new JSONObject(out.toString("UTF-8"));
            if (strictInteger(json, "schemaVersion") != 1)
                throw new IOException("Unsupported map asset schemaVersion");
            JSONArray assets = json.getJSONArray("assets");
            if (assets.length() == 0 || assets.length() > MAX_ENTRIES)
                throw new IOException("Invalid map asset count");
            Map<String, Entry> entries = new LinkedHashMap<>();
            for (int i = 0; i < assets.length(); i++) {
                Entry entry = new Entry(assets.getJSONObject(i));
                if (entries.put(entry.id, entry) != null)
                    throw new IOException("Duplicate asset id: " + entry.id);
            }
            return new MapAssetCatalog(manager, entries);
        } catch (JSONException error) {
            throw new IOException("Invalid map manifest", error);
        }
    }

    public boolean isEmpty() { return entries.isEmpty(); }
    public Map<String, Entry> entries() { return entries; }

    /** Load one bitmap on demand. The caller owns its lifecycle/cache. */
    public Bitmap decode(String assetId) throws IOException {
        Entry entry = entries.get(assetId);
        if (entry == null) throw new IOException("Unknown map asset: " + assetId);
        BitmapFactory.Options options = new BitmapFactory.Options();
        options.inScaled = false;
        try (InputStream input = assetManager.open(ROOT + entry.path)) {
            Bitmap image = BitmapFactory.decodeStream(input, null, options);
            if (image == null) throw new IOException("Unable to decode: " + entry.path);
            if (image.getWidth() != entry.widthPx || image.getHeight() != entry.heightPx) {
                image.recycle();
                throw new IOException("PNG size differs from manifest: " + entry.id);
            }
            return image;
        }
    }
}
