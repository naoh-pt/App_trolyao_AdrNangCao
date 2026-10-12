# Stage 5 Implementation Report: Persistent Animation FPS Settings & Preview

**Project:** `VirtualAssistant` (Android)  
**Package:** `com.example.assistant`  
**Date:** 2026-10-08  
**Status:** Complete  

---

## 1. Branch and Baseline Commit

- **Branch:** `feature/android-integration`
- **Baseline Commit:** `9b5ef54` (`9b5ef54 complete chang 4ab`)

---

## 2. Architecture and Single Source of Truth

To provide safe, consistent runtime control over animation playback speed across the entire application without mutating static catalog constants or creating scattered defaults, an immutable domain model was created:

[`com.example.assistant.domain.AnimationFpsSettings`](file:///d:/nam5/semester_1/advance_android/01_trolyAI/troLyAo_ani/android/app/src/main/java/com/example/assistant/domain/AnimationFpsSettings.kt)

### Key Architectural Decisions:
1. **Single Source of Truth:**
   - Defines default FPS values:
     - `idle`: 5 FPS
     - `thinking`: 8 FPS
     - `talk`: 10 FPS
     - `happy`: 10 FPS
     - `sad`: 8 FPS
     - `surprised`: 10 FPS
   - Defines allowed bounds:
     - `MIN_FPS`: 4
     - `MAX_FPS`: 20
     - `clampFps(fps)`: enforces `4..20` range
   - Defines action key constants: `"idle"`, `"thinking"`, `"talk"`, `"happy"`, `"sad"`, `"surprised"`.
2. **Catalog Cleanliness:**
   - `CharacterFrameCatalog` references `AnimationFpsSettings.DEFAULT_*_FPS` directly.
   - `CharacterFrameCatalog` remains strictly immutable at runtime and is never mutated.
3. **Pure Helpers:**
   - `fpsFor(actionName: String): Int`: returns configured FPS or clamped default.
   - `withFps(actionName: String, newFps: Int): AnimationFpsSettings`: returns clamped immutable copy.
   - `withStep(actionName: String, delta: Int): AnimationFpsSettings`: returns clamped copy adjusted by `delta`.
   - `applyOverride(baseSpec: CharacterAnimationSpec): CharacterAnimationSpec`: returns a copy of `baseSpec` with the effective FPS applied, preserving the frame array, action name, and playback mode.

---

## 3. DataStore Persistence

Extended the existing [`SettingsStore.kt`](file:///d:/nam5/semester_1/advance_android/01_trolyAI/troLyAo_ani/android/app/src/main/java/com/example/assistant/data/local/SettingsStore.kt) preferences DataStore (`"settings"`). No secondary DataStore file was created.

### Preference Keys:
```kotlin
private val idleFpsKey = intPreferencesKey("fps_idle")
private val thinkingFpsKey = intPreferencesKey("fps_thinking")
private val talkFpsKey = intPreferencesKey("fps_talk")
private val happyFpsKey = intPreferencesKey("fps_happy")
private val sadFpsKey = intPreferencesKey("fps_sad")
private val surprisedFpsKey = intPreferencesKey("fps_surprised")
```

### Persistence Features:
- **Observable Flow:**
  `val animationFpsSettings: Flow<AnimationFpsSettings>` emits whenever any key updates.
  Missing values fall back to defaults; loaded values are clamped via `AnimationFpsSettings.clampFps(...)`.
- **Atomic Mutation Operations:**
  - `adjustFps(actionName: String, delta: Int)`: Reads the current value inside `context.dataStore.edit`, adds delta, clamps, and saves.
  - `setFps(actionName: String, fps: Int)`: Clamps and saves the exact FPS.
  - `resetFpsToDefaults()`: Restores all six keys to their default constants (`5, 8, 10, 10, 8, 10`).
- **Isolation & Race Protection:**
  - Modifying one action modifies only its specific preference key, leaving the other five preferences (as well as `baseUrlKey` and `clientIdKey`) completely intact.
  - DataStore `.edit` serialization guarantees protection against lost updates or out-of-range race conditions during rapid user taps.
  - Zero DataStore reads occur inside Compose animation frame clocks.

---

## 4. App-Wide Settings Propagation

Instead of passing settings down across intermediate view models or polling from disk, settings are propagated through Compose architecture:

1. **Root Observation:**
   In [`MainActivity.kt`](file:///d:/nam5/semester_1/advance_android/01_trolyAI/troLyAo_ani/android/app/src/main/java/com/example/assistant/MainActivity.kt), `settingsStore.animationFpsSettings` is collected once using `collectAsStateWithLifecycle(initialValue = AnimationFpsSettings.DEFAULT)`.
2. **CompositionLocal:**
   Provided via `CompositionLocalProvider(LocalAnimationFpsSettings provides fpsSettings)`.
3. **Transparent Consumption:**
   In [`CharacterAvatar.kt`](file:///d:/nam5/semester_1/advance_android/01_trolyAI/troLyAo_ani/android/app/src/main/java/com/example/assistant/ui/components/CharacterAvatar.kt):
   ```kotlin
   @Composable
   fun CharacterAvatar(
       state: CharacterState,
       emotion: Emotion,
       modifier: Modifier = Modifier,
       fpsSettings: AnimationFpsSettings = LocalAnimationFpsSettings.current,
       restartKey: Any? = null,
       onOneShotFinished: () -> Unit = {},
   ) {
       val baseSpec = animationSpecFor(state, emotion)
       val effectiveSpec = fpsSettings.applyOverride(baseSpec)
       ...
   }
   ```
4. **Zero Impact on ChatViewModel:**
   Neither `ChatViewModel`, backend DTOs, nor `HomeScreen` require manual FPS passing. All screens automatically render with the user's saved FPS.

---

## 5. Preview & Reliable Replay Design

Inside [`SettingsScreen.kt`](file:///d:/nam5/semester_1/advance_android/01_trolyAI/troLyAo_ani/android/app/src/main/java/com/example/assistant/ui/settings/SettingsScreen.kt) and [`SettingsViewModel.kt`](file:///d:/nam5/semester_1/advance_android/01_trolyAI/troLyAo_ani/android/app/src/main/java/com/example/assistant/ui/settings/SettingsViewModel.kt):

- **Shared Preview:** One dedicated preview area at a fixed, stable height (`240.dp`) displays the selected animation with `ContentScale.Fit` anchored to `Alignment.BottomCenter`.
- **Selected Action State:** Tracked by `ui.selectedPreviewAction` in `SettingsUiState`.
- **Deterministic Replay Key:**
  [`CharacterAnimationPlayer.kt`](file:///d:/nam5/semester_1/advance_android/01_trolyAI/troLyAo_ani/android/app/src/main/java/com/example/assistant/ui/character/CharacterAnimationPlayer.kt) introduces a defaulted `restartKey: Any? = null`:
  ```kotlin
  var currentFrameIndex by remember(spec, restartKey) { mutableIntStateOf(0) }
  LaunchedEffect(spec, restartKey, lifecycleOwner) { ... }
  ```
  When "Phát lại" is tapped or when a different action is selected for preview ("Xem"), `vm.replayPreview()` / `vm.selectPreviewAction(...)` increments `replayKey`. This cleanly resets elapsed time, frame index, and one-shot completion without any temporary fake animation switching or arbitrary delay timers.
- **Preview Independence:** The preview invokes an empty callback `{}` for `onOneShotFinished`. It has zero interaction with `ChatViewModel` or network requests.
- **Accessibility:**
  - Each minus and plus button has a clear text symbol and descriptive `contentDescription` (e.g. `"Giảm tốc độ cho Chờ"`).
  - Selected preview action is communicated via row highlight, `"Đang xem"` button text, and `"Đang xem: Chờ (5 FPS)"` header text (never by color alone).
  - Current FPS is clearly displayed as text (`"$currentFps FPS"`).

---

## 6. Files Changed and Added

| File | Status | Description |
|---|---|---|
| [`domain/AnimationFpsSettings.kt`](file:///d:/nam5/semester_1/advance_android/01_trolyAI/troLyAo_ani/android/app/src/main/java/com/example/assistant/domain/AnimationFpsSettings.kt) | **Added** | Immutable model, bounds (4..20), defaults (5,8,10,10,8,10), `applyOverride`, and `LocalAnimationFpsSettings`. |
| [`ui/character/CharacterFrameResources.kt`](file:///d:/nam5/semester_1/advance_android/01_trolyAI/troLyAo_ani/android/app/src/main/java/com/example/assistant/ui/character/CharacterFrameResources.kt) | **Modified** | Referenced `AnimationFpsSettings` constants in `CharacterFrameCatalog` and added `specForAction(actionName)`. |
| [`data/local/SettingsStore.kt`](file:///d:/nam5/semester_1/advance_android/01_trolyAI/troLyAo_ani/android/app/src/main/java/com/example/assistant/data/local/SettingsStore.kt) | **Modified** | Added 6 DataStore keys, `animationFpsSettings` flow, `adjustFps`, `setFps`, `resetFpsToDefaults`. |
| [`ui/character/CharacterAnimationPlayer.kt`](file:///d:/nam5/semester_1/advance_android/01_trolyAI/troLyAo_ani/android/app/src/main/java/com/example/assistant/ui/character/CharacterAnimationPlayer.kt) | **Modified** | Added `restartKey: Any? = null` parameter, resetting frame index and elapsed time on key change. |
| [`ui/components/CharacterAvatar.kt`](file:///d:/nam5/semester_1/advance_android/01_trolyAI/troLyAo_ani/android/app/src/main/java/com/example/assistant/ui/components/CharacterAvatar.kt) | **Modified** | Read `LocalAnimationFpsSettings.current`, derived effective spec via `applyOverride`, forwarded `restartKey`. |
| [`MainActivity.kt`](file:///d:/nam5/semester_1/advance_android/01_trolyAI/troLyAo_ani/android/app/src/main/java/com/example/assistant/MainActivity.kt) | **Modified** | Collected DataStore FPS flow at root and provided via `CompositionLocalProvider`. |
| [`ui/settings/SettingsViewModel.kt`](file:///d:/nam5/semester_1/advance_android/01_trolyAI/troLyAo_ani/android/app/src/main/java/com/example/assistant/ui/settings/SettingsViewModel.kt) | **Modified** | Added FPS state, preview selection, `increaseFps`, `decreaseFps`, `replayPreview`, `restoreDefaultFps`. |
| [`ui/settings/SettingsScreen.kt`](file:///d:/nam5/semester_1/advance_android/01_trolyAI/troLyAo_ani/android/app/src/main/java/com/example/assistant/ui/settings/SettingsScreen.kt) | **Modified** | Made vertically scrollable with `LazyColumn`; preserved backend controls; added character preview and FPS controls. |
| [`domain/AnimationFpsSettingsTest.kt`](file:///d:/nam5/semester_1/advance_android/01_trolyAI/troLyAo_ani/android/app/src/test/java/com/example/assistant/domain/AnimationFpsSettingsTest.kt) | **Added** | 16 comprehensive unit tests verifying defaults, clamping, pure logic, isolation, and duration calculations. |

---

## 7. Verification Results

```powershell
$env:JAVA_HOME = "C:\Program Files\Android\Android Studio\jbr"
```

### 1. Unit Tests (`.\gradlew.bat testDebugUnitTest`):
```text
BUILD SUCCESSFUL in 35s
25 actionable tasks: 6 executed, 19 up-to-date

Results:
- AnimationFpsSettingsTest:     16 passed, 0 failed
- CharacterAnimationPlayerTest: 10 passed, 0 failed
- CharacterFrameResourcesTest:   6 passed, 0 failed
- ChatAnimationIntegrationTest:  9 passed, 0 failed
- UnitTest:                      7 passed, 0 failed

Total: 48 / 48 passed (100% passing, 0 failures, 0 errors, 0 skipped).
```

### 2. Debug Build (`.\gradlew.bat assembleDebug`):
```text
BUILD SUCCESSFUL in 26s
37 actionable tasks: 5 executed, 32 up-to-date

Artifact: app/build/outputs/apk/debug/app-debug.apk
Size: 17,044,962 bytes (~16.25 MB)
```

### 3. Android Lint (`.\gradlew.bat lintDebug`):
```text
BUILD SUCCESSFUL in 53s
28 actionable tasks: 7 executed, 21 up-to-date

Errors: 0 errors
New warnings: 0 new warnings
```

### 4. Git Diff Check (`git diff --check`):
```text
Clean, exit code 0.
```

---

## 8. Confirmations

1. **No Image Assets Changed:**
   `res/drawable` WebP frame assets and catalog indices remain completely unchanged.
2. **No Backend or API Files Changed:**
   Retrofit endpoints, DTOs, ApiClient, Room database, and repositories remain untouched.
3. **Stage 4 Layered Chat Layout Unchanged:**
   The layered Box design, soft frosted anime gradient panel, IME detection, 53% / 66.25% panel heights, and message bubbles are 100% preserved.

---

## 9. Physical-Phone Manual Checklist

- [ ] **Open Settings & Scroll:** Open Settings screen and scroll smoothly through the full screen using `LazyColumn`.
- [ ] **Backend Controls:** Verify backend URL input, "Kiểm tra kết nối" button, and "Lưu" button function as expected.
- [ ] **Six Action Rows:** Confirm all six actions are displayed with Vietnamese labels:
  - Chờ (Idle)
  - Suy nghĩ (Thinking)
  - Nói (Talk)
  - Vui (Happy)
  - Buồn (Sad)
  - Ngạc nhiên (Surprised)
- [ ] **Minus Lower Bound:** Tap `[−]` until reaching 4 FPS; verify the button disables and does not go below 4.
- [ ] **Plus Upper Bound:** Tap `[+]` until reaching 20 FPS; verify the button disables and does not go above 20.
- [ ] **Preview Selection:** Tap "Xem" on different actions (e.g. Vui, Buồn, Ngạc nhiên); verify preview updates immediately from frame 0.
- [ ] **LOOP Animations in Preview:** Verify Chờ, Suy nghĩ, Nói loop continuously.
- [ ] **ONE_SHOT Animations in Preview:** Verify Vui, Buồn, Ngạc nhiên play once and stay on the final frame.
- [ ] **Replay Button:** Tap "Phát lại"; verify the currently selected animation restarts from frame 0.
- [ ] **Dynamic Speed Update:** Adjust FPS of the selected animation; verify playback speed changes immediately.
- [ ] **Restore Defaults:** Tap "Khôi phục mặc định"; verify all six values reset to `5, 8, 10, 10, 8, 10 FPS`.
- [ ] **Persistence Across App Restarts:** Change several FPS values, close the app completely from recent apps, reopen, and confirm the changed values persist.
- [ ] **Home Screen Animation:** Return to Home; verify idle animation runs at the saved idle FPS.
- [ ] **Chat Screen Animation:** Open Chat; verify thinking and talk animations run at their saved FPS.
- [ ] **Chat One-Shot Completion:** Verify emotional responses in Chat complete properly and transition back to idle based on their effective duration.
- [ ] **Rapid Tapping Stability:** Tap plus/minus rapidly; confirm no crash, freeze, or corrupted preference values.

---

## 10. Remaining Limitations & Notes

- DataStore updates are asynchronous; while `collectAsStateWithLifecycle` immediately pushes updates through `LocalAnimationFpsSettings`, UI buttons also immediately disable at boundaries based on the current state.
- Physical device screen heights may vary; `LazyColumn` guarantees full reachability on small screens (e.g. compact phones in landscape orientation).

---

## 11. Final Verdict

**STAGE 5 COMPLETE — PERSISTENT PER-ANIMATION FPS CONTROLS & PREVIEW SUCCESSFULLY DELIVERED**
