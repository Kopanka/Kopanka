package com.kopanka;

import android.app.Activity;
import android.os.Bundle;
import com.kopanka.map.MapSurface;

/** MAP-002A: isolated, map-only technical preview; legacy MainActivity stays intact. */
public final class MapPreviewActivity extends Activity {
    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        setContentView(new MapSurface(this));
    }
}
