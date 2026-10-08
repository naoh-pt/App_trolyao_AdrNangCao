# Stage 6B Implementation Report: Persistent Speech Rate and Pitch Controls

**Project:** `VirtualAssistant` (Android)  
**Package:** `com.example.assistant`  
**Date:** 2026-10-08  
**Status:** Complete  

---

## 1. Pre-Flight Git State

- **Branch:** `feature/android-integration`
- **Baseline Commit:** `698f323376ac18e21abd929a100d02512d5dcfbf` (`feat(android): implement Stage 6A Vietnamese TTS for assistant replies`)
- **Initial Working Tree:** Clean source working directory (`698f323` cleanly committed; local untracked archive/review files preserved).

---

## 2. Files Inspected

Before editing, the existing Stage 6A architecture was inspected:
- [`app/src/main/java/com/example/assistant/speech/VietnameseTtsHelper.kt`](file:///d:/nam5/semester_1/advance_android/01_trolyAI/troLyAo_ani/android/app/src/main/java/com/example/assistant/speech/VietnameseTtsHelper.kt): Context safety, queue flushing, state machine, pending queue.
- [`app/src/main/java/com/example/assistant/data/local/SettingsStore.kt`](file:///d:/nam5/semester_1/advance_android/01_trolyAI/troLyAo_ani/android/app/src/main/java/com/example/assistant/data/local/SettingsStore.kt): Existing preferences store (`tts_enabled`, `base_url`, `fps_*`).
- [`app/src/main/java/com/example/assistant/MainActivity.kt`](file:///d:/nam5/semester_1/advance_android/01_trolyAI/troLyAo_ani/android/app/src/main/java/com/example/assistant/MainActivity.kt): Root `CompositionLocalProvider` hierarchy.
- [`app/src/main/java/com/example/assistant/ui/settings/SettingsViewModel.kt`](file:///d:/nam5/semester_1/advance_android/01_trolyAI/troLyAo_ani/android/app/src/main/java/com/example/assistant/ui/settings/SettingsViewModel.kt): `SettingsUiState` and user actions.
- [`app/src/main/java/com/example/assistant/ui/settings/SettingsScreen.kt`](file:///d:/nam5/semester_1/advance_android/01_trolyAI/troLyAo_ani/android/app/src/main/java/com/example/assistant/ui/settings/SettingsScreen.kt): Existing "Giọng nói" section.
- [`app/src/main/java/com/example/assistant/ui/chat/ChatScreen.kt`](file:///d:/nam5/semester_1/advance_android/01_trolyAI/troLyAo_ani/android/app/src/main/java/com/example/assistant/ui/chat/ChatScreen.kt): Assistant response speech event observer and layout.
- [`app/src/test/java/com/example/assistant/speech/SpeechSettingsAndEventTest.kt`](file:///d:/nam5/semester_1/advance_android/01_trolyAI/troLyAo_ani/android/app/src/test/java/com/example/assistant/speech/SpeechSettingsAndEventTest.kt): Existing Stage 6A unit tests.
- [`app/src/main/java/com/example/assistant/domain/AnimationFpsSettings.kt`](file:///d:/nam5/semester_1/advance_android/01_trolyAI/troLyAo_ani/android/app/src/main/java/com/example/assistant/domain/AnimationFpsSettings.kt): Reference domain pattern for bounds, stepping, and composition locals.

---

## 3. Files Changed and Reasons

| File | Type | Reason |
|---|---|---|
| [`domain/SpeechSettings.kt`](file:///d:/nam5/semester_1/advance_android/01_trolyAI/troLyAo_ani/android/app/src/main/java/com/example/assistant/domain/SpeechSettings.kt) | **Added** | Pure, immutable domain model containing `enabled`, `speechRate`, `pitch`, bounds `[0.5f..2.0f]`, step `0.1f`, decimal normalization, formatting, and `LocalSpeechSettings` composition local. |
| [`data/local/SettingsStore.kt`](file:///d:/nam5/semester_1/advance_android/01_trolyAI/troLyAo_ani/android/app/src/main/java/com/example/assistant/data/local/SettingsStore.kt) | Modified | Added `speech_rate` and `speech_pitch` float preference keys. Exposes unified `speechSettings: Flow<SpeechSettings>`, `setSpeechRate`, `setPitch`, `adjustSpeechRate`, `adjustPitch`, and `resetSpeechVoiceDefaults()`. |
| [`speech/VietnameseTtsHelper.kt`](file:///d:/nam5/semester_1/advance_android/01_trolyAI/troLyAo_ani/android/app/src/main/java/com/example/assistant/speech/VietnameseTtsHelper.kt) | Modified | Added rate/pitch configuration via `setSpeechRate` and `setPitch` before every `speak()`. Stored pending requests with `(text, rate, pitch)` during initialization. Preserved existing lifecycle and error handling. |
| [`MainActivity.kt`](file:///d:/nam5/semester_1/advance_android/01_trolyAI/troLyAo_ani/android/app/src/main/java/com/example/assistant/MainActivity.kt) | Modified | Replaced single `ttsEnabled` subscription with `speechSettings` flow collection, providing `LocalSpeechSettings` and backward-compatible `LocalTtsEnabled`. |
| [`ui/settings/SettingsViewModel.kt`](file:///d:/nam5/semester_1/advance_android/01_trolyAI/troLyAo_ani/android/app/src/main/java/com/example/assistant/ui/settings/SettingsViewModel.kt) | Modified | Integrated `speechSettings` into `SettingsUiState`. Added `decreaseSpeechRate`, `increaseSpeechRate`, `decreasePitch`, `increasePitch`, and `restoreVoiceDefaults()`. Maintained backward-compatible constructor and `ttsEnabled` getter. |
| [`ui/settings/SettingsScreen.kt`](file:///d:/nam5/semester_1/advance_android/01_trolyAI/troLyAo_ani/android/app/src/main/java/com/example/assistant/ui/settings/SettingsScreen.kt) | Modified | Added 2 control rows ("Tốc độ đọc", "Cao độ giọng") with minus/value/plus buttons, Vietnamese accessibility descriptions, "Khôi phục giọng mặc định" button, preview stop on parameter change, and parameterized "Nghe thử". |
| [`ui/chat/ChatScreen.kt`](file:///d:/nam5/semester_1/advance_android/01_trolyAI/troLyAo_ani/android/app/src/main/java/com/example/assistant/ui/chat/ChatScreen.kt) | Modified | Consumes `LocalSpeechSettings.current`, speaks incoming assistant replies with configured `speechRate` and `pitch`, stops on exit or speech disable, and provides backward-compatible overload. |
| [`speech/SpeechSettingsAndEventTest.kt`](file:///d:/nam5/semester_1/advance_android/01_trolyAI/troLyAo_ani/android/app/src/test/java/com/example/assistant/speech/SpeechSettingsAndEventTest.kt) | Modified | Added 11 new unit tests (17 tests total) covering defaults, upper/lower clamping, 0.1 stepping, boundary conditions, float drift normalization, reset isolation, multiplier formatting, and step check helpers. |

---

## 4. Speech Settings Data Model

The domain model [`SpeechSettings`](file:///d:/nam5/semester_1/advance_android/01_trolyAI/troLyAo_ani/android/app/src/main/java/com/example/assistant/domain/SpeechSettings.kt) is an immutable data class:

```kotlin
data class SpeechSettings(
    val enabled: Boolean = DEFAULT_ENABLED,
    val speechRate: Float = DEFAULT_RATE,
    val pitch: Float = DEFAULT_PITCH,
)
```

### Invariants:
- **Rate bounds:** `0.5f` to `2.0f`, step `0.1f`, default `1.0f`.
- **Pitch bounds:** `0.5f` to `2.0f`, step `0.1f`, default `1.0f`.
- **Enabled default:** `true`.
- **Purity:** Pure Kotlin; independent of Android `Context`, Compose runtime, and `TextToSpeech` engine.
- **Provider:** `LocalSpeechSettings = compositionLocalOf { SpeechSettings.DEFAULT }`.

---

## 5. DataStore Keys and Defaults

Stored in the existing `settings` preferences DataStore:

| Key Name | Preference Type | Default Value | Notes |
|---|---|---|---|
| `tts_enabled` | `Boolean` | `true` | Preserved from Stage 6A. |
| `speech_rate` | `Float` | `1.0f` | Added in Stage 6B. |
| `speech_pitch` | `Float` | `1.0f` | Added in Stage 6B. |

### Migration & Compatibility:
- When upgrading from Stage 6A where `speech_rate` or `speech_pitch` do not exist in DataStore, preferences default to `1.0f`.
- Reading invalid values outside `[0.5f..2.0f]` safely clamps to limits.
- Calling `resetSpeechVoiceDefaults()` resets `speech_rate` and `speech_pitch` to `1.0f` while leaving `tts_enabled`, `base_url`, `client_id`, and `fps_*` completely untouched.

---

## 6. Clamping and Decimal Normalization Rules

To avoid IEEE 754 floating-point drift (e.g. `0.7f + 0.1f` yielding `0.79999995f` or `1.1000001f`):

```kotlin
fun normalize(value: Float, min: Float = MIN_RATE, max: Float = MAX_RATE): Float {
    val clamped = value.coerceIn(min, max)
    return Math.round(clamped * 10f) / 10f
}
```

- Every mutation (`withSpeechRate`, `withPitch`, `withStepRate`, `withStepPitch`, `setSpeechRate`, `setPitch`, `adjustSpeechRate`, `adjustPitch`) strictly runs through `normalize`.
- Formatted values use `String.format(Locale.US, "%.1fx", normalize(value))` ensuring predictable labels (`0.5x`, `1.0x`, `2.0x`).

---

## 7. TTS Helper Changes

In [`VietnameseTtsHelper.kt`](file:///d:/nam5/semester_1/advance_android/01_trolyAI/troLyAo_ani/android/app/src/main/java/com/example/assistant/speech/VietnameseTtsHelper.kt):
1. **Application of rate & pitch:**
   Before each utterance:
   ```kotlin
   engine.setSpeechRate(rate)
   engine.setPitch(pitch)
   engine.speak(text, TextToSpeech.QUEUE_FLUSH, null, utteranceId)
   ```
2. **Pending request queue with parameters:**
   If speech is triggered during `TtsState.INITIALIZING`, the request is retained as:
   ```kotlin
   private data class PendingSpeech(val text: String, val rate: Float, val pitch: Float)
   ```
   Upon `onTtsInitialized()`, the queued text is synthesized with its original `rate` and `pitch`.
3. **Safety & Disposal:**
   - Error return codes from `setSpeechRate`, `setPitch`, or `speak` are logged and mapped to concise Vietnamese errors (`Lỗi khi phát âm thanh.`, `Lỗi khi phát giọng nói: ...`).
   - `stop()` clears `pendingSpeech` and halts ongoing audio.
   - `shutdown()` cleans up native resources on Composable disposal.

---

## 8. Settings UI Behavior

The `Giọng nói` card in [`SettingsScreen.kt`](file:///d:/nam5/semester_1/advance_android/01_trolyAI/troLyAo_ani/android/app/src/main/java/com/example/assistant/ui/settings/SettingsScreen.kt) features:
1. **Đọc câu trả lời switch:** Toggles speech enabled/disabled. Disabling immediately calls `ttsHelper.stop()`.
2. **Tốc độ đọc row:**
   - "−" button: decreases rate by `0.1x`, disabled at `0.5x`.
   - Value display: e.g. `1.0x`.
   - "+" button: increases rate by `0.1x`, disabled at `2.0x`.
   - Content descriptions: `Giảm tốc độ đọc`, `Tăng tốc độ đọc`.
3. **Cao độ giọng row:**
   - "−" button: decreases pitch by `0.1x`, disabled at `0.5x`.
   - Value display: e.g. `1.0x`.
   - "+" button: increases pitch by `0.1x`, disabled at `2.0x`.
   - Content descriptions: `Giảm cao độ giọng`, `Tăng cao độ giọng`.
4. **Action buttons:**
   - **Nghe thử:** Speaks `"Xin chào, mình là trợ lý ảo của bạn."` using currently displayed rate and pitch. Enabled only when `speech.enabled && ttsHelper.isReady`.
   - **Khôi phục giọng mặc định:** Resets rate and pitch to `1.0x` without touching the enabled switch.
5. **Preview isolation:**
   - Tapping "−", "+", or "Khôi phục giọng mặc định" automatically calls `ttsHelper.stop()` so conflicting previews are stopped.
   - No auto-speak on adjustments; user triggers "Nghe thử" intentionally.

---

## 9. Chat Integration Behavior

In [`ChatScreen.kt`](file:///d:/nam5/semester_1/advance_android/01_trolyAI/troLyAo_ani/android/app/src/main/java/com/example/assistant/ui/chat/ChatScreen.kt):
- `speechSettings` is collected from `LocalSpeechSettings.current`.
- When a new assistant reply arrives via `vm.speechEvents`:
  - If `speechSettings.enabled == true`, speaks using `ttsHelper.speak(text, speechSettings.speechRate, speechSettings.pitch)`.
  - If `speechSettings.enabled == false`, remains silent.
- Invariants maintained:
  - Historical messages are never spoken.
  - User messages, pending drafts, and errors are never spoken.
  - Recompositions and IME keyboard changes do not trigger replay.
  - Exiting the screen disposes `rememberVietnameseTts()`, releasing audio resources.

---

## 10. Automated Command Results

All four required verification commands were executed directly:

### 1. `testDebugUnitTest`
```powershell
.\gradlew testDebugUnitTest
```
**Result:** `BUILD SUCCESSFUL in 18s`  
**Test Suites:**
- `SpeechSettingsAndEventTest`: 17 passed, 0 failed
- `AnimationFpsSettingsTest`: 16 passed, 0 failed
- `CharacterAnimationPlayerTest`: 10 passed, 0 failed
- `ChatAnimationIntegrationTest`: 9 passed, 0 failed
- `UnitTest`: 7 passed, 0 failed
- `CharacterFrameResourcesTest`: 6 passed, 0 failed  
**Total:** **65 passed, 0 failed, 0 errors, 0 skipped**.

### 2. `assembleDebug`
```powershell
.\gradlew assembleDebug
```
**Result:** `BUILD SUCCESSFUL in 10s` (37 actionable tasks: 5 executed, 32 up-to-date).

### 3. `lintDebug`
```powershell
.\gradlew lintDebug
```
**Result:** `BUILD SUCCESSFUL in 1m 13s` (28 actionable tasks: 7 executed, 21 up-to-date, 0 errors).

### 4. `git diff --check`
```powershell
git diff --check
```
**Result:** Clean (exit code 0; zero whitespace or conflict errors).

---

## 11. Manual Phone Checklist

| # | Check Item | Expected Verification Step |
|---|---|---|
| 1 | Upgrade persistence | Existing `Đọc câu trả lời` toggle state remains intact after installing Stage 6B build. |
| 2 | Initial defaults | "Tốc độ đọc" and "Cao độ giọng" display `1.0x` by default. |
| 3 | Rate limits | Minus button disables at `0.5x`; plus button disables at `2.0x`. |
| 4 | Pitch limits | Minus button disables at `0.5x`; plus button disables at `2.0x`. |
| 5 | Rate preview | Pressing "Nghe thử" at `0.5x` is noticeably slower than at `2.0x`. |
| 6 | Pitch preview | Pressing "Nghe thử" at `0.5x` is noticeably deeper than at `2.0x`. |
| 7 | Process restart | Modifying rate/pitch, force-closing the app, and reopening Settings preserves both values. |
| 8 | Chat playback | In Chat, new assistant replies speak at the customized speed and pitch. |
| 9 | History silence | Opening past conversations or returning from Settings remains completely silent. |
| 10 | Reset voice button | Pressing "Khôi phục giọng mặc định" sets rate and pitch back to `1.0x`. |
| 11 | Reset isolation | "Khôi phục giọng mặc định" does not alter the "Đọc câu trả lời" switch. |
| 12 | Non-regression | Backend configuration, character animation FPS settings, keyboard-open chat panel, and one-shot animations function normally. |

---

## 12. Known Limitations & Scope Boundaries

- **TALKING Animation Synchronization:** The character TALKING animation continues to run for a fixed duration (2000ms for neutral responses, or the one-shot frame duration for emotions). Full synchronization between Text-to-Speech duration (via `UtteranceProgressListener`) and character lip sync/animation is intentionally left for a subsequent stage.
- **Audio Scopes:** No microphone input, STT, backend audio streaming, voice downloading, or voice gender selection was added in this stage.

---

## 13. Git Status and Diff Stat

### `git diff --stat`
```text
 .../java/com/example/assistant/MainActivity.kt     |   9 +-
 .../example/assistant/data/local/SettingsStore.kt  |  45 +++++-
 .../assistant/speech/VietnameseTtsHelper.kt        |  74 ++++++---
 .../com/example/assistant/ui/chat/ChatScreen.kt    |  27 +++-
 .../assistant/ui/settings/SettingsScreen.kt        | 157 +++++++++++++++++--
 .../assistant/ui/settings/SettingsViewModel.kt     |  66 +++++++-
 .../assistant/speech/SpeechSettingsAndEventTest.kt | 172 ++++++++++++++++++++-
 7 files changed, 498 insertions(+), 52 deletions(-)
```

### Final `git status --short`
```text
 M android/app/src/main/java/com/example/assistant/MainActivity.kt
 M android/app/src/main/java/com/example/assistant/data/local/SettingsStore.kt
 M android/app/src/main/java/com/example/assistant/speech/VietnameseTtsHelper.kt
 M android/app/src/main/java/com/example/assistant/ui/chat/ChatScreen.kt
 M android/app/src/main/java/com/example/assistant/ui/settings/SettingsScreen.kt
 M android/app/src/main/java/com/example/assistant/ui/settings/SettingsViewModel.kt
 M android/app/src/test/java/com/example/assistant/speech/SpeechSettingsAndEventTest.kt
?? android/android_stage6a_sources.zip
?? android/app/src/main/java/com/example/assistant/domain/SpeechSettings.kt
?? android/review/character_animation_stage4a_layered_chat_layout.md
?? android/review/character_animation_stage4b_ime_transparent_panel.md
?? android/review/character_speech_stage6b_voice_controls.md
?? android_stage6a_sources_complete.zip
```

---

## 14. Summary

1. **What was implemented:**
   - Pure domain model `SpeechSettings` with clamping, 0.1 stepping, and decimal normalization.
   - Persistent `speech_rate` and `speech_pitch` float preference keys in `SettingsStore`.
   - App-wide `LocalSpeechSettings` propagation from `MainActivity`.
   - Parameterized `setSpeechRate` and `setPitch` in `VietnameseTtsHelper`, including pending initialization queue preservation.
   - Settings UI controls with minus/value/plus buttons for "Tốc độ đọc" and "Cao độ giọng", "Khôi phục giọng mặc định" reset, and isolated preview stop.
   - Chat screen integration using customized rate and pitch for new assistant replies.
2. **Exact files changed / added:**
   - Added: `domain/SpeechSettings.kt`
   - Added: `review/character_speech_stage6b_voice_controls.md`
   - Modified: `data/local/SettingsStore.kt`
   - Modified: `speech/VietnameseTtsHelper.kt`
   - Modified: `MainActivity.kt`
   - Modified: `ui/settings/SettingsViewModel.kt`
   - Modified: `ui/settings/SettingsScreen.kt`
   - Modified: `ui/chat/ChatScreen.kt`
   - Modified: `speech/SpeechSettingsAndEventTest.kt`
3. **Test / build / lint results:**
   - Unit tests: 65/65 passed.
   - `assembleDebug`: SUCCESSFUL.
   - `lintDebug`: SUCCESSFUL (0 errors).
   - `git diff --check`: Clean (0 errors).
4. **Anything not tested:** Physical audio output requires a device with a Vietnamese TTS engine installed (e.g. Google Speech Services).
5. **Readiness:** Fully ready for physical-phone verification.
