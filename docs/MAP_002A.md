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

## Stable debug APK signing (2026-11-23)

Device install report: Android refused build #18 as an update to older MAP-002A.
The signatures were different: previous test cert SHA-256 starts `37:18:45`,
build #18 starts `DC:EA:C5`. GitHub hosted debug builds normally receive a
new default debug keystore on each fresh runner.

**One-time migration to a separate app:** the stable test application ID is now
`com.kopanka.maptest.stable` (label: KOPANKA Map Test Stable). The existing
`com.kopanka.maptest` and production `com.kopanka` apps remain installed and
unchanged; Android treats the stable test as an additional, independent app.
Prior exploration progress remains in the old test app and is not imported.

**Future updates to this stable test:** Gradle's debug build uses the fixed
`maptestdebug` alias from `prototype/android/ci/maptest-debug.keystore.b64`,
expanded by GitHub Actions before the build. CI checks the fixture SHA-256 and
the APK signer's certificate fingerprint on every build; the cert SHA-256 is:
`6E:3F:1C:47:F5:D5:E0:15:68:60:21:60:6D:2B:BA:F9:A8:B2:39:2E:BA:1C:DD:9C:AE:4C:2E:11:03:6E:9D:29`.
For local builds, first run from repository root:
```sh
base64 --decode prototype/android/ci/maptest-debug.keystore.b64 > prototype/android/ci/maptest-debug.keystore
gradle --project-dir prototype/android :app:assembleDebug
```

**SECURITY:** this debug-only key is intentionally PUBLIC and has a known
password. It does **not** identify a trusted publisher. Never use it for a
production/release app, app-store publication, or any sensitive data. An eventual
production signing key must be private and stored in a secret manager. This
test-only signature is suitable solely for repeatable installation of the
separate MAP-002A proof-of-concept on a test device.

Acceptance: install the new stable app beside both older apps, verify same
fingerprint across two CI debug builds, then confirm Android can update
the stable app without uninstalling and without losing fog state.

## Fog vs out-of-world diagnostic (2026-11-23)

Temporary test-only palette in `MapSurface.java`:
- **Purple** `#51435F`: unexplored logical cells **inside** the 512x512 world.
  Opaque diamonds cover hidden geography. Tap these cells to reveal terrain.
- **Dark teal** `#142021`: area **outside** the world's logical footprint.
  Tapping it must not reveal a tile.
- Regular green/blue/gray: explored terrain, unchanged.
- Zoom 1.2x and screen-space camera clamps remain unchanged.

The diagnostic color is not final art; remove it when the camera-edge test
is accepted and the final fog shader/art is available. This screenshot-based
test must compare right edge, land edge, and bottom sea edge. At every
edge, clearly identify whether the empty region is purple fog (valid) or
dark-teal outside-world space (camera or world boundary). Record both
observed behavior and screenshots before coordinator acceptance.

Stable test package remains `com.kopanka.maptest.stable`; incremented
`versionCode` from 2 to 3, preserving data and using the same debug signing key.
