# Stage 11 — Assistant Actions & Full Emotion Sequence Integration

## 1. Final Verdict

**READY FOR DEVICE TEST**

The stable application was verified, committed, backed up to `backup/pre-assistant-actions`, and pushed to remote `origin`. All Stage 11 requirements have been implemented on `feature/assistant-actions-reminders`:
1. The response-emotion animation plays through its full frame sequence before returning to `idle`, with an FPS-aware recovery watchdog (300–500 ms margin) replacing the former fixed 1000 ms cutoff.
2. Safe, deterministic assistant actions (`set_timer`, `create_calendar_event`, `map_search`) were introduced with allowlisted Intent builders and explicit UI confirmation cards.
3. Zero automatic app launches occur upon receiving replies; external apps are opened exclusively via explicit user button taps.
4. All existing chat, RAG, provider fallback, TTS sync, voice input, and settings remain untouched and operational.
5. The complete backend suite (352 tests), all 109 Android unit tests, `compileall`, `assembleDebug`, and `git diff --check` passed cleanly during the final pre-commit verification.
6. Stage 11 implementation changes were reviewed on the feature branch before commit.

---

## 2. Original Branch and HEAD

- **Branch before checkpoint**: `feature/android-voice-input`
- **Initial HEAD commit**: `fd599d00a06dd0a126077e85ed48ef4834c08c54` (`merge: integrate Android TTS animation synchronization`)

---

## 3. Verified Stable Checkpoint Commit

- **Checkpoint commit SHA**: `67efc3d52623b32e650ea82b403487c8d9df7e14`
- **Commit message**: `chore: checkpoint stable app before assistant actions`
- **Committed files**:
  - `android/app/src/main/java/com/example/assistant/ui/chat/ChatScreen.kt`
  - `android/app/src/main/java/com/example/assistant/ui/chat/ChatViewModel.kt`
  - `android/app/src/main/res/drawable/ic_mic.xml`
  - `android/app/src/test/java/com/example/assistant/ui/chat/VoiceInputTest.kt`
  - `review/android-stage10-voice-input.md`

---

## 4. Backup Branch Name and Remote Push Confirmation

- **Backup branch**: `backup/pre-assistant-actions`
- **Remote destination**: `origin/backup/pre-assistant-actions`
- **Push status**: Successfully pushed to `https://github.com/naoh-pt/App_trolyao_AdrNangCao.git` at commit `67efc3d52623b32e650ea82b403487c8d9df7e14`.

---

## 5. Stage 11 Feature Branch and Current HEAD

- **Feature branch**: `feature/assistant-actions-reminders`
- **Branch HEAD before the Stage 11 commit**: `67efc3d52623b32e650ea82b403487c8d9df7e14`

---

## 6. Complete Changed-File List with Reasons

| File | Change type | Rationale |
|---|---|---|
| `android/app/build.gradle.kts` | Modified | Enabled default return values for Android unit tests that exercise framework classes. |
| `android/app/src/main/AndroidManifest.xml` | Modified | Added `<uses-permission android:name="com.android.alarm.permission.SET_ALARM" />` required for `AlarmClock.ACTION_SET_TIMER`. |
| `android/app/src/main/java/com/example/assistant/data/remote/Dtos.kt` | Modified | Added `AssistantActionDto` and mapped optional `action` field on `SendMessageResponse` and `MessageDto`. |
| `android/app/src/main/java/com/example/assistant/data/repo/ChatRepository.kt` | Modified | Added `AssistantReply` wrapper to return both `MessageEntity` and `AssistantActionDto?` from `sendMessage`. |
| `android/app/src/main/java/com/example/assistant/ui/chat/AssistantActionDispatcher.kt` | Added | Pure allowlisted action dispatcher: defines `AssistantActionPayload`, pure `parseActionPayload`, `buildActionIntent`, label resolution, and safe activity launcher `launchActionSafely`. |
| `android/app/src/main/java/com/example/assistant/ui/chat/ChatViewModel.kt` | Modified | Implemented `calculateEmotionWatchdogDurationMs`, updated `SpeechAnimationCoordinator` for direct neutral-to-idle transition, replaced fixed timeout with dynamic watchdog, added `activeActions` state, and debounced action button taps. |
| `android/app/src/main/java/com/example/assistant/ui/chat/ChatScreen.kt` | Modified | Added `LocalAnimationFpsSettings` propagation to ViewModel, action card button rendering under assistant messages, and safe action launcher integration. |
| `android/app/src/test/java/com/example/assistant/ui/chat/SpeechAnimationSyncTest.kt` | Modified | Updated `testTtsDisabledNeutralReply` to verify direct `IDLE` transition for neutral replies when TTS is disabled. |
| `android/app/src/test/java/com/example/assistant/ui/chat/Stage11AssistantActionsAndEmotionTest.kt` | Added | 18 unit tests verifying full emotion sequence watchdog, neutral-to-idle transitions, FPS-aware duration scaling, stale callback protection, action payload parsing, and external app fallbacks. |
| `backend/app/schemas/conversation.py` | Modified | Added `AssistantActionResponse` schema, optional `action` fields to `MessageResponse` and `SendMessageResponse`, and `@model_serializer` to omit `action` when `None`. |
| `backend/app/services/assistant_action_service.py` | Added | Deterministic local recognition service for relative timer (`set_timer`), calendar event (`create_calendar_event`), and map search (`map_search`). |
| `backend/app/api/v1/conversations.py` | Modified | Routed `recognize_action` ahead of quick replies, returned proposed action, saved messages to SQLite, and restored actions upon idempotency replay. |
| `backend/tests/test_assistant_action_service.py` | Added | 24 tests covering timers, calendar events, map searches, ambiguity clarifications, URL rejection, normal queries bypass, and route persistence/idempotency. |
| `review/android-stage11-assistant-actions.md` | Added | This deliverable report. |

---

## 7. Before/After Emotion-Animation Lifecycle

### Before (Stage 8–10)
1. **User sends message**: Character transitions to `THINKING` (looping).
2. **Reply arrives with TTS**: Remains `THINKING` until speech starts.
3. **TTS starts (`onSpeechStarted`)**: Character transitions to `TALKING + NEUTRAL` (looping `talk` frames).
4. **TTS completes (`onSpeechCompleted`)**:
   - If response emotion was non-neutral (e.g. `happy`, `sad`, `surprised`), coordinator sets `TALKING + responseEmotion`.
   - `scheduleEmotionTimeoutIfNeeded()` scheduled a **fixed 1000 ms timer** (`delay(EMOTION_DISPLAY_DURATION_MS)`).
   - After 1000 ms, the coroutine forcibly reset the character to `IDLE + NEUTRAL`.
   - **Problem**: `happy` (1500 ms @ 10 FPS), `sad` (2625 ms @ 8 FPS), and `surprised` (2300 ms @ 10 FPS) were cut off mid-animation and never completed their full frame sequences.

### After (Stage 11)
1. **User sends message**: Character transitions to `THINKING` (looping).
2. **Reply arrives with TTS**: Remains `THINKING` until speech starts.
3. **TTS starts (`onSpeechStarted`)**: Character transitions to `TALKING + NEUTRAL` (looping `talk` frames).
4. **TTS completes (`onSpeechCompleted`)**:
   - If response emotion is `NEUTRAL`: transitions **immediately and directly** to `IDLE + NEUTRAL`.
   - If response emotion is non-neutral (`happy`, `sad`, `surprised`):
     - Transitions to `TALKING + responseEmotion`.
     - `CharacterAnimationPlayer` runs through every frame from 0 to `frames.size - 1` driven by the frame clock and configured FPS.
     - Upon reaching the final frame, `CharacterAnimationPlayer` invokes `onOneShotFinished()`.
     - `vm.onCharacterAnimationFinished()` cancels the watchdog coroutine and smoothly transitions character to `IDLE + NEUTRAL`.
5. **TTS disabled**:
   - Non-neutral emotion plays once from frame 0 through completion.
   - Neutral emotion returns directly to `IDLE`.
6. **Watchdog**: Acts strictly as failure recovery (see Section 8).

---

## 8. Exact Watchdog Calculation

The watchdog is implemented as a failure recovery fallback in `calculateEmotionWatchdogDurationMs`:

$$\text{frameDurationMs} = \lfloor \frac{1000}{\text{fps}} \rfloor$$
$$\text{totalDurationMs} = \text{frameCount} \times \text{frameDurationMs}$$
$$\text{watchdogMs} = \text{totalDurationMs} + \text{safetyMarginMs}$$

Where:
- $\text{safetyMarginMs} = 400\text{ ms}$ (within the required 300–500 ms window).
- For `Emotion.NEUTRAL`: $\text{watchdogMs} = 0\text{ ms}$ (no watchdog scheduled; immediate transition to `IDLE`).

### Concrete Watchdog Durations by Animation

| Emotion | Frames | Default FPS | Nominal Duration | Watchdog Timeout ($\text{margin} = 400\text{ ms}$) |
|---|---|---|---|---|
| `happy` | 15 | 10 | 1500 ms | **1900 ms** |
| `sad` | 21 | 8 | 2625 ms | **3025 ms** |
| `surprised` | 23 | 10 | 2300 ms | **2700 ms** |
| `happy` (slow 4 FPS) | 15 | 4 | 3750 ms | **4150 ms** |
| `sad` (slow 4 FPS) | 21 | 4 | 5250 ms | **5650 ms** |
| `neutral` | 0 | - | 0 ms | **0 ms** (direct to `IDLE`) |

Under normal operation, `onOneShotFinished()` fires at `totalDurationMs`, canceling the watchdog coroutine before it can ever trigger.

---

## 9. Supported Vietnamese Timer/Calendar/Map Patterns

### 1. Relative Timer (`set_timer`)
- `nhắc tôi học bài sau 5 phút`
- `nhắc mình uống nước sau 10 phút nữa`
- `hẹn giờ 30 phút để nghỉ`
- `nhắc tôi kiểm tra bài sau 2 giờ`
- `hẹn giờ 15 phút`

### 2. Calendar Event (`create_calendar_event`)
- `đặt lịch học Android lúc 20 giờ hôm nay`
- `đặt lịch nộp bài lúc 8 giờ tối mai`
- `nhắc tôi họp nhóm lúc 19:30 ngày mai`
- `đặt lịch thi lúc 9 giờ sáng mai`
- `đặt lịch họp phụ huynh lúc 14:00 hôm nay`

### 3. Map Search (`map_search`)
- `tìm Học viện Kỹ thuật Mật mã trên bản đồ`
- `mở bản đồ tìm Hồ Gươm`
- `chỉ đường đến Bảo tàng Hà Nội`
- `tìm đường đến Hồ Gươm`
- `chỉ đường tới Công viên Cầu Giấy`

---

## 10. False-Positive and Ambiguity Safeguards

1. **Duration boundaries (Timer)**:
   - Range strictly enforced: 1 minute (60s) to 24 hours (86,400s).
   - $\le 0$ minutes: Anna responds asking for a valid duration $> 0$, `action = None`.
   - $> 24$ hours: Anna responds stating the 24-hour limit, `action = None`.
   - Missing duration (e.g. `nhắc tôi học bài`): Anna asks for the specific duration, `action = None`.
2. **Date and Time Ambiguity (Calendar)**:
   - Missing day (neither `hôm nay` nor `mai`): Anna asks user to clarify the day, `action = None`.
   - Ambiguous 12-hour time without modifier (e.g. `lúc 8 giờ`): Anna asks whether morning or evening was intended, `action = None`.
   - Past time validation: If target timestamp $\le$ current time in `Asia/Ho_Chi_Minh` (UTC+7), Anna informs the user that time has passed, `action = None`.
3. **Map Query Safeguards (Map)**:
   - Empty/generic commands (`mở bản đồ`, `chỉ đường`): Anna asks which place to find, `action = None`.
   - Raw URI rejection: Queries matching `http://`, `https://`, `geo:`, etc. are rejected with a request for plain place names, `action = None`.
   - Length cap: Max 200 characters.
4. **Non-Action Fallthrough**:
   - Academic queries (`Học viện Kỹ thuật Mật mã ở đâu?`, `Quy chế thi lại?`, `Giải thích thuật toán RSA`) do not match action triggers and fall through safely to RAG / AI generation.
   - Conversational intents (`Xin chào`, `Cảm ơn bạn`) fall through to deterministic quick replies.

---

## 11. Backend Response Examples for All Three Action Types

### 1. Relative Timer
```json
{
  "user_message": {
    "id": "e81d7ad3-a330-4e56-821f-8cbbe9f00101",
    "role": "user",
    "text": "nhắc tôi học bài sau 5 phút",
    "emotion": null,
    "created_at": "2026-10-09T16:50:00.000000Z"
  },
  "assistant_message": {
    "id": "7fa1bc82-55cd-4f51-b054-c9f28df00202",
    "role": "assistant",
    "text": "Được rồi! Sau 5 phút Anna sẽ nhắc bạn học bài nhé.",
    "emotion": "happy",
    "action": {
      "type": "set_timer",
      "label": "Đặt hẹn giờ 5 phút",
      "message": "Học bài",
      "duration_seconds": 300,
      "title": null,
      "start_at": null,
      "end_at": null,
      "query": null
    },
    "created_at": "2026-10-09T16:50:00.000000Z"
  },
  "sources": [],
  "action": {
    "type": "set_timer",
    "label": "Đặt hẹn giờ 5 phút",
    "message": "Học bài",
    "duration_seconds": 300,
    "title": null,
    "start_at": null,
    "end_at": null,
    "query": null
  }
}
```

### 2. Calendar Event
```json
{
  "user_message": {
    "id": "a11d7ad3-a330-4e56-821f-8cbbe9f00103",
    "role": "user",
    "text": "đặt lịch nộp bài lúc 8 giờ tối mai",
    "emotion": null,
    "created_at": "2026-10-09T16:50:00.000000Z"
  },
  "assistant_message": {
    "id": "b2a1bc82-55cd-4f51-b054-c9f28df00204",
    "role": "assistant",
    "text": "Mình đã chuẩn bị lịch hẹn \"Nộp bài\" cho bạn rồi nè. Bạn nhấn nút bên dưới để mở ứng dụng Lịch và xác nhận nhé!",
    "emotion": "happy",
    "action": {
      "type": "create_calendar_event",
      "label": "Mở lịch để xác nhận",
      "message": null,
      "duration_seconds": null,
      "title": "Nộp bài",
      "start_at": "2026-10-10T20:00:00+07:00",
      "end_at": "2026-10-10T20:30:00+07:00",
      "query": null
    },
    "created_at": "2026-10-09T16:50:00.000000Z"
  },
  "sources": [],
  "action": {
    "type": "create_calendar_event",
    "label": "Mở lịch để xác nhận",
    "message": null,
    "duration_seconds": null,
    "title": "Nộp bài",
    "start_at": "2026-10-10T20:00:00+07:00",
    "end_at": "2026-10-10T20:30:00+07:00",
    "query": null
  }
}
```

### 3. Map Search
```json
{
  "user_message": {
    "id": "c31d7ad3-a330-4e56-821f-8cbbe9f00105",
    "role": "user",
    "text": "tìm Học viện Kỹ thuật Mật mã trên bản đồ",
    "emotion": null,
    "created_at": "2026-10-09T16:50:00.000000Z"
  },
  "assistant_message": {
    "id": "d4a1bc82-55cd-4f51-b054-c9f28df00206",
    "role": "assistant",
    "text": "Mình đã tìm thấy địa điểm \"Học viện Kỹ thuật Mật mã\" cho bạn. Bạn bấm nút bên dưới để mở bản đồ nhé!",
    "emotion": "happy",
    "action": {
      "type": "map_search",
      "label": "Mở bản đồ",
      "message": null,
      "duration_seconds": null,
      "title": null,
      "start_at": null,
      "end_at": null,
      "query": "Học viện Kỹ thuật Mật mã"
    },
    "created_at": "2026-10-09T16:50:00.000000Z"
  },
  "sources": [],
  "action": {
    "type": "map_search",
    "label": "Mở bản đồ",
    "message": null,
    "duration_seconds": null,
    "title": null,
    "start_at": null,
    "end_at": null,
    "query": "Học viện Kỹ thuật Mật mã"
  }
}
```

---

## 12. Android Confirmation and Intent Behavior

1. **Explicit Confirmation**: Action buttons render as compact `ElevatedButton` cards beneath assistant bubbles. No Intent is dispatched automatically upon message receipt.
2. **Timer Intent**:
   - Intent: `Intent(AlarmClock.ACTION_SET_TIMER)`
   - Extras: `EXTRA_MESSAGE = payload.message`, `EXTRA_LENGTH = payload.durationSeconds`, `EXTRA_SKIP_UI = true`.
   - Error handling: Catches `ActivityNotFoundException` $\rightarrow$ Toast: `"Không tìm thấy ứng dụng hẹn giờ trên thiết bị."`
3. **Calendar Intent**:
   - Intent: `Intent(Intent.ACTION_INSERT)` with `data = CalendarContract.Events.CONTENT_URI`
   - Extras: `Events.TITLE`, `EXTRA_EVENT_BEGIN_TIME`, `EXTRA_EVENT_END_TIME`, `Events.DESCRIPTION = "Được tạo bởi trợ lý ảo Anna"`.
   - Pre-fills system calendar form without silently creating an event; user must review and tap Save/Cancel.
   - Error handling: Catches `ActivityNotFoundException` $\rightarrow$ Toast: `"Không tìm thấy ứng dụng lịch trên thiết bị."`
4. **Map Intent**:
   - Intent: `Intent(Intent.ACTION_VIEW)` with `Uri.parse("geo:0,0?q=" + Uri.encode(payload.query))`
   - Resolves generically to any compatible map application without hardcoding package names.
   - Error handling: Catches `ActivityNotFoundException` $\rightarrow$ Toast: `"Không tìm thấy ứng dụng bản đồ trên thiết bị."`
5. **Debouncing**: `canClickAction()` enforces a 1000 ms guard preventing rapid repeated taps.

---

## 13. Permissions Added and Why

Only **one** permission was added to `android/app/src/main/AndroidManifest.xml`:
```xml
<uses-permission android:name="com.android.alarm.permission.SET_ALARM" />
```
- **Why**: Required by Android OS when dispatching `AlarmClock.ACTION_SET_TIMER` with `EXTRA_SKIP_UI = true`.
- **Calendar**: `ACTION_INSERT` on `CalendarContract.Events.CONTENT_URI` launches the system calendar editor activity; no read/write permissions required.
- **Maps**: `ACTION_VIEW` on generic `geo:` URIs requires no permissions.

---

## 14. Targeted Test Results

### Backend Tests
- **Command**:
  ```powershell
  python -m pytest -q -p no:cacheprovider tests/test_assistant_action_service.py tests/test_quick_reply.py
  ```
- **Outcome**: **119 passed, 0 failed, 1 warning in 0.48s**.
  - `test_assistant_action_service.py`: 24 passed (timers, calendars, maps, clarifications, security, route persistence, idempotency).
  - `test_quick_reply.py`: 95 passed (all quick-reply intent and route regressions).
- **Final complete backend suite**: `python -m pytest -q -p no:cacheprovider tests` — **352 passed, 1 warning**.

---

## 15. Android Unit-Test Result and Test Count

- **Command**:
  ```powershell
  $env:JAVA_HOME = "C:\Program Files\Android\Android Studio\jbr"; $env:ANDROID_HOME = "$env:LOCALAPPDATA\Android\Sdk"; .\gradlew.bat testDebugUnitTest
  ```
- **Final outcome**: `BUILD SUCCESSFUL in 1m 12s`. **109 passed, 0 failed, 0 errors, 0 skipped** across 10 test suites:
  - `Stage11AssistantActionsAndEmotionTest`: 18 passed *(New)*
  - `VoiceInputTest`: 9 passed
  - `SpeechAnimationSyncTest`: 12 passed
  - `ChatAnimationIntegrationTest`: 9 passed
  - `SpeechSettingsAndEventTest`: 17 passed
  - `CharacterAnimationPlayerTest`: 10 passed
  - `CharacterFrameResourcesTest`: 6 passed
  - `AnimationFpsSettingsTest`: 16 passed
  - `ChatDisplaySettingsTest`: 5 passed
  - `UnitTest`: 7 passed

---

## 16. assembleDebug Result and APK Path

- **Command**:
  ```powershell
  $env:JAVA_HOME = "C:\Program Files\Android\Android Studio\jbr"; $env:ANDROID_HOME = "$env:LOCALAPPDATA\Android\Sdk"; .\gradlew.bat assembleDebug
  ```
- **Final outcome**: `BUILD SUCCESSFUL in 46s` (37 actionable tasks: 3 executed, 34 up-to-date).
- **APK Path**:
  [`D:\nam5\semester_1\advance_android\01_trolyAI\troLyAo_ani_integration\android\app\build\outputs\apk\debug\app-debug.apk`](file:///D:/nam5/semester_1/advance_android/01_trolyAI/troLyAo_ani_integration/android/app/build/outputs/apk/debug/app-debug.apk)

---

## 17. compileall and git diff --check Results

- **Python compileall**:
  ```powershell
  python -m compileall -q app tests
  ```
  Result: Clean (exit code 0, zero syntax or byte-compile errors).
- **Git diff check**:
  ```powershell
  git diff --check
  ```
  Result: Clean (exit code 0, zero whitespace issues or conflict markers).

---

## 18. Confirmation of Zero Real External API Calls

- **Confirmed**: No real Gemini, Groq, embedding, map, weather, or external network API calls occurred during development or verification.
- All testing utilized deterministic local parsing, unit test mocks, and offline local test runners.

---

## 19. Confirmation of Zero Automatic App Launches

- **Confirmed**: External applications are never launched upon reply arrival.
- Responses containing actions display an in-chat button card.
- The action Intent is dispatched strictly upon an explicit user tap on the action button.

---

## 20. Known Limitations

1. **In-Memory Action Persistence**: Proposed action button metadata is retained in the active chat session memory (`ChatUiState.activeActions`). If the app process terminates or chat history is reloaded from Room, old conversation messages display the assistant text and emotion, but historical action buttons are not rendered. This preserves the existing Room schema without risking an unmigrated database crash.
2. **Relative Day Granularity**: The MVP calendar parser supports `hôm nay` (today) and `ngày mai` / `mai` (tomorrow) with precise hours/minutes. Arbitrary dates (e.g. "ngày 15 tháng 11") are treated as ambiguous and prompt the user for clarification.
3. **Emulator Pre-installs**: Default emulator images lacking Google Play Services or Clock/Maps apps will trigger the friendly Vietnamese fallback Toast rather than opening external apps.

---

## 21. Physical-Device Tests Still Pending

The following manual device tests have passed all unit and build verifications and remain pending on physical hardware:

1. [ ] Send `"Nhắc tôi học bài sau 5 phút nữa."` $\rightarrow$ Verify Anna responds and displays `"⏰ Đặt hẹn giờ 5 phút"`.
2. [ ] Tap the timer button $\rightarrow$ Confirm Android Clock starts a 5-minute timer named `"Học bài"`.
3. [ ] Send `"Đặt lịch học Android lúc 8 giờ tối mai."` $\rightarrow$ Verify Anna responds and displays `"📅 Mở lịch để xác nhận"`.
4. [ ] Tap the calendar button $\rightarrow$ Confirm Android Calendar opens with pre-filled title `"Học Android"` and tomorrow 20:00 time.
5. [ ] Send `"Tìm Học viện Kỹ thuật Mật mã trên bản đồ."` $\rightarrow$ Verify Anna responds and displays `"📍 Mở bản đồ"`.
6. [ ] Tap the map button $\rightarrow$ Confirm Android Maps opens centered on `"Học viện Kỹ thuật Mật mã"`.
7. [ ] Send `"Nhắc tôi học bài"` without duration $\rightarrow$ Verify Anna asks for clarification and shows no button.
8. [ ] Send an academic question (e.g. `"Quy chế thi của học viện"`) $\rightarrow$ Confirm normal response without action buttons.
9. [ ] Test `happy`, `sad`, and `surprised` responses $\rightarrow$ Confirm final emotion plays completely through frame 15/21/23 before returning to `idle`.
10. [ ] Confirm `talk` remains synchronized with TTS speaking duration.
11. [ ] Confirm voice input microphone button continues to work normally.

---

## 22. Pre-commit git status --short

```text
 M android/app/build.gradle.kts
 M android/app/src/main/AndroidManifest.xml
 M android/app/src/main/java/com/example/assistant/data/remote/Dtos.kt
 M android/app/src/main/java/com/example/assistant/data/repo/ChatRepository.kt
 M android/app/src/main/java/com/example/assistant/ui/chat/ChatScreen.kt
 M android/app/src/main/java/com/example/assistant/ui/chat/ChatViewModel.kt
 M android/app/src/test/java/com/example/assistant/ui/chat/SpeechAnimationSyncTest.kt
 M backend/app/api/v1/conversations.py
 M backend/app/schemas/conversation.py
?? android-stage10-review.zip
?? android/app/src/main/java/com/example/assistant/ui/chat/AssistantActionDispatcher.kt
?? android/app/src/test/java/com/example/assistant/ui/chat/Stage11AssistantActionsAndEmotionTest.kt
?? backend/app/services/assistant_action_service.py
?? backend/tests/test_assistant_action_service.py
?? review/android-stage11-assistant-actions.md
```

---

## 23. Stage 11 Compatibility Fix: Context & External App Fallbacks

### Physical-Device Findings
During physical device integration testing of Stage 11:
1. `EXTRA_SKIP_UI` was confirmed functioning for timer configuration.
2. Direct ADB command using `geo:0,0?q=Ho%20Guom` successfully opened the installed map application, but tapping Anna's in-app map action button failed.
3. Direct ADB Calendar `ACTION_INSERT` with `CalendarContract.Events.CONTENT_URI` returned `unable to resolve Intent` because no local application resolved that action.
4. Investigation revealed that `LocalContext.current` requires `Intent.FLAG_ACTIVITY_NEW_TASK` when launching external tasks if the context is not directly an `Activity`. Additionally, map searches and calendar events require robust browser-based fallbacks when native target apps are unavailable.

### Context / New-Task Fix
- Added `prepareForContext(context: Context, intent: Intent): Intent`:
  ```kotlin
  internal fun prepareForContext(context: Context, intent: Intent): Intent {
      if (context !is Activity) {
          intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
      }
      return intent
  }
  ```
- Applied consistently to all action dispatches (timer, calendar native, calendar web fallback, map native, and map web fallback).
- Ensures non-Activity contexts safely open external applications in a new task without runtime exceptions, while avoiding unnecessary flags when an `Activity` context is available.

### Map HTTPS Web Fallback
- Primary intent attempts `geo:0,0?q=<encodedQuery>` via `Intent.ACTION_VIEW`.
- If `ActivityNotFoundException` is caught, Anna automatically falls back to the official Google Maps HTTPS search endpoint:
  ```
  https://www.google.com/maps/search/?api=1&query=<URI-encoded query>
  ```
- The query strictly originates from the validated plain `map_search` payload. Raw URIs from the backend are disallowed.
- If both native and web fallback fail, a friendly Vietnamese Toast is shown: `"Không tìm thấy ứng dụng bản đồ trên thiết bị."`.

### Calendar Web Template Fallback
- Primary intent attempts native `Intent.ACTION_INSERT` with `CalendarContract.Events.CONTENT_URI`.
- If `ActivityNotFoundException` is caught, Anna falls back to a safe Google Calendar web template URL via `Intent.ACTION_VIEW`:
  ```
  https://calendar.google.com/calendar/render?action=TEMPLATE&text=<TITLE>&dates=<START>/<END>&details=<DETAILS>
  ```
- Formats dates in UTC compact format `yyyyMMdd'T'HHmmss'Z'`.
- Includes description: `Được tạo bởi trợ lý ảo Anna`.
- All user-visible parameters are safely percent-encoded. The event is never created automatically; the user reviews and confirms in the browser.
- If both native and web fallback fail, a friendly Vietnamese Toast is shown: `"Không tìm thấy ứng dụng lịch trên thiết bị."`.

### Tests and Verification
- **Unit Tests (`Stage11AssistantActionsAndEmotionTest.kt`)**:
  - `testNonActivityContextAddsNewTaskFlag`: Verifies `FLAG_ACTIVITY_NEW_TASK` is added for non-Activity context.
  - `testActivityContextDoesNotAddUnnecessaryNewTaskFlag`: Verifies `FLAG_ACTIVITY_NEW_TASK` is not added for Activity context.
  - `testMapPrimaryIntentRemainsGeo`: Verifies `geo:` scheme and percent-encoded query.
  - `testMapBrowserFallbackUrlAndHost`: Verifies `https://www.google.com/maps/search/?api=1&query=` endpoint.
  - `testCalendarNativeIntentRemainsPrimaryAction`: Verifies native `ACTION_INSERT` payload structure.
  - `testCalendarBrowserFallbackContainsUtcFormattedDatesAndDetails`: Verifies `yyyyMMdd'T'HHmmss'Z'` UTC formatting, title, and description.
  - `testNoActionLaunchedAutomatically`: Verifies actions remain inert until explicit button press.
- **UTF-8 Integrity**: Preserved Vietnamese strings (`"Được tạo bởi trợ lý ảo Anna"`, `"Đặt hẹn giờ"`, `"Mở lịch để xác nhận"`, `"Mở bản đồ"`, and error messages).
- **Build Output**: `android/app/build/outputs/apk/debug/app-debug.apk`.

### Required Physical-Device Retest
1. [ ] Tap **"Mở bản đồ"** on physical device $\rightarrow$ Verify Maps opens with `geo:0,0?q=...` or browser opens Google Maps search.
2. [ ] Tap **"Mở lịch để xác nhận"** on device where `ACTION_INSERT` was unresolved $\rightarrow$ Verify browser opens Google Calendar web template with pre-filled title, time, and description.
3. [ ] Tap **"Đặt hẹn giờ"** on physical device $\rightarrow$ Verify Clock app starts timer without UI crash.
