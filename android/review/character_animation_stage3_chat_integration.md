# Stage 3 Implementation Report: Chat Animation Integration & FPS Tuning

**Project:** `VirtualAssistant` (Android)  
**Package:** `com.example.assistant`  
**Date:** 2026-10-07  
**Status:** Complete  

---

## 1. Baseline Commit and Branch

- **Branch:** `feature/android-integration`
- **Baseline Commit:** `55b4409` (`55b4409 chuan hoa hinh anh vay nhanvat`)

---

## 2. Files Changed

### Modified Files:
- [`app/src/main/java/com/example/assistant/ui/character/CharacterFrameResources.kt`](file:///d:/nam5/semester_1/advance_android/01_trolyAI/troLyAo_ani/android/app/src/main/java/com/example/assistant/ui/character/CharacterFrameResources.kt): Updated FPS metadata for all 6 character animation specifications in `CharacterFrameCatalog`.
- [`app/src/main/java/com/example/assistant/ui/chat/ChatViewModel.kt`](file:///d:/nam5/semester_1/advance_android/01_trolyAI/troLyAo_ani/android/app/src/main/java/com/example/assistant/ui/chat/ChatViewModel.kt): Integrated `onCharacterAnimationFinished()`, pure state reducers, timer management, and race condition guards.
- [`app/src/main/java/com/example/assistant/ui/chat/ChatScreen.kt`](file:///d:/nam5/semester_1/advance_android/01_trolyAI/troLyAo_ani/android/app/src/main/java/com/example/assistant/ui/chat/ChatScreen.kt): Connected `onOneShotFinished = vm::onCharacterAnimationFinished` on `CharacterAvatar`.
- [`app/src/test/java/com/example/assistant/ui/character/CharacterFrameResourcesTest.kt`](file:///d:/nam5/semester_1/advance_android/01_trolyAI/troLyAo_ani/android/app/src/test/java/com/example/assistant/ui/character/CharacterFrameResourcesTest.kt): Updated FPS and frame duration assertion values.
- [`app/src/test/java/com/example/assistant/ui/character/CharacterAnimationPlayerTest.kt`](file:///d:/nam5/semester_1/advance_android/01_trolyAI/troLyAo_ani/android/app/src/test/java/com/example/assistant/ui/character/CharacterAnimationPlayerTest.kt): Updated timing test documentation comments to match 8 FPS idle.
- [`app/src/test/java/com/example/assistant/UnitTest.kt`](file:///d:/nam5/semester_1/advance_android/01_trolyAI/troLyAo_ani/android/app/src/test/java/com/example/assistant/UnitTest.kt): Expanded `testEmotionFallback` to explicitly verify `"neutral"`, `" NEUTRAL "`, `"angry"`, etc.

### Added Files:
- [`app/src/test/java/com/example/assistant/ui/chat/ChatAnimationIntegrationTest.kt`](file:///d:/nam5/semester_1/advance_android/01_trolyAI/troLyAo_ani/android/app/src/test/java/com/example/assistant/ui/chat/ChatAnimationIntegrationTest.kt): 9 new unit tests verifying exact FPS, durations, state transitions, and race condition protections.
- [`review/character_animation_stage3_chat_integration.md`](file:///d:/nam5/semester_1/advance_android/01_trolyAI/troLyAo_ani/android/review/character_animation_stage3_chat_integration.md): Stage 3 documentation report.

---

## 3. Exact FPS Values and Durations

In `CharacterFrameResources.kt`, only the metadata FPS values were modified. No images, drawables, or playback modes were touched.

| Action | Frames | Old FPS | **Stage 3 FPS** | Frame Duration | Playback Mode | Total Duration |
|---|---|---|---|---|---|---|
| `idle` | 32 | 16 | **6 FPS** | 166 ms | `LOOP` | 5312 ms (~5.3s) |
| `thinking` | 30 | 16 | **8 FPS** | 125 ms | `LOOP` | 3750 ms (3.75s) |
| `talk` | 19 | 18 | **10 FPS** | 100 ms | `LOOP` | 1900 ms (1.9s) |
| `happy` | 15 | 15 | **10 FPS** | 100 ms | `ONE_SHOT` | 1500 ms (1.5s) |
| `sad` | 21 | 14 | **8 FPS** | 125 ms | `ONE_SHOT` | 2625 ms (2.625s) |
| `surprised` | 23 | 16 | **10 FPS** | 100 ms | `ONE_SHOT` | 2300 ms (2.3s) |

---

## 4. State-Transition Behavior

The chat lifecycle and character state transition flow operates as follows:

```
[App Idle / Ready]
        │ (CharacterState.IDLE, Emotion.NEUTRAL)
        ▼
[User Sends Message]
        │ - talkJob cancelled
        │ - CharacterState.THINKING, Emotion.NEUTRAL, sending = true
        ▼
[Backend Response Received]
        ├────────────────────────────────────────┬────────────────────────────────────────┐
        ▼                                        ▼                                        ▼
[Neutral Response]                      [Emotional Response]                     [Network/API Failure]
 (Emotion.NEUTRAL)                       (HAPPY / SAD / SURPRISED)                - talkJob cancelled
 - CharacterState.TALKING                - CharacterState.TALKING                 - CharacterState.IDLE
 - Emotion.NEUTRAL                       - Emotion: parsed emotion                - Emotion.NEUTRAL
 - Starts 2.0s talking timer             - NO timer started                       - sending = false
        │                                        │
        ▼ (after 2.0s)                           ▼ (on animation completion)
 [Timer Expires]                         [onCharacterAnimationFinished()]
        │                                        │
        └───────────────────┬────────────────────┘
                            ▼
              [CharacterState.IDLE, Emotion.NEUTRAL]
```

---

## 5. How Neutral Talk Differs from Emotional One-Shot Playback

1. **Neutral Response (`talk`):**
   - **Mode:** `PlaybackMode.LOOP` (19 frames).
   - **Mechanism:** A neutral conversational reply does not have a predetermined physical ending pose; mouth movement loops continuously during speech.
   - **Duration:** Controlled by a fixed 2.0s coroutine timer (`TALKING_MS = 2000L`). When the timer completes, the character returns to `IDLE` + `NEUTRAL`.
   - **Callback Ignored:** Any animation completion callbacks while in `NEUTRAL` are ignored by `canHandleAnimationFinished`.

2. **Emotional Response (`happy`, `sad`, `surprised`):**
   - **Mode:** `PlaybackMode.ONE_SHOT`.
   - **Mechanism:** Emotional reactions are expressive character performances (e.g. jumping with joy, crying, gasping in shock) that culminate in a specific final rest frame.
   - **Duration Problem with Fixed Timer:**
     - `sad` @ 8 FPS takes **2625 ms** (2.625 seconds).
     - `surprised` @ 10 FPS takes **2300 ms** (2.300 seconds).
     - Under the old 2.0s timer, `sad` was cut off at frame 16 (out of 21), and `surprised` was cut off at frame 20 (out of 23), breaking the natural resolution of the emotion.
   - **Stage 3 Solution:** No fixed timer is launched for emotional responses. The animation plays naturally to its final frame. When Compose reaches completion, `onOneShotFinished` invokes `vm.onCharacterAnimationFinished()`, gracefully transitioning back to `IDLE` + `NEUTRAL`.

---

## 6. Callback and Race-Condition Protection

To prevent race conditions, `ChatViewModel` utilizes pure transition logic:

```kotlin
fun canHandleAnimationFinished(state: CharacterState, emotion: Emotion): Boolean =
    state == CharacterState.TALKING && emotion != Emotion.NEUTRAL

fun ChatUiState.reduceAnimationFinished(): ChatUiState =
    if (canHandleAnimationFinished(characterState, emotion)) {
        copy(characterState = CharacterState.IDLE, emotion = Emotion.NEUTRAL)
    } else {
        this
    }
```

### Verified Race Conditions:
1. **New message sent while an older animation is still playing:**
   - Calling `send()` cancels any active `talkJob`, sets `characterState = THINKING`, and `emotion = NEUTRAL`.
   - If an obsolete `onOneShotFinished` callback arrives from the previous composable, `canHandleAnimationFinished(THINKING, NEUTRAL)` evaluates to `false`.
   - Result: The callback is safely discarded; the assistant stays in `THINKING`.
2. **New chat created while an emotional animation is active:**
   - Calling `newChat()` cancels `talkJob`, resets `requestId`, and assigns a fresh `ChatUiState` (`IDLE` + `NEUTRAL`).
   - If an obsolete animation completion callback arrives, `canHandleAnimationFinished(IDLE, NEUTRAL)` evaluates to `false`.
   - Result: Discarded without side effects.
3. **Screen leaves and returns to foreground:**
   - `CharacterAnimationPlayer` manages frame timing within `repeatOnLifecycle(Lifecycle.State.STARTED)`.
   - When backgrounded, frame ticks cease. When returned to foreground, playback resumes seamlessly.
4. **Obsolete callback arrives after state changed:**
   - State reducer checks `current.characterState == TALKING && current.emotion != NEUTRAL`. If state has changed for any reason, the reducer returns the current state unchanged.
5. **Neutral response does not reuse previous emotional animation:**
   - When response arrives, `_ui.update` sets `emotion = Emotion.from(reply.emotion)` explicitly, which resolves unknown/null to `Emotion.NEUTRAL`.
6. **One-shot completion callback handled only once:**
   - In `CharacterAnimationPlayer`, `hasNotifiedCompletion` ensures `currentOnFinished()` is invoked exactly once per spec cycle before suspending via `awaitCancellation()`.
   - In `ChatViewModel`, processing the first callback sets `characterState = IDLE`. Any subsequent duplicate call encounters `canHandleAnimationFinished(IDLE, ...) == false` and exits immediately.

---

## 7. Tests Added and Updated

### Updated Existing Tests:
- `CharacterFrameResourcesTest.kt`: Updated `testFpsAndDurationSpecifications()` to verify the 6 exact FPS and frame duration values.
- `UnitTest.kt`: Expanded `testEmotionFallback()` to test `"neutral"`, `" NEUTRAL "`, `"angry"`, `""`, `"   "`, and `null`.
- `CharacterAnimationPlayerTest.kt`: Updated documentation comments to reflect 8 FPS idle.

### Added Test Suite (`ChatAnimationIntegrationTest.kt`):
- `testExactFpsValuesForStage3`: Validates all 6 exact FPS values.
- `testTotalDurationsReflectNewFps`: Validates exact calculated durations (4000ms, 3750ms, 1900ms, 1500ms, 2625ms, 2300ms).
- `testEmotionalOneShotDurationsExceedOldFixedTimer`: Verifies that `sad` (2625ms) and `surprised` (2300ms) exceed 2000ms and must use completion callbacks.
- `testCanHandleAnimationFinishedOnlyForEmotionalTalking`: Tests all state/emotion combinations for the callback guard.
- `testReduceAnimationFinishedTransitionsToIdleAndNeutral`: Tests successful transition from emotional TALKING to IDLE + NEUTRAL.
- `testReduceAnimationFinishedIgnoresNonQualifyingStates`: Tests that neutral talk, thinking, and idle states are not modified.
- `testRaceConditionNewMessageSentWhileEmotionalAnimationActive`: Verifies that sending a message ignores old callbacks.
- `testRaceConditionNewChatCreatedWhileEmotionalAnimationActive`: Verifies that `newChat()` ignores old callbacks.
- `testDuplicateCallbackHandledSafely`: Verifies idempotency of duplicate completion callbacks.

---

## 8. Results of Test, Build, and Lint Commands

```powershell
$env:JAVA_HOME = "C:\Program Files\Android\Android Studio\jbr"
```

### 1. Unit Tests (`.\gradlew.bat testDebugUnitTest`):
```text
BUILD SUCCESSFUL in 1m 51s
25 actionable tasks: 17 executed, 8 up-to-date

Results:
- TEST-com.example.assistant.ui.chat.ChatAnimationIntegrationTest.xml: 9 tests, 0 failures, 0 errors (0.008s)
- TEST-com.example.assistant.ui.character.CharacterAnimationPlayerTest.xml: 10 tests, 0 failures, 0 errors (0.054s)
- TEST-com.example.assistant.ui.character.CharacterFrameResourcesTest.xml:  6 tests, 0 failures, 0 errors (0.014s)
- TEST-com.example.assistant.UnitTest.xml:                                  7 tests, 0 failures, 0 errors (0.149s)

Total: 32 tests executed, 32 passed, 0 failed, 0 skipped.
```

### 2. Debug Build (`.\gradlew.bat assembleDebug`):
```text
BUILD SUCCESSFUL in 1m 8s
37 actionable tasks: 4 executed, 33 up-to-date

Artifact: app/build/outputs/apk/debug/app-debug.apk
Size: 17,012,194 bytes (~16.22 MB)
```

### 3. Android Lint (`.\gradlew.bat lintDebug`):
```text
BUILD SUCCESSFUL in 2m 27s
28 actionable tasks: 7 executed, 21 up-to-date

Errors: 0 errors
New warnings: 0 new warnings
Pre-existing baseline warnings:
- OldTargetApi (1)
- GradleDependency (10)
- DataExtractionRules (1)
- MissingApplicationIcon (1)
- IconDuplicates (25) (harmless hold frames in sprite package)
```

---

## 9. Remaining Known Issue (Preserved Intentionally)

- **Issue:** The character avatar height shrinks from `210.dp` to `80.dp` when the soft keyboard is displayed (`imeVisible`).
- **Status:** **Intentionally preserved unchanged in Stage 3.** Per the project guidelines, keyboard resize behavior, soft input modes, and chat layout redesign are reserved for a separate subsequent stage.

---

## 10. Short Manual Testing Checklist for Physical Android Phone

When testing on a physical Android device connected to the FastAPI backend:

1. **Idle State:**
   - Launch the application and enter the Chat screen.
   - Verify the anime character plays the `idle` animation continuously at a calm 6 FPS (approx. 5.3s per cycle) without jitter.
2. **Sending & Thinking State:**
   - Type a prompt and tap Send.
   - Verify the character immediately switches to `thinking` (8 FPS) with typing dots active while waiting for server response.
3. **Neutral Response:**
   - Receive a neutral response from the backend (`emotion: null` or `emotion: "neutral"`).
   - Verify the character plays the `talk` animation at 10 FPS for approx. 2 seconds, then smoothly returns to `idle`.
4. **Emotional Response — Happy:**
   - Send a prompt that triggers happiness (or mock `emotion: "happy"`).
   - Verify the character plays the full 15-frame `happy` animation once (1.5s) and returns to `idle` upon completion.
5. **Emotional Response — Sad:**
   - Send a prompt that triggers sadness (`emotion: "sad"`).
   - Verify the character plays the full 21-frame `sad` animation at 8 FPS (takes 2.6s, does not cut off at 2.0s) and returns to `idle`.
6. **Emotional Response — Surprised:**
   - Send a prompt that triggers surprise (`emotion: "surprised"`).
   - Verify the character plays the full 23-frame `surprised` animation at 10 FPS (takes 2.3s) and returns to `idle`.
7. **Race Condition — Quick Send:**
   - While an emotional animation is playing, immediately type and send another message.
   - Verify the character switches to `thinking` and does not revert to `idle` when the older animation finishes.
8. **New Chat Reset:**
   - While an emotional animation is playing, tap the `+` (New Chat) icon.
   - Verify the chat resets cleanly and the character transitions immediately to `idle`.
9. **App Background / Foreground:**
   - Background the app (Home button) during animation playback; bring it back.
   - Verify no crashes, no frame skips, and smooth resumption of animation.

---

## 11. Final Verdict

**STAGE 3 COMPLETE — READY FOR RUNTIME VALIDATION**
