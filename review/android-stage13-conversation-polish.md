# Android Stage 13 — Conversation Polish

Final verdict: **READY FOR DEVICE TEST**

## Repository and base

- Repository: `D:\nam5\semester_1\advance_android\01_trolyAI\troLyAo_ani_integration`.
- Stage 13 branch: `feature/android-stage13-conversation-polish`.
- Exact base: `origin/feature/local-time-quick-replies`, SHA `ef63047e3320175b15d0e51982d323832f77eac5`.
- Fetch confirmed `origin/main` at `8121d510a845dac761438f6e597e68d8f1872b1d`. Stage 12 is not contained in that main, so its verified remote HEAD was selected as instructed. No merge into main.
- Stage 12 required checkpointing: initial working tree contained exactly the three reviewed Stage 12 paths, with no staged changes. Reviewed the service diff, new tests, and report; `git diff --check` passed. Reran the report's targeted command: **194 passed**, one existing Starlette/httpx deprecation warning. The reviewed report already records **416 passed** for the full backend suite against this diff, so that suite was not redundantly rerun.
- Stage 12 commit: `ef63047e3320175b15d0e51982d323832f77eac5`, `feat(backend): add local time and date quick replies`; pushed successfully to `origin/feature/local-time-quick-replies` before creating Stage 13.
- Git metadata belongs to a linked worktree in the sibling checkout. Authorized Git writes required sandbox escalation. Authorized Gradle commands likewise required access to the existing Gradle cache/SDK. No source files outside this repository were edited.

## Exact Stage 13 files

Modified:

1. `android/app/src/main/java/com/example/assistant/data/local/SettingsStore.kt`
2. `android/app/src/main/java/com/example/assistant/data/repo/ChatRepository.kt`
3. `android/app/src/main/java/com/example/assistant/domain/ChatDisplaySettings.kt`
4. `android/app/src/main/java/com/example/assistant/ui/chat/ChatScreen.kt`
5. `android/app/src/main/java/com/example/assistant/ui/chat/ChatViewModel.kt`
6. `android/app/src/main/java/com/example/assistant/ui/settings/SettingsScreen.kt`
7. `android/app/src/main/java/com/example/assistant/ui/settings/SettingsViewModel.kt`
8. `android/app/src/test/java/com/example/assistant/ui/chat/SpeechAnimationSyncTest.kt`

Added:

9. `android/app/src/main/java/com/example/assistant/ui/chat/ReplyReveal.kt`
10. `android/app/src/test/java/com/example/assistant/domain/TypewriterSettingsTest.kt`
11. `android/app/src/test/java/com/example/assistant/ui/chat/ConversationPolishLifecycleTest.kt`
12. `android/app/src/test/java/com/example/assistant/ui/chat/ReplyRevealTest.kt`
13. `review/android-stage13-conversation-polish.md`

Stage 13 has no backend changes. The Stage 12 paths belong exclusively to its separate base commit.

## Existing architecture discovered

Inspected MainActivity, ChatScreen, ChatViewModel, MessageEntity/DAOs, ChatRepository, VietnameseTtsHelper, CharacterAvatar, CharacterAnimationPlayer, CharacterFrameResources, all three settings components, and the existing Android tests. Used `rg` to locate the relevant classes, callbacks, settings, UI controls, and tests before editing. No repository AGENTS.md was found.

- MainActivity collects DataStore speech, FPS, and display settings with lifecycle awareness and supplies CompositionLocals. Chat ViewModels are scoped to navigation entries, so selecting another conversation gets that entry's own state. No MainActivity change was necessary.
- Room stores complete immutable MessageEntity text. ChatRepository persists complete API responses and updates conversation metadata before returning the assistant reply. History is a Room flow; backend send events and history collection are separate.
- ChatViewModel already owns SpeechAnimationCoordinator, non-replayed speech/stop flows, unique utterance IDs, request IDs/retry drafts, and a watchdog derived from the complete emotion sequence plus 400 ms.
- VietnameseTtsHelper already queues speech during initialization, reports unavailable language/initialization/speech failures, uses QUEUE_FLUSH, and exposes start/done/error/stop callbacks and stop/shutdown cleanup. It remains unchanged.
- CharacterAvatar resolves the state/emotion spec and applies the existing FPS overrides. CharacterAnimationPlayer uses a lifecycle-aware frame clock, total sequence duration, one-shot completion, and restart keys. Happy has 15 frames, sad 21, surprised 23. Neutral talk loops; neutral has no separate final-emotion sequence. These files and every PNG are unchanged.
- No chat stop/replay buttons existed. Added one text control beneath only the latest assistant reply; settings' existing voice preview remains separate.

## Typewriter design and Unicode

`ReplyRevealPlanner` is pure and produces UTF-16 endpoints only at character boundaries. It uses standard-library `java.text.BreakIterator.getCharacterInstance(Locale.ROOT)`, conservatively joins combining marks, ZWJ sequences, emoji skin modifiers, emoji tag sequences, and regional-indicator flag pairs when older iterators expose internal boundaries. Surrogate pairs are never sliced arbitrarily. Tests cover Vietnamese, decomposed accents, surrogate emoji, skin tones, flags, keycaps, and joined family/profession emoji. No dependency was added.

`ReplyRevealController` is a ViewModel-owned presentation session with stable message IDs, a set of already presented/history IDs, and one immutable current reveal snapshot. Rendering reads the snapshot; recomposition cannot start a new reveal. Partial text is never written to Room, a domain message, a DTO, or the backend. All assistant response sources use the same path, including quick replies, RAG/provider/fallback responses and action text.

The repository's only addition is an optional local `beforeAssistantCached` notification after parsing the complete response and before the unchanged complete-row upsert. The ViewModel masks that exact incoming row until send completion starts its reveal. This prevents Room from flashing the full new reply during the existing conversation-metadata refresh. Other history rows and user rows remain immediately visible, including history arriving during a request. No API signature, DTO, persistence contents/order, timeout, or request ID behavior changed.

Timing:

- Target duration is `clusterCount * 20 ms`, clamped to **300–4500 ms**.
- Normal tick is **30 ms**. Endpoints distribute clusters over at most 150 ticks; long text reveals multiple clusters per tick.
- Very small replies use fewer ticks with longer intervals so even one character takes 300 ms.
- Examples tested: short greeting 300 ms; 100 clusters 1980 ms; 10,000 clusters 4500 ms.
- Empty text completes immediately. Disabled mode displays full text immediately. Timing is independent of animation FPS. Coroutine scheduling can introduce normal wall-clock jitter.
- Tapping the active bubble skips immediately and reports reveal completion. Completed bubbles have no skip click behavior.

## Setting

Added **Hiệu ứng hiện chữ dần** to settings, with a Vietnamese accessibility description. It extends existing ChatDisplaySettings and uses the existing preferences DataStore key `typewriter_enabled`. Default and missing-key fallback are both **true**. Toggling off skips an active reveal; future replies display completely. There is no speed slider, migration, dependency, or change to the existing font/FPS/speech/base URL keys or controls. Persistence tests recreate a real preferences DataStore and verify the toggle survives while saved font, talk FPS and TTS settings remain unchanged.

## Coordinated lifecycle

Extended the existing SpeechAnimationCoordinator rather than introducing another animation/TTS state machine. Its explicit phases are Idle, Thinking, RevealingOrSpeaking, and FinalEmotion. The reveal controller manages text presentation only.

| Event | Result |
| --- | --- |
| Send/retry starts | Cancel old reveal; invalidate speech token; stop output; Thinking with neutral emotion |
| Complete new response received | Start reveal and issue full-text TTS without waiting for either to finish; neutral talk while either is pending |
| Reveal finishes/skips before TTS | Remain neutral talk until speech terminates |
| TTS completes/errors/stops before reveal | Remain neutral talk until reveal completes/skips |
| Both terminate | Happy/sad/surprised FinalEmotion, one complete existing animation cycle, then Idle |
| TTS disabled/unavailable | Reveal alone holds talk; failure releases the speech condition |
| Typewriter disabled | Full text immediately; speech alone holds talk |
| Both disabled | Enter final emotion immediately, then Idle |
| Neutral response with both conditions complete | Existing direct Idle behavior; there is no neutral emotion one-shot asset |
| Backend failure | Cancel presentation and watchdog, invalidate output, Idle; existing retry/error draft behavior retained |

The existing complete-cycle callback and FPS-derived watchdog remain in use. Watchdog recovery is scheduled only in non-neutral final emotion, never while reveal or speech is active. Two older SpeechAnimationSyncTest expectations were intentionally updated: receipt now starts talk before speech's start callback, and stopping speech plays the final emotion instead of going directly idle.

## Cancellation and controls

- Reveal ticks run in a composable LaunchedEffect under `repeatOnLifecycle(STARTED)`, with nonblocking coroutine delays. Progress lives in the ViewModel, not composable remember state.
- New requests, new chat, conversation navigation/disposal, backend error, and lifecycle stop cancel the old presentation. Disposal/stop removes partial presentation so returning/recreation shows complete text without rerunning. Backend requests retain their existing ViewModel lifetime; a reply received while chat is inactive is stored and displayed fully without automatic speech/reveal.
- Navigation entries own separate conversation ViewModels. Leaving for history before deletion disposes/stops the old presentation; no delete or selection semantics were changed.
- Stable message IDs suppress historical/idempotent redisplay. Per-response/replay UUID tokens reject old reveal, start/done/error/stop and emotion callbacks. Animation restart keys and watchdog tokens bind playback to the current response.
- TTS progress is marshalled onto the composition's main coroutine scope before touching the coordinator. Composition disposal cancels those callbacks. Old helper callbacks cannot release a newer reply's talk state.
- **Dừng đọc** explicitly stops pending/active output and releases its speech condition even when the engine omits a stop callback. Reveal can continue. After both conditions complete, final emotion still plays.
- **Đọc lại** reads the complete latest assistant MessageEntity text, skips any remaining reveal, assigns a fresh utterance token, enters talk, then plays that message's full emotion cycle. Explicit replay works even with automatic TTS disabled. Sending during replay stops it and enters thinking.
- Text buttons and the skip action have Vietnamese accessibility labels; no icon library was added. Existing messages/history do not automatically reveal or speak.

## Verification

Executed from `android`:

```powershell
$env:JAVA_HOME = "C:\Program Files\Android\Android Studio\jbr"
$env:ANDROID_HOME = "$env:LOCALAPPDATA\Android\Sdk"
.\gradlew.bat testDebugUnitTest
.\gradlew.bat assembleDebug
```

Final test command: **BUILD SUCCESSFUL**, 16 seconds. Final build command: **BUILD SUCCESSFUL**, 4 seconds. Inspected every `app/build/test-results/testDebugUnitTest/TEST-*.xml` suite:

| Suite | Tests | Failures | Errors | Skipped |
| --- | ---: | ---: | ---: | ---: |
| AnimationFpsSettingsTest | 16 | 0 | 0 | 0 |
| ChatDisplaySettingsTest | 5 | 0 | 0 | 0 |
| TypewriterSettingsTest | 3 | 0 | 0 | 0 |
| SpeechSettingsAndEventTest | 17 | 0 | 0 | 0 |
| CharacterAnimationPlayerTest | 10 | 0 | 0 | 0 |
| CharacterFrameResourcesTest | 6 | 0 | 0 | 0 |
| ChatAnimationIntegrationTest | 9 | 0 | 0 | 0 |
| ConversationPolishLifecycleTest | 18 | 0 | 0 | 0 |
| ReplyRevealTest | 22 | 0 | 0 | 0 |
| SpeechAnimationSyncTest | 12 | 0 | 0 | 0 |
| Stage11AssistantActionsAndEmotionTest | 18 | 0 | 0 | 0 |
| VoiceInputTest | 9 | 0 | 0 | 0 |
| UnitTest | 7 | 0 | 0 | 0 |
| **Total** | **152** | **0** | **0** | **0** |

This includes all existing Android tests for chat integration, TTS sync, full-cycle emotions, FPS, font size, speech settings, voice input, reminder/timer, calendar, and map behavior, plus 43 added Stage 13 tests. Tests cover pure production planners/controllers/coordinator and actual preferences file persistence. They do not replace device validation of Compose rendering, lifecycle integration, or a particular TTS engine.

APK local path: `D:\nam5\semester_1\advance_android\01_trolyAI\troLyAo_ani_integration\android\app\build\outputs\apk\debug\app-debug.apk`. `git check-ignore` confirms it is ignored; it is neither tracked nor staged. No APK was installed on a device.

Root checks: `git diff --check` passed with no output; reviewed status, stat, name-status, and cached name-status. `git ls-files "*.apk" "*.zip" "*.db" "*.sqlite" "*.sqlite3" "local.properties" ".env"` returned no paths. No generated artifact, cache, database, ZIP, secret, local.properties, or environment file is included. Gradle temporarily created a Kotlin session marker which disappeared after its task finished; it was never staged or deleted manually.

Backend API paths, DTOs/fields, timeout values, RAG, embeddings, Gemini/Groq/fallback routing, actions, voice input, FPS, font-size behavior, PNG assets, package/SDK/Gradle configuration, base URL settings, panel proportions/transparency, and IME behavior are preserved. No real Gemini, Groq, embedding, or other AI API calls occurred; verification was local. Only authorized Git operations contacted the Git remote.

## Publication and final status

Only the 13 explicitly listed Stage 13 paths are eligible for staging. Publication uses `feat(android): add polished typewriter chat lifecycle` and pushes only `feature/android-stage13-conversation-polish` to origin. Nothing is merged into or pushed directly to main.

Full final `git status --short` at successful closeout is empty (no lines). The post-commit/push command verifies this; branch/commit/push output is recorded in the accompanying completion response.

```text
```

## Proposed device-test checklist

1. Install/open the local debug APK yourself. Use a local mocked backend for longer/custom responses if avoiding paid/external providers. Confirm the new setting defaults on; existing FPS, font and voice values are retained.
2. With automatic TTS on, send `Mấy giờ rồi?`. Expect thinking while waiting, then gradual text and talk; after reveal AND speech finish, observe one complete emotion cycle followed by idle.
3. With a mock response containing Vietnamese decomposed accents and `😀 👩‍💻 👍🏽 🇻🇳`, verify no broken intermediate characters. Try short, medium and very long replies; long reveal should finish around 4.5 seconds. Tap a revealing bubble to finish it; tap again and confirm no text change.
4. Slow speech to make TTS finish last; then use a short spoken reply/fast rate so reveal finishes last. Confirm talk lasts until both complete. Repeat with TTS disabled, typewriter disabled, and both disabled. Check an unavailable Vietnamese TTS engine if available.
5. During output tap Dừng đọc, then Đọc lại. Confirm replay reads the complete reply, including when automatic TTS is disabled; emotion completes afterward. Send another message during reveal, speech, replay and emotion: old callbacks must not interrupt the new thinking/reply.
6. During reveal/speech rotate, background/foreground, leave for settings through existing navigation, return, select another conversation, create a new chat, and delete the old conversation from history. Confirm audio stops, old presentation does not affect the new screen, and history displays fully without automatic replay. Also leave while the backend is pending, then return after it completes.
7. Toggle the setting off, restart the app, and confirm it persists; toggle back on. Exercise history reload and a local request-id replay: stored messages must stay complete, with no duplicate reveal or speech.
8. Check voice input still fills the draft without sending; test reminder/timer, calendar and map action buttons explicitly, using a mock/local backend. Confirm no action launches automatically. Verify keyboard/IME proportions, transparent panel, font changes, and animation FPS overrides.
9. Disconnect the local backend and send/retry a message. Confirm the existing error/draft behavior and idle recovery, then reconnect and retry without duplicate stored messages.
