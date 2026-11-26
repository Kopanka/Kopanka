package com.kopanka.map;

import android.content.res.AssetManager;
import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/**
 * MAP-003 technical demonstration. 32x32 data occupies a small region of the
 * unchanged 512x512 logical world; index order is cells[row][col].
 */
public final class DemoMap {
    public static final int ORIGIN_COL = 240;
    public static final int ORIGIN_ROW = 238;
    public final int width, height;
    private final Cell[][] cells;

    public static final class Cell {
        public final String terrain;
        public final int elevation, riverMask, coastMask;
        public final List<String> objects;
        Cell(JSONObject json) throws JSONException {
            terrain = json.getString("terrain");
            elevation = json.optInt("elevation");
            riverMask = json.optInt("riverMask");
            coastMask = json.optInt("coastMask");
            List<String> objects = new ArrayList<>();
            JSONArray values = json.optJSONArray("objects");
            if (values != null) for (int i = 0; i < values.length(); i++)
                objects.add(values.getString(i));
            this.objects = Collections.unmodifiableList(objects);
        }
    }

    private DemoMap(JSONObject json) throws JSONException, IOException {
        width = json.getInt("width");
        height = json.getInt("height");
        if (width != 32 || height != 32)
            throw new IOException("MAP-003 demo must be 32x32");
        JSONArray rows = json.getJSONArray("cells");
        if (rows.length() != height) throw new IOException("Wrong demo row count");
        cells = new Cell[height][width];
        for (int row = 0; row < height; row++) {
            JSONArray cols = rows.getJSONArray(row);
            if (cols.length() != width) throw new IOException("Wrong demo col count at " + row);
            for (int col = 0; col < width; col++)
                cells[row][col] = new Cell(cols.getJSONObject(col));
        }
    }

    public static DemoMap load(AssetManager assets) throws IOException {
        try (InputStream in = assets.open(MapAssetCatalog.ROOT + "demo/map_32x32.json")) {
            ByteArrayOutputStream out = new ByteArrayOutputStream();
            byte[] b = new byte[4096];
            int n;
            while ((n = in.read(b)) != -1) {
                if (out.size() + n > 1024 * 1024)
                    throw new IOException("Demo map too large");
                out.write(b, 0, n);
            }
            return new DemoMap(new JSONObject(out.toString("UTF-8")));
        } catch (JSONException e) {
            throw new IOException("Invalid MAP-003 demo", e);
        }
    }

    public Cell at(int globalCol, int globalRow) {
        int col = globalCol - ORIGIN_COL, row = globalRow - ORIGIN_ROW;
        if (row < 0 || row >= height || col < 0 || col >= width) return null;
        return cells[row][col];
    }

    public boolean sea(int col, int row) {
        Cell cell = at(col, row);
        return cell != null && "sea".equals(cell.terrain);
    }
}
