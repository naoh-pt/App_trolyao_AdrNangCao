# Stage 14A — Demo question picker and guided scenarios

Verdict: **READY FOR DEVICE TEST**

- Repository: `D:\nam5\semester_1\advance_android\01_trolyAI\troLyAo_ani_integration`
- Branch: `feature/stage14-demo-weather`
- Base: `origin/main`, `b765d9945e6ca2961792350db44cd9cc58a96ac1`.
- Local main and origin/main matched at start. The completed `origin/fix/android-stage13-1-external-actions` branch is an ancestor of the base. Stage 12 quick replies, Stage 13 conversation polish, Android external actions, map punctuation and calendar language parsing are included.
- Backup: `backup/pre-stage14-20261021`, pushed and verified locally/remotely at exactly `b765d9945e6ca2961792350db44cd9cc58a96ac1`. It preserves all tracked source at the stable release.

## Exact files

Modified:

- `android/app/src/main/java/com/example/assistant/ui/chat/ChatScreen.kt`
- `android/app/src/main/java/com/example/assistant/ui/chat/ChatViewModel.kt`

Added:

- `android/app/src/main/java/com/example/assistant/ui/demo/DemoQuestionCatalog.kt`
- `android/app/src/main/java/com/example/assistant/ui/demo/DemoScenarioController.kt`
- `android/app/src/main/java/com/example/assistant/ui/demo/DemoQuestionSheet.kt`
- `android/app/src/test/java/com/example/assistant/ui/demo/DemoCatalogTest.kt`
- `android/app/src/test/java/com/example/assistant/ui/demo/DemoScenarioControllerTest.kt`
- `review/android-stage14a-demo-question-picker.md`

## Architecture and UI

The existing ChatViewModel owns ChatUiState and the draft; sending, request IDs, messages and speech already have their own established lifecycle. MainActivity navigation scopes that ViewModel to the chat entry. MessageBubble has a typewriter skip surface with a separate action button. The character layer and foreground panel already have fixed size/fraction and IME handling. These mechanisms are reused without changing their behavior.

A Material core List icon sits immediately left of the microphone in the existing single input row. Its Vietnamese content description is `Mở câu hỏi và kịch bản demo`. Opening clears focus and hides the keyboard, preserving the unsent draft. Dismissal does not request focus or show the keyboard. No character dimensions, chat panel proportions, keyboard inset rules, voice or send callbacks changed. The extra button uses the available input-row width without wrapping the row.

The Material ModalBottomSheet skips partial expansion; its content requests 85% of available height. Two tabs provide two-level navigation:

- **Kịch bản**: two-column cards lead to scenario details, ordered question rows, and an explicit Start button.
- **Theo nhóm**: two-column category cards lead to 4–5 compact question rows, with a visible `Quay lại` control. The categories are Trò chuyện (4), Thời gian (4), Học tập & RAG (4), Cảm xúc (4), Tiện ích (5), Thời tiết (4 disabled).

There is no search or carousel. Sheet selection and navigation do not invoke sending, speech, reveal, or animation methods. Normal sheet dismissal/back handling is retained.

All 25 prompts are local UTF-8 source data with stable IDs, no database, remote configuration, URL, executable content, or network loading. RAG and Internet/AI/backend requirements are informational labels; the tuition question explicitly shows `Cần nạp tài liệu RAG`. Material theme colors, standard minimum touch targets, accessible text labels, and the existing chat font-size setting for question/card text are used. Long prompt previews have two lines with ellipsis; the full prompt is always selected. Disabled Weather cards have disabled semantics and a visible Stage 14B label. No icon dependency was added.

## Scenarios and order

**Demo nhanh 3 phút — 4 steps**

1. Xin chào Anna
2. Mấy giờ rồi?
3. Nhắc tôi học bài sau 5 phút
4. Tìm trên bản đồ Học viện Kỹ thuật Mật mã

**Demo đầy đủ — 8 steps**

1. Xin chào Anna
2. Anna có thể giúp mình những gì?
3. Mấy giờ rồi?
4. Học phí đại học hệ chính quy là bao nhiêu tiền một tín chỉ?
5. Hôm nay mình hơi buồn và mất động lực học.
6. Nhắc tôi học bài sau 5 phút
7. Tạo lịch học Android lúc 8 giờ tối ngày mai
8. Tìm trên bản đồ Học viện Kỹ thuật Mật mã

**Demo không phụ thuộc quota — 6 steps**

Label: `Không cần quota AI; backend vẫn phải chạy`. This is not advertised as offline.

1. Xin chào Anna
2. Mấy giờ rồi?
3. Hôm nay là thứ mấy?
4. Nhắc tôi học bài sau 5 phút
5. Tạo lịch học Android lúc 8 giờ tối ngày mai
6. Tìm trên bản đồ Hồ Gươm.

## Draft and progress

Demo state is a field of the existing ChatUiState. A pure reducer changes only draft/demo fields; it has no repository, coroutine, TTS, animation, message creation or send dependency. Empty drafts receive the complete prompt and the sheet closes. Different nonblank drafts require a lightweight replacement dialog. Cancel preserves both draft and scenario progress. Confirmation checks the original draft snapshot; a concurrent input change requires another review. Sending and retry-pending states reject replacement. Selecting the same prompt needs no confirmation.

Starting a scenario selects step 1. A compact title/progress/question control appears above the input only while a scenario is active; tapping expands Previous, Next/Complete and Stop. Manual navigation fills drafts and is bounded at both ends. Replacing a nonblank draft during navigation uses the same confirmation. At the final step the expanded guide offers `Hoàn thành kịch bản`; completion marks progress without creating/deleting a conversation or sending. Stop clears scenario state and preserves the draft/messages. Selecting a standalone question stops the previous scenario only after an accepted selection.

No AI-text inspection or response-driven advancement exists. Recomposition does not select questions or advance steps. The existing ViewModel retains progress through rotation and navigation while its chat entry survives. Existing navigation that destroys that entry, process death, and new-chat reset can reset demo state. Switching conversation never automatically applies a prompt: every application requires an explicit picker or guide tap. No new navigation or persistence system was introduced.

Weather category and its four prepared questions remain disabled. Both UI enablement and reducer validation reject disabled selections. No scenario references Weather; no Weather request was implemented. Stage 14B requires a separate change after device verification.

## Verification

Commands from `android`, using existing Android Studio JBR and local Android SDK:

```powershell
$env:JAVA_HOME = "C:\Program Files\Android\Android Studio\jbr"
$env:ANDROID_HOME = "$env:LOCALAPPDATA\Android\Sdk"
.\gradlew.bat testDebugUnitTest assembleDebug
```

- Android XML results: **216 tests, 216 passed, 0 failures, 0 errors, 0 skipped**.
- Includes 30 new catalog/controller tests and all 186 existing regression tests (typewriter, TTS/animation, chat/history, voice input, actions/timer/calendar/maps, settings, FPS and font size).
- New tests cover stable unique IDs/order/references, disabled Weather, RAG/quota labels, Vietnamese strings, progress bounds/completion/switching/copies, draft replacement/cancel/concurrent edits, busy/retry guards, full prompt selection, and unchanged non-demo chat state.
- `assembleDebug`: **BUILD SUCCESSFUL**.
- Local APK: `D:\nam5\semester_1\advance_android\01_trolyAI\troLyAo_ani_integration\android\app\build\outputs\apk\debug\app-debug.apk`. Exists locally, ignored by Git, not tracked or staged; not installed.
- `git diff --check`: passed. Reviewed source diff and exact staged paths before commit.
- Artifact query (`git ls-files` for APK/ZIP/database/local.properties/.env): no tracked matches. No generated files or secrets staged.
- Backend source, API/DTO schemas, character assets, dependencies/Gradle, settings, backend URLs, local configuration, .env and main were untouched. Existing TTS, animation, typewriter, actions, conversation, voice-input and IME logic were preserved.
- No real external API calls occurred. Gradle/JVM tests use existing local fakes; no backend, Weather, Gemini, Groq, embedding or RAG request was made.

Full pre-commit `git status --short` (new directories contain only the exact files listed above):

```text
 M android/app/src/main/java/com/example/assistant/ui/chat/ChatScreen.kt
 M android/app/src/main/java/com/example/assistant/ui/chat/ChatViewModel.kt
?? android/app/src/main/java/com/example/assistant/ui/demo/
?? android/app/src/test/java/com/example/assistant/ui/demo/
?? review/android-stage14a-demo-question-picker.md
```

The final post-commit/push status is expected to be empty and is checked separately in the delivery response.

## Physical-device checklist

1. Open chat with a blank draft. Tap the List icon: verify keyboard hides, character remains stable, sheet opens near full height, and dismiss/back leaves the draft and keyboard unchanged.
2. Browse both tabs and all five enabled categories. Verify Vietnamese accents, two-column cards, Back, scrolling, and large font settings. Weather must show `Sắp có ở Stage 14B` and reject taps.
3. Select `Tìm trên bản đồ Hồ Gươm.`. Verify exact full draft, closed sheet, no new message/thinking/speech/animation, and no automatic keyboard. Edit the draft normally.
4. Enter a custom draft, select another question, and cancel replacement. Verify the original draft survives. Repeat and confirm replacement. No message should exist until Send.
5. Start Demo nhanh 3 phút. Verify step 1/4, expand guide, Previous bound, Next order, and confirmation when overwriting an unsent draft. Press Send explicitly for each desired step; existing responses/typewriter/TTS and action confirmations should work. Next must never send.
6. At step 4, complete manually. Verify completion state and final bound. Stop and verify draft/history unchanged. Start Demo đầy đủ (8 steps) and Demo không phụ thuộc quota (6 steps); verify orders and backend/quota/RAG labels.
7. Rotate with a scenario active. Open Settings and return using the existing navigation path; verify no duplicate steps or automatic sends, and progress retention wherever the existing chat ViewModel remains alive. Switch/new conversation and verify no prompt is automatically attached or sent.
8. Check microphone, normal send/edit/retry, TTS stop/replay, bubble reveal-skip, action-button isolation, timer, Calendar and Maps. Return from external apps and confirm no automatic relaunch.
9. Repeat at normal and maximum text size, keyboard open/closed, and during a pending request. Check input controls stay on one row, enabled state is clear, and no unrelated chat behavior changed.

Device visual/accessibility and external-application checks remain pending user verification. Weather remains deferred to Stage 14B.
