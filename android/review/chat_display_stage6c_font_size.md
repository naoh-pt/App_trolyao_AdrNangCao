# Stage 6C Implementation Report: Persistent Chat Message Font Size

**Project:** `VirtualAssistant` (Android)  
**Package:** `com.example.assistant`  
**Date:** 2026-10-08  
**Status:** Complete  

---

## 1. Files Inspected

Before implementing Stage 6C, the following existing Stage 6B sources were inspected:
- [`data/local/SettingsStore.kt`](file:///d:/nam5/semester_1/advance_android/01_trolyAI/troLyAo_ani/android/app/src/main/java/com/example/assistant/data/local/SettingsStore.kt): Existing preferences store containing `base_url`, `client_id`, `fps_*`, and Stage 6B speech preferences (`tts_enabled`, `speech_rate`, `speech_pitch`).
- [`domain/SpeechSettings.kt`](file:///d:/nam5/semester_1/advance_android/01_trolyAI/troLyAo_ani/android/app/src/main/java/com/example/assistant/domain/SpeechSettings.kt): Stage 6B domain model used as reference pattern for immutable settings and `CompositionLocal`.
- [`MainActivity.kt`](file:///d:/nam5/semester_1/advance_android/01_trolyAI/troLyAo_ani/android/app/src/main/java/com/example/assistant/MainActivity.kt): Root `CompositionLocalProvider` hierarchy.
- [`ui/settings/SettingsViewModel.kt`](file:///d:/nam5/semester_1/advance_android/01_trolyAI/troLyAo_ani/android/app/src/main/java/com/example/assistant/ui/settings/SettingsViewModel.kt): `SettingsUiState` and user actions.
- [`ui/settings/SettingsScreen.kt`](file:///d:/nam5/semester_1/advance_android/01_trolyAI/troLyAo_ani/android/app/src/main/java/com/example/assistant/ui/settings/SettingsScreen.kt): Settings sections layout and cards.
- [`ui/chat/ChatScreen.kt`](file:///d:/nam5/semester_1/advance_android/01_trolyAI/troLyAo_ani/android/app/src/main/java/com/example/assistant/ui/chat/ChatScreen.kt): Chat panel layout, message bubbles, and text styling.
- [`domain/AnimationFpsSettingsTest.kt`](file:///d:/nam5/semester_1/advance_android/01_trolyAI/troLyAo_ani/android/app/src/test/java/com/example/assistant/domain/AnimationFpsSettingsTest.kt) & [`speech/SpeechSettingsAndEventTest.kt`](file:///d:/nam5/semester_1/advance_android/01_trolyAI/troLyAo_ani/android/app/src/test/java/com/example/assistant/speech/SpeechSettingsAndEventTest.kt): Existing test suites.

---

## 2. Files Changed and Added for Stage 6C

| File | Type | Reason |
|---|---|---|
| [`domain/ChatDisplaySettings.kt`](file:///d:/nam5/semester_1/advance_android/01_trolyAI/troLyAo_ani/android/app/src/main/java/com/example/assistant/domain/ChatDisplaySettings.kt) | **Added** | Pure immutable domain model for message font size (`12sp..20sp`, step `1sp`, default `14sp`), line height calculation (`fontSizeSp + 4`), and `LocalChatDisplaySettings` composition local. |
| [`data/local/SettingsStore.kt`](file:///d:/nam5/semester_1/advance_android/01_trolyAI/troLyAo_ani/android/app/src/main/java/com/example/assistant/data/local/SettingsStore.kt) | Modified | Added `message_font_size_sp` integer preference key (`DEFAULT_FONT_SIZE_SP = 14`). Exposes `chatDisplaySettings: Flow<ChatDisplaySettings>`, `setMessageFontSize()`, `adjustMessageFontSize()`, and `resetMessageFontSize()`. |
| [`MainActivity.kt`](file:///d:/nam5/semester_1/advance_android/01_trolyAI/troLyAo_ani/android/app/src/main/java/com/example/assistant/MainActivity.kt) | Modified | Collects `chatDisplaySettings` from `SettingsStore` and provides `LocalChatDisplaySettings` across the Compose hierarchy. |
| [`ui/settings/SettingsViewModel.kt`](file:///d:/nam5/semester_1/advance_android/01_trolyAI/troLyAo_ani/android/app/src/main/java/com/example/assistant/ui/settings/SettingsViewModel.kt) | Modified | Added `chatDisplaySettings` to `SettingsUiState`, collected flow in `init`, and added `decreaseMessageFontSize()`, `increaseMessageFontSize()`, and `restoreMessageFontSize()`. |
| [`ui/settings/SettingsScreen.kt`](file:///d:/nam5/semester_1/advance_android/01_trolyAI/troLyAo_ani/android/app/src/main/java/com/example/assistant/ui/settings/SettingsScreen.kt) | Modified | Added "Hiển thị trò chuyện" card containing the "Cỡ chữ tin nhắn" minus/value/plus row, "Khôi phục cỡ chữ" button, and lightweight live message preview. |
| [`ui/chat/ChatScreen.kt`](file:///d:/nam5/semester_1/advance_android/01_trolyAI/troLyAo_ani/android/app/src/main/java/com/example/assistant/ui/chat/ChatScreen.kt) | Modified | Injected `displaySettings: ChatDisplaySettings = LocalChatDisplaySettings.current` and passed dynamic `fontSizeSp` and `lineHeightSp` to `MessageBubble` instances. |
| [`domain/ChatDisplaySettingsTest.kt`](file:///d:/nam5/semester_1/advance_android/01_trolyAI/troLyAo_ani/android/app/src/test/java/com/example/assistant/domain/ChatDisplaySettingsTest.kt) | **Added** | 5 unit tests validating default value `14`, lower bound clamping `12`, upper bound clamping `20`, step `1`, reset, line height calculation, and isolation from speech settings. |

---

## 3. DataStore Key, Range, Step, and Default

- **Preference Key:** `intPreferencesKey("message_font_size_sp")`
- **Default:** `14sp`
- **Minimum:** `12sp`
- **Maximum:** `20sp`
- **Step:** `1sp`
- **Clamping:** Stored and written values are clamped via `ChatDisplaySettings.clampFontSize(size)` to `[12..20]`.
- **Isolation:** Modifying `message_font_size_sp` does NOT alter `tts_enabled`, `speech_rate`, `speech_pitch`, `fps_*`, `base_url`, or `client_id`. `resetMessageFontSize()` only resets font size back to `14sp`.

---

## 4. Where the Font Size Is Applied

The setting strictly affects message-bubble text content:
- **User messages** in `ChatScreen` (`MessageBubble`).
- **Assistant messages** in `ChatScreen` (`MessageBubble`).
- **Pending user message** bubble (`MessageBubble` with dimmed state).
- **Settings screen preview bubbles** in "Hiển thị trò chuyện" section.

### Paired Line Height Rule:
`lineHeightSp = fontSizeSp + 4`
- `12sp → 16sp`
- `14sp → 18sp` (default)
- `16sp → 20sp`
- `20sp → 24sp`

### Strictly Preserved Elements (Not Modified):
- App bar titles ("Trò chuyện 💬", "Cài đặt ⚙️").
- Buttons and action icons.
- Settings labels and section titles.
- Backend status / error text.
- Message input `OutlinedTextField` placeholder and typed text.
- "Đang suy nghĩ~" typing bubble label and pulsing dots.
- Offline banner warning.
- Chat panel frosted gradient, corner radius, borders, padding, and IME height fractions (`0.53f` / `0.6625f`).

---

## 5. Confirmation of Non-Regression

- **Stage 4 Layout:** Character display height `360.dp`, frosted gradient panel, dynamic IME closed/open fractions (`0.53f` / `0.6625f`), and zero character resizing/movement are preserved.
- **Stage 5 Animation FPS:** Persistent per-action FPS settings (`idle=5`, `thinking=8`, `talk=10`, `happy=10`, `sad=8`, `surprised=10`), live preview player, and DataStore keys are intact.
- **Stage 6A & 6B TTS:** Zero-replay speech events, `VietnameseTtsHelper` lifecycle safety, `tts_enabled` switch, `speech_rate` (`0.5x..2.0x`), `speech_pitch` (`0.5x..2.0x`), and voice reset remain intact.
- **Backend Settings:** URL normalization, health check, and persistent `client_id` header remain unaffected.

---

## 6. Automated Test, Build, and Lint Results

### 1. `testDebugUnitTest`
```powershell
.\gradlew testDebugUnitTest
```
**Result:** `BUILD SUCCESSFUL in 43s`  
- `ChatDisplaySettingsTest`: 5 passed
- `SpeechSettingsAndEventTest`: 17 passed
- `AnimationFpsSettingsTest`: 16 passed
- `CharacterAnimationPlayerTest`: 10 passed
- `ChatAnimationIntegrationTest`: 9 passed
- `UnitTest`: 7 passed
- `CharacterFrameResourcesTest`: 6 passed  
**Total:** **70 passed, 0 failed, 0 errors, 0 skipped**.

### 2. `assembleDebug`
```powershell
.\gradlew assembleDebug
```
**Result:** `BUILD SUCCESSFUL in 19s` (37 actionable tasks: 4 executed, 33 up-to-date).

### 3. `lintDebug`
```powershell
.\gradlew lintDebug
```
**Result:** `BUILD SUCCESSFUL in 53s` (28 actionable tasks: 7 executed, 21 up-to-date, 0 errors).

### 4. `git diff --check`
```powershell
git diff --check
```
**Result:** Clean (exit code 0; zero whitespace or conflict errors).

---

## 7. Manual Phone Checklist

| # | Check Item | Verification Procedure & Expected Behavior |
|---|---|---|
| 1 | Default Value | On fresh install or upgrade, "Cỡ chữ tin nhắn" displays `14sp`. |
| 2 | Minus Boundary | Tapping "−" decrements by 1sp; stops and disables at `12sp`. |
| 3 | Plus Boundary | Tapping "+" increments by 1sp; stops and disables at `20sp`. |
| 4 | Settings Preview | Sample bubbles ("Xin chào!", "Mình có thể giúp gì cho bạn?") in Settings immediately resize as font size changes. |
| 5 | Chat Screen Bubbles | Navigating to Chat, user and assistant messages render with the selected font size and proportional line height. |
| 6 | Persistence | Force-stopping and restarting the app preserves the selected font size. |
| 7 | Reset Button | Tapping "Khôi phục cỡ chữ" resets only font size to `14sp`. |
| 8 | Settings Isolation | Modifying or resetting font size does not change speech toggle, speech rate, pitch, animation FPS, or backend URL. |
| 9 | Layout Stability | Opening and closing the software keyboard in Chat works seamlessly; the frosted panel expands smoothly without distorting the character. |

---

## 8. Git Status and Diff Stat

### `git diff --stat`
```text
 .../java/com/example/assistant/MainActivity.kt     |  15 +-
 .../example/assistant/data/local/SettingsStore.kt  |  74 ++++-
 .../assistant/speech/VietnameseTtsHelper.kt        |  74 +++--
 .../com/example/assistant/ui/chat/ChatScreen.kt    |  60 +++-
 .../assistant/ui/settings/SettingsScreen.kt        | 317 ++++++++++++++++++++-
 .../assistant/ui/settings/SettingsViewModel.kt     |  95 +++++-
 .../assistant/speech/SpeechSettingsAndEventTest.kt | 172 ++++++++++-
 7 files changed, 752 insertions(+), 55 deletions(-)
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
?? android/app/src/main/java/com/example/assistant/domain/ChatDisplaySettings.kt
?? android/app/src/main/java/com/example/assistant/domain/SpeechSettings.kt
?? android/app/src/test/java/com/example/assistant/domain/ChatDisplaySettingsTest.kt
?? android/review/character_animation_stage4a_layered_chat_layout.md
?? android/review/character_animation_stage4b_ime_transparent_panel.md
?? android/review/character_speech_stage6b_voice_controls.md
?? android/review/chat_display_stage6c_font_size.md
?? android_stage6a_sources_complete.zip
```

---

## 9. Combined Summary: Stage 6B & Stage 6C

The working tree holds the uncommitted, verified implementations of both **Stage 6B** and **Stage 6C**:

### Stage 6B: Persistent Speech Rate & Pitch Controls
- **Domain Model:** [`domain/SpeechSettings.kt`](file:///d:/nam5/semester_1/advance_android/01_trolyAI/troLyAo_ani/android/app/src/main/java/com/example/assistant/domain/SpeechSettings.kt) with `[0.5x..2.0x]` range, `0.1x` step, default `1.0x`, decimal normalization, and `LocalSpeechSettings`.
- **DataStore:** `speech_rate` and `speech_pitch` float preference keys in `SettingsStore`.
- **TTS Engine:** `VietnameseTtsHelper` applies rate and pitch before speech; queues parameters if initializing.
- **Settings UI:** "Tốc độ đọc", "Cao độ giọng" rows with `−`/`+` buttons, "Khôi phục giọng mặc định" reset button, preview stop on adjustment, and sample speech button.
- **Chat Screen:** Assistant responses speak with custom rate and pitch; zero replay for historical messages.

### Stage 6C: Persistent Chat Message Font Size
- **Domain Model:** [`domain/ChatDisplaySettings.kt`](file:///d:/nam5/semester_1/advance_android/01_trolyAI/troLyAo_ani/android/app/src/main/java/com/example/assistant/domain/ChatDisplaySettings.kt) with `[12sp..20sp]` range, `1sp` step, default `14sp`, `lineHeightSp = fontSizeSp + 4`, and `LocalChatDisplaySettings`.
- **DataStore:** `message_font_size_sp` integer preference key in `SettingsStore`.
- **Settings UI:** "Hiển thị trò chuyện" card with "Cỡ chữ tin nhắn" `−`/`+` controls, "Khôi phục cỡ chữ" reset button, and live 2-bubble preview.
- **Chat Screen:** Injects `LocalChatDisplaySettings.current` and dynamically sizes user, assistant, and pending message bubbles while leaving all layout chrome and input controls intact.
