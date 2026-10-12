# Stage 6A Implementation Report: Vietnamese Text-to-Speech for New Assistant Replies

**Project:** `VirtualAssistant` (Android)  
**Package:** `com.example.assistant`  
**Date:** 2026-10-08  
**Status:** Complete  

---

## 1. Pre-Flight Git State

- **Branch:** `feature/android-integration`
- **Latest Commit:** `04a148a43ee30af31e0b257a7b6ea7e5cacf553b` (`feat(android): add persistent animation FPS settings`)
- **Initial Working Tree:** Clean source working directory (`04a148a` cleanly committed; `android_stage3_updated_sources.zip` staged for deletion).

---

## 2. Files Inspected

Before editing, the following existing implementations were analyzed:
- [`app/src/main/java/com/example/assistant/ui/chat/ChatViewModel.kt`](file:///d:/nam5/semester_1/advance_android/01_trolyAI/troLyAo_ani/android/app/src/main/java/com/example/assistant/ui/chat/ChatViewModel.kt): Identifies exact insertion point for new assistant replies (`repo.sendMessage(...).fold(onSuccess = { reply -> ... })`).
- [`app/src/main/java/com/example/assistant/ui/chat/ChatScreen.kt`](file:///d:/nam5/semester_1/advance_android/01_trolyAI/troLyAo_ani/android/app/src/main/java/com/example/assistant/ui/chat/ChatScreen.kt): Layered Compose layout with frosted anime panel, IME handling, and message list state.
- [`app/src/main/java/com/example/assistant/data/local/SettingsStore.kt`](file:///d:/nam5/semester_1/advance_android/01_trolyAI/troLyAo_ani/android/app/src/main/java/com/example/assistant/data/local/SettingsStore.kt): DataStore preferences store for base URL, client ID, and animation FPS keys.
- [`app/src/main/java/com/example/assistant/ui/settings/SettingsViewModel.kt`](file:///d:/nam5/semester_1/advance_android/01_trolyAI/troLyAo_ani/android/app/src/main/java/com/example/assistant/ui/settings/SettingsViewModel.kt): Settings UI state and operations.
- [`app/src/main/java/com/example/assistant/ui/settings/SettingsScreen.kt`](file:///d:/nam5/semester_1/advance_android/01_trolyAI/troLyAo_ani/android/app/src/main/java/com/example/assistant/ui/settings/SettingsScreen.kt): Vertically scrollable settings view with backend and animation preview controls.
- [`app/src/main/java/com/example/assistant/MainActivity.kt`](file:///d:/nam5/semester_1/advance_android/01_trolyAI/troLyAo_ani/android/app/src/main/java/com/example/assistant/MainActivity.kt): App root providing composition locals and navigation.
- [`app/src/main/AndroidManifest.xml`](file:///d:/nam5/semester_1/advance_android/01_trolyAI/troLyAo_ani/android/app/src/main/AndroidManifest.xml): App permissions and component declarations.
- Existing unit tests in `app/src/test/java/com/example/assistant/`.

---

## 3. Files Changed and Why

| File | Type | Reason |
|---|---|---|
| [`AndroidManifest.xml`](file:///d:/nam5/semester_1/advance_android/01_trolyAI/troLyAo_ani/android/app/src/main/AndroidManifest.xml) | Modified | Added `<queries>` intent filter for `android.intent.action.TTS_SERVICE` as required by Android 11+ package visibility. Zero recording permissions added. |
| [`data/local/SettingsStore.kt`](file:///d:/nam5/semester_1/advance_android/01_trolyAI/troLyAo_ani/android/app/src/main/java/com/example/assistant/data/local/SettingsStore.kt) | Modified | Added `tts_enabled` DataStore boolean key (`DEFAULT_TTS_ENABLED = true`), exposed `ttsEnabled: Flow<Boolean>`, and `setTtsEnabled(Boolean)`. |
| [`ui/settings/SettingsViewModel.kt`](file:///d:/nam5/semester_1/advance_android/01_trolyAI/troLyAo_ani/android/app/src/main/java/com/example/assistant/ui/settings/SettingsViewModel.kt) | Modified | Added `ttsEnabled` field to `SettingsUiState`, collected flow in `init`, and exposed `setTtsEnabled(Boolean)`. |
| [`speech/VietnameseTtsHelper.kt`](file:///d:/nam5/semester_1/advance_android/01_trolyAI/troLyAo_ani/android/app/src/main/java/com/example/assistant/speech/VietnameseTtsHelper.kt) | **Added** | Reusable lifecycle-aware TTS controller with `applicationContext`, safe Vietnamese locale checking (`vi-VN`), pending queue, `QUEUE_FLUSH`, `stop()`, `shutdown()`, and `rememberVietnameseTts()`. |
| [`MainActivity.kt`](file:///d:/nam5/semester_1/advance_android/01_trolyAI/troLyAo_ani/android/app/src/main/java/com/example/assistant/MainActivity.kt) | Modified | Collected DataStore `ttsEnabled` at root and provided through `LocalTtsEnabled` composition local. |
| [`ui/chat/ChatViewModel.kt`](file:///d:/nam5/semester_1/advance_android/01_trolyAI/troLyAo_ani/android/app/src/main/java/com/example/assistant/ui/chat/ChatViewModel.kt) | Modified | Added `speechEvents: SharedFlow<String>` with `replay = 0` emitted strictly on `onSuccess` of `sendMessage()`. |
| [`ui/chat/ChatScreen.kt`](file:///d:/nam5/semester_1/advance_android/01_trolyAI/troLyAo_ani/android/app/src/main/java/com/example/assistant/ui/chat/ChatScreen.kt) | Modified | Integrated `rememberVietnameseTts()`, collected `speechEvents` when `ttsEnabled == true`, and stopped speech when `ttsEnabled == false`. |
| [`ui/settings/SettingsScreen.kt`](file:///d:/nam5/semester_1/advance_android/01_trolyAI/troLyAo_ani/android/app/src/main/java/com/example/assistant/ui/settings/SettingsScreen.kt) | Modified | Added "Giọng nói" section with "Đọc câu trả lời" Material 3 Switch and "Nghe thử" button. |
| [`speech/SpeechSettingsAndEventTest.kt`](file:///d:/nam5/semester_1/advance_android/01_trolyAI/troLyAo_ani/android/app/src/test/java/com/example/assistant/speech/SpeechSettingsAndEventTest.kt) | **Added** | 6 unit tests verifying default value, state isolation, zero-replay flow behavior, and TtsState safety. |

---

## 4. Architecture of the Critical One-Time Speech Event

### Problem:
Observing the list of messages (`StateFlow<List<MessageEntity>>`) would cause historical messages to be spoken again upon screen rotation, navigation back from History/Settings, keyboard open/close recompositions, or room cache synchronization.

### Solution:
A decoupled, one-time event stream was implemented in `ChatViewModel`:
```kotlin
private val _speechEvents = MutableSharedFlow<String>(replay = 0, extraBufferCapacity = 1)
val speechEvents: SharedFlow<String> = _speechEvents.asSharedFlow()
```

### Invariants Guaranteed:
- **Strictly New Replies:** Only emitted in `repo.sendMessage(id, rid, text).fold(onSuccess = { reply -> _speechEvents.emit(reply.text) })`.
- **Zero Historical Replay:** `replay = 0` guarantees `replayCache.isEmpty()`. Resubscribing (e.g., returning to ChatScreen) never replays previously spoken replies.
- **Exclusion of Non-Speech Messages:** User messages, drafts/pending messages, network errors, and historical messages loaded via `loadMessages()` are never emitted to `speechEvents`.
- **Decoupled Architecture:** `ChatViewModel` retains zero references to `Context`, `TextToSpeech`, Android Activity, or Compose runtime.

---

## 5. TTS Initialization and Lifecycle Handling

The [`VietnameseTtsHelper`](file:///d:/nam5/semester_1/advance_android/01_trolyAI/troLyAo_ani/android/app/src/main/java/com/example/assistant/speech/VietnameseTtsHelper.kt) class encapsulates Android's native `android.speech.tts.TextToSpeech`:

1. **Context Safety:** Uses `context.applicationContext` directly. Does not retain an Activity or Composable reference.
2. **Safe Initialization:**
   - In `onInit(status)`: checks for `TextToSpeech.SUCCESS`.
   - Sets `Locale("vi", "VN")`.
   - Checks `langResult` against `LANG_MISSING_DATA` and `LANG_NOT_SUPPORTED`. If unsupported, updates state to `TtsState.UNAVAILABLE` with a localized message rather than crashing.
3. **Pending Text Support:**
   If a reply arrives before initialization completes, the text is queued in `pendingText` and immediately spoken once initialization succeeds.
4. **Queue Flush:**
   Uses `TextToSpeech.QUEUE_FLUSH` with a unique `UUID.randomUUID().toString()` utterance ID so that newer replies immediately supersede older ongoing speech.
5. **Screen Lifecycle Disposal:**
   `rememberVietnameseTts()` binds disposal to Compose's `DisposableEffect(helper) { onDispose { helper.shutdown() } }`. Navigating away from `ChatScreen` or `SettingsScreen` shuts down the engine and stops audio playback immediately.
6. **Immediate Disable Handling:**
   `LaunchedEffect(ttsEnabled)` in `ChatScreen` triggers `ttsHelper.stop()` the instant the user disables the setting.

---

## 6. DataStore Setting Details

- **Store:** Existing `settings` DataStore in `SettingsStore`.
- **Key:** `booleanPreferencesKey("tts_enabled")`
- **Default:** `DEFAULT_TTS_ENABLED = true`
- **Isolation:** Modifying `tts_enabled` does not alter `base_url`, `client_id`, or `fps_*` preferences.

---

## 7. Vietnamese Locale Availability Handling

When `Locale("vi", "VN")` is queried against the system TTS engine:
- If available: status is `TtsState.READY`, speech plays normally.
- If missing data (`LANG_MISSING_DATA`) or unsupported (`LANG_NOT_SUPPORTED`):
  - Sets `errorMessage = "Chưa hỗ trợ giọng nói tiếng Việt trên thiết bị này."`
  - Sets `state = TtsState.UNAVAILABLE`
  - "Nghe thử" button is disabled and displays the localized error message.
  - The app never crashes and does not force open external app store or settings intents.

---

## 8. Automated Verification Results

All automated commands were executed with JDK 17 (`C:\Program Files\Android\Android Studio\jbr`):

### 1. Unit Tests (`.\gradlew.bat testDebugUnitTest`):
```text
BUILD SUCCESSFUL in 23s
25 actionable tasks: 3 executed, 22 up-to-date

Results:
- SpeechSettingsAndEventTest:    6 passed, 0 failed
- AnimationFpsSettingsTest:     16 passed, 0 failed
- CharacterAnimationPlayerTest: 10 passed, 0 failed
- CharacterFrameResourcesTest:   6 passed, 0 failed
- ChatAnimationIntegrationTest:  9 passed, 0 failed
- UnitTest:                      7 passed, 0 failed

Total: 54 / 54 passed (100% passing, 0 failures, 0 errors, 0 skipped).
```

### 2. Debug Build (`.\gradlew.bat assembleDebug`):
```text
BUILD SUCCESSFUL in 34s
37 actionable tasks: 5 executed, 32 up-to-date

Artifact: app/build/outputs/apk/debug/app-debug.apk
Size: 17,047,402 bytes (~16.26 MB)
```

### 3. Android Lint (`.\gradlew.bat lintDebug`):
```text
BUILD SUCCESSFUL in 1m 56s
28 actionable tasks: 8 executed, 20 up-to-date

Errors: 0 errors
New warnings: 0 new warnings
```

### 4. Git Diff Check (`git diff --check`):
```text
Clean, exit code 0.
```

---

## 9. Scope Boundary Confirmations

- **Microphone / Recording:** NOT implemented. Zero recording permissions in manifest.
- **Voice Pitch / Speech Rate:** NOT implemented (reserved for Stage 6B).
- **Backend Audio / STT:** NOT implemented.
- **Stage 4 & Stage 5 Layouts:** Frosted gradient panel, keyboard expansion, character animations, and per-action FPS controls remain 100% preserved.

---

## 10. Physical Phone Manual Test Checklist

- [ ] **Settings - Default Switch State:** Open Settings; verify "Đọc câu trả lời" switch is ON by default.
- [ ] **Settings - Sample Audio:** Tap "Nghe thử"; hear the Vietnamese sentence: *"Xin chào, mình là trợ lý ảo của bạn."*
- [ ] **Settings - Disable Speech:** Toggle "Đọc câu trả lời" to OFF; verify "Nghe thử" button becomes disabled.
- [ ] **Settings - Persistence:** Kill the app from Recent Apps, reopen Settings, and verify switch remains OFF. Turn it back ON.
- [ ] **Chat - New Reply Speech:** Send a message; upon backend response arrival, verify the assistant reply is spoken in Vietnamese once.
- [ ] **Chat - Keyboard Recomposition Stability:** Open and close the keyboard while in chat; verify past messages are NOT spoken again.
- [ ] **Chat - Navigation Silence:** Navigate to History screen and return to Chat; verify historical messages remain silent.
- [ ] **Chat - Existing Conversation Silence:** Open an existing chat session from History; verify no speech plays on entry.
- [ ] **Chat - Speech Interruption by Newer Reply:** If another response arrives while previous speech is playing, verify the previous speech stops and the new response starts immediately (`QUEUE_FLUSH`).
- [ ] **Chat - Immediate Stop upon Disabling:** If speech is playing and user turns off switch in Settings, verify speech stops immediately.
- [ ] **Chat - Immediate Stop upon Leaving Screen:** If speech is playing and user taps Back to exit ChatScreen, verify speech stops immediately (`shutdown()`).
- [ ] **General Stability:** Verify character animations, FPS controls, and backend health tests function normally without regressions.

*(Note: Tests 5 and 9 require a live backend. If the backend is offline, tests 1–4, 10–12 can be verified directly via the "Nghe thử" button in Settings).*

---

## 11. Git Diff Stat & Status

### `git diff --stat`:
```text
 android/app/src/main/AndroidManifest.xml           |  6 ++
 .../java/com/example/assistant/MainActivity.kt     | 10 ++-
 .../example/assistant/data/local/SettingsStore.kt  | 12 ++++
 .../com/example/assistant/ui/chat/ChatScreen.kt    | 25 ++++++-
 .../com/example/assistant/ui/chat/ChatViewModel.kt | 10 +++
 .../assistant/ui/settings/SettingsScreen.kt        | 84 +++++++++++++++++++++-
 .../assistant/ui/settings/SettingsViewModel.kt     | 12 ++++
 7 files changed, 156 insertions(+), 3 deletions(-)
```

### `git status --short`:
```text
D  android_stage3_updated_sources.zip
 M app/src/main/AndroidManifest.xml
 M app/src/main/java/com/example/assistant/MainActivity.kt
 M app/src/main/java/com/example/assistant/data/local/SettingsStore.kt
 M app/src/main/java/com/example/assistant/ui/chat/ChatScreen.kt
 M app/src/main/java/com/example/assistant/ui/chat/ChatViewModel.kt
 M app/src/main/java/com/example/assistant/ui/settings/SettingsScreen.kt
 M app/src/main/java/com/example/assistant/ui/settings/SettingsViewModel.kt
?? app/src/main/java/com/example/assistant/speech/
?? app/src/test/java/com/example/assistant/speech/
?? review/character_animation_stage4a_layered_chat_layout.md
?? review/character_animation_stage4b_ime_transparent_panel.md
?? review/character_speech_stage6a_tts.md
```

---

## 12. Final Verdict

**STAGE 6A COMPLETE — VIETNAMESE TEXT-TO-SPEECH FOR NEW ASSISTANT REPLIES READY FOR RUNTIME VALIDATION**
