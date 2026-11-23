# MAP-002A — Android technical map foundation

Status: implementation preview / not accepted, 2026-11-20.

## Scope
- 512x512 logical cells, 32x32 chunk coordinates.
- 128x64 logical isometric ground footprint; anchor (64,32), 1.2x fixed camera.
- Viewport culling using inverse projection; no full-world paint loop.
- Temporary deterministic geography in the 32x32 showcase (240..271) with mountains,
  river, coastline/sea, both forests, mine in mountains, quarry on plain, cave, settlement.
- Revealed-cell mask stored locally as one Base64-encoded BitSet.
- No hero, menus, transport, economy, advertising, or finalized art.

## Launch and test
In this branch, AndroidManifest starts MapPreviewActivity. Legacy MainActivity remains
in the repository and is not used by the preview.

Run from `prototype/android` with JDK 17 / Android SDK 35 / Gradle 8.9:
```
gradle :app:assembleDebug
```
Install `app/build/outputs/apk/debug/app-debug.apk`.

- Drag one finger to pan. Fixed scale, no pinch zoom and no rotation.
- Tap a tile to reveal nearby cells. Close and reopen to verify persistence.
- Pan across the 32x32 demo. Verify mountain -> river -> sea, both forest types,
  mine in mountain and quarry on plain.
- Test on real device: FPS, memory, seams, screen edges, rotation lifecycle, save/relaunch.
- Screenshots and device/model/build details required for acceptance.

## Known limits
These are colored Canvas placeholders, NOT final PNG assets. Coast/water transitions
and high-sprite alpha bleed will be verified after art integration. The procedural
outer 512x512 area is not a finished geographical world. Current renderer is a
prototype on Android Canvas, not a verified production engine. No hardware performance
measurement or signed release APK is claimed.

A coordinator must approve MAP-001 in docs/DECISIONS.md before final asset production.

## MAP-002A camera-edge fix (2026-11-23)
After device testing of land and sea borders, camera movement now clamps the entire
rectangular viewport to the world (0..511 logical cell centers), based on inverse
isometric screen-corner projection and the fixed 1.2x zoom. This avoids large
out-of-world black areas near the diamond's tips; fog INSIDE the world is unchanged.
The camera constraint is recalculated on Android view size changes and each drag.

Retest on the separate `com.kopanka.maptest` app: pan to all 4 world sides and
diamond corners, including a land and a sea end. The screen should no longer be
dominated by empty out-of-world background. Ensure one-finger panning remains
smooth, zoom remains fixed, and explored cells still persist after restart.
Dark unexplored cells remain legitimate fog; test may need tapping to reveal them.
Status stays draft until physical device regression checks finish.
