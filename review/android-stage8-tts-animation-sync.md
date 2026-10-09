# Stage 8 — Android Text-to-Speech Animation Synchronization

## 1. Final verdict

**READY FOR DEVICE RETEST**

The character animation lifecycle has been synchronized with Android's `TextToSpeech` engine lifecycle via `UtteranceProgressListener`. The character reliably loops `talk` at 10 FPS for the entire duration of the spoken reply, briefly displays non-neutral response emotions (`happy`, `sad`, `surprised`) upon speech completion, immediately returns to `idle` for neutral responses, and safely handles cancellations, errors, and screen disposal without getting stuck.

---

## 2. Current path, branch, and HEAD

- **Worktree path**: `D:\nam5\semester_1\advance_android\01_trolyAI\troLyAo_ani_integration`
- **Current branch**: `fix/android-tts-animation-sync`
- **HEAD commit**: `23f7fd6eab03012e7f420e7b91a58f8a027ba20e` (`chore: prepare Android and AI backend for device testing`)

---

## 3. Confirmed root cause of premature idle transition

Before this stage, there was no connection between Android's TTS engine lifecycle and character animation states:

1. **Neutral responses cut off by hardcoded timer**: `ChatViewModel` scheduled an unconditional `delay(TALKING_MS)` (where `TALKING_MS = 2000L`) that forced the character back to `IDLE` after only 2.0 seconds, regardless of how long TTS actually spoke.
2. **Emotional responses never displayed `talk`**: For non-neutral replies (`HAPPY`, `SAD`, `SURPRISED`), `ChatViewModel` set `characterState = TALKING` and `emotion = emotion` immediately upon reply receipt. `CharacterAnimationPlayer` mapped `TALKING + HAPPY` directly to the `happy` one-shot animation (15 frames @ 10 FPS = 1500 ms) instead of `talk`. Once the one-shot completed (1.5s), `onCharacterAnimationFinished()` immediately transitioned to `IDLE`, completely cutting off while TTS was still speaking.
3. **No utterance progress tracking**: `VietnameseTtsHelper` never attached an `UtteranceProgressListener` to the Android `TextToSpeech` engine and exposed no lifecycle callbacks (`onStart`, `onDone`, `onError`, `onStop`).

---

## 4. Exact animation state flow before and after the change

### Before:
```
User sends message:
  THINKING (loop)
    ↓
Reply received:
  - If HAPPY: TALKING + HAPPY immediately (plays 1500ms one-shot, talk animation skipped)
  - If NEUTRAL: TALKING + NEUTRAL (plays talk for fixed 2000ms timer)
    ↓
Timer expires / one-shot ends (1.5s - 2.0s):
  IDLE + NEUTRAL (prematurely returns to idle while TTS is still speaking)
```

### After:
```
User sends message:
  THINKING (loop)
    ↓
Reply received (TTS enabled):
  Remains in THINKING until TTS audio engine actually starts speaking
    ↓
TTS onStart(utteranceId):
  TALKING + NEUTRAL (loops "talk" animation at configured 10 FPS for full real speech duration)
    ↓
TTS onDone(utteranceId):
  - If non-neutral (HAPPY, SAD, SURPRISED):
      TALKING + responseEmotion (briefly shows emotion for EMOTION_DISPLAY_DURATION_MS = 1000L or until one-shot completes)
        ↓
      IDLE + NEUTRAL
  - If neutral:
      IDLE + NEUTRAL (immediately returns to idle)
```

---

## 5. Every changed/added file and why

| File | Change type | Rationale |
|---|---|---|
| [`android/app/src/main/java/com/example/assistant/speech/VietnameseTtsHelper.kt`](file:///D:/nam5/semester_1/advance_android/01_trolyAI/troLyAo_ani_integration/android/app/src/main/java/com/example/assistant/speech/VietnameseTtsHelper.kt) | Modified | Added `TtsProgressListener` interface; attached Android `UtteranceProgressListener` to `TextToSpeech` engine; tracked `utteranceId` in `speak()`, `PendingSpeech`, and `speakInternal()`; forwarded `onStart`, `onDone`, `onError`, and `onStop` callbacks; detached listener on `shutdown()`. |
| [`android/app/src/main/java/com/example/assistant/ui/chat/ChatViewModel.kt`](file:///D:/nam5/semester_1/advance_android/01_trolyAI/troLyAo_ani_integration/android/app/src/main/java/com/example/assistant/ui/chat/ChatViewModel.kt) | Modified | Introduced `SpeechAnimationCoordinator` to centralize state transitions; added `SpeechEvent(utteranceId, text)`; introduced `EMOTION_DISPLAY_DURATION_MS = 1000L`; added `stopSpeechEvents` flow; added handlers for speech callbacks (`onSpeechStarted`, `onSpeechCompleted`, `onSpeechError`, `onSpeechStopped`, `onSpeechNotStarted`, `onScreenDisposed`, `setTtsEnabled`); removed hardcoded 2000ms delay. |
| [`android/app/src/main/java/com/example/assistant/ui/chat/ChatScreen.kt`](file:///D:/nam5/semester_1/advance_android/01_trolyAI/troLyAo_ani_integration/android/app/src/main/java/com/example/assistant/ui/chat/ChatScreen.kt) | Modified | Registered `ttsHelper.listener` to invoke `vm.onSpeech*` callbacks; hooked `onDispose` to stop TTS and call `vm.onScreenDisposed()`; synchronized `vm.setTtsEnabled()`; passed `event.utteranceId` to `ttsHelper.speak()`; collected `stopSpeechEvents` to immediately stop playback. |
| [`android/app/src/test/java/com/example/assistant/ui/chat/SpeechAnimationSyncTest.kt`](file:///D:/nam5/semester_1/advance_android/01_trolyAI/troLyAo_ani_integration/android/app/src/test/java/com/example/assistant/ui/chat/SpeechAnimationSyncTest.kt) | Added | 12 targeted offline unit tests covering the complete speech-animation state matrix, utterance validation, and error recovery. |

---

## 6. Unique utterance IDs and stale callback handling

- Each new assistant message generates a unique `UUID.randomUUID().toString()` as its `utteranceId`.
- `SpeechAnimationCoordinator` stores this as `activeUtteranceId`.
- The `utteranceId` is emitted via `SpeechEvent` and passed to `VietnameseTtsHelper.speak(...)`, which registers it with Android's `TextToSpeech` engine.
- Every callback (`onStart`, `onDone`, `onError`, `onStop`) forwards the `utteranceId`.
- `SpeechAnimationCoordinator` verifies that `utteranceId == activeUtteranceId`:
  - If the IDs match: the state transition proceeds.
  - If the IDs do not match (e.g. from an older utterance): the callback returns `false` and is completely ignored, preventing stale callbacks from overwriting the animation state of a newer request.

---

## 7. Behavior across scenarios

- **TTS enabled**:
  - Sending message: enters `THINKING`.
  - Backend reply arrives: prepares utterance while remaining `THINKING`.
  - Audio starts (`onStart`): enters `TALKING` + `NEUTRAL` (loops `talk` animation at 10 FPS).
  - Speech finishes (`onDone`): non-neutral emotion displayed for `EMOTION_DISPLAY_DURATION_MS` (1000 ms), then enters `IDLE`. Neutral responses enter `IDLE` immediately.
- **TTS disabled**:
  - Shows response emotion briefly (`EMOTION_DISPLAY_DURATION_MS = 1000L`), then returns to `IDLE`.
- **TTS start failure / unavailable engine**:
  - Triggers `onSpeechError(utteranceId)`, cleanly exiting `TALKING` to display the response emotion briefly (if non-neutral) or directly `IDLE`. UI is never stuck in `TALKING`.
- **TTS onError**:
  - Safely exits `TALKING`, displays response emotion briefly if appropriate, then returns to `IDLE`.
- **Interrupted speech**:
  - `onSpeechStopped(utteranceId)` clears active utterance and transitions character directly to `IDLE` + `NEUTRAL`.
- **New request while speech is active**:
  - `send()` immediately clears `activeUtteranceId`, cancels active jobs, emits `stopSpeechEvents` to stop audio playback, and enters `THINKING`. Any late callbacks from the previous utterance are rejected.
- **Screen disposal**:
  - `DisposableEffect.onDispose` detaches listener, invokes `ttsHelper.stop()`, and calls `vm.onScreenDisposed()`, cancelling background jobs and restoring `IDLE` + `NEUTRAL`.

---

## 8. Targeted test commands and results

- **Command**:
  ```powershell
  $env:JAVA_HOME = "C:\Program Files\Android\Android Studio\jbr"; $env:ANDROID_HOME = "C:\Users\trong\AppData\Local\Android\Sdk"; .\gradlew.bat testDebugUnitTest
  ```
- **Result**: `BUILD SUCCESSFUL in 33s`. 82 tests executed across 8 test suites, **82 passed, 0 failed, 0 errors, 0 skipped**.
  - `com.example.assistant.ui.chat.SpeechAnimationSyncTest`: 12 passed
  - `com.example.assistant.ui.chat.ChatAnimationIntegrationTest`: 9 passed
  - `com.example.assistant.speech.SpeechSettingsAndEventTest`: 17 passed
  - `com.example.assistant.ui.character.CharacterAnimationPlayerTest`: 10 passed
  - `com.example.assistant.ui.character.CharacterFrameResourcesTest`: 6 passed
  - `com.example.assistant.domain.AnimationFpsSettingsTest`: 16 passed
  - `com.example.assistant.domain.ChatDisplaySettingsTest`: 5 passed
  - `com.example.assistant.UnitTest`: 7 passed

---

## 9. assembleDebug result and APK path

- **Command**:
  ```powershell
  $env:JAVA_HOME = "C:\Program Files\Android\Android Studio\jbr"; $env:ANDROID_HOME = "C:\Users\trong\AppData\Local\Android\Sdk"; .\gradlew.bat assembleDebug
  ```
- **Result**: `BUILD SUCCESSFUL in 8s`, 37 actionable tasks (4 executed, 33 up-to-date).
- **APK path**:
  [`D:\nam5\semester_1\advance_android\01_trolyAI\troLyAo_ani_integration\android\app\build\outputs\apk\debug\app-debug.apk`](file:///D:/nam5/semester_1/advance_android/01_trolyAI/troLyAo_ani_integration/android/app/build/outputs/apk/debug/app-debug.apk)

---

## 10. git diff --check result

- **Command**: `git diff --check`
- **Result**: Clean (exit code 0, no whitespace errors or merge conflict markers).

---

## 11. Confirmations

- **Backend untouched**: No backend files modified or referenced.
- **No API/network calls**: Zero calls to Gemini, Groq, or external network services.
- **No assets changed**: Animation frame drawables, image resources, and FPS settings are completely unchanged.
- **Git safety**: Nothing was staged, committed, merged, or pushed.

---

## 12. Full `git status --short`

```text
 M android/app/src/main/java/com/example/assistant/speech/VietnameseTtsHelper.kt
 M android/app/src/main/java/com/example/assistant/ui/chat/ChatScreen.kt
 M android/app/src/main/java/com/example/assistant/ui/chat/ChatViewModel.kt
?? android/app/src/test/java/com/example/assistant/ui/chat/SpeechAnimationSyncTest.kt
?? review/android-stage8-tts-animation-sync.md
```
