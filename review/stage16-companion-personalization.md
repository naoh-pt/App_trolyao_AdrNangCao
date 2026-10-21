# Stage 16 — Companion conversation mode and personalization

Verdict: **READY FOR DEVICE TEST**

- Repository: `D:\nam5\semester_1\advance_android\01_trolyAI\troLyAo_ani_integration`
- Stage 15 source: `feature/stage15-personal-memory`, `7d02d121c3981d9d4f3627cb54b7e7dca7633f24`. Clean and equal to origin at start; no checkpointing of unfinished Stage 15 files was needed.
- Preserved checkpoint: `backup/stage15-memory-before-companion-20261021`, created/pushed at exactly `7d02d121c3981d9d4f3627cb54b7e7dca7633f24`.
- Stage 16: `feature/stage16-companion-personalization`, created from the published Stage 15 branch.
- Main remains `c547e1070bab84faef73cbff479b4db7588b8f62`; no merge or main push.

## Exact files

Modified:

```text
android/app/src/main/java/com/example/assistant/MainActivity.kt
android/app/src/main/java/com/example/assistant/data/local/SettingsStore.kt
android/app/src/main/java/com/example/assistant/data/remote/ChatApi.kt
android/app/src/main/java/com/example/assistant/data/repo/ChatRepository.kt
android/app/src/main/java/com/example/assistant/ui/chat/ChatScreen.kt
android/app/src/main/java/com/example/assistant/ui/chat/ChatViewModel.kt
android/app/src/main/java/com/example/assistant/ui/demo/DemoQuestionCatalog.kt
android/app/src/main/java/com/example/assistant/ui/memory/ConversationEntryCheckIn.kt
android/app/src/main/java/com/example/assistant/ui/settings/SettingsScreen.kt
android/app/src/test/java/com/example/assistant/ui/demo/DemoCatalogTest.kt
android/app/src/test/java/com/example/assistant/ui/demo/DemoScenarioControllerTest.kt
android/app/src/test/java/com/example/assistant/ui/memory/MemoryFeatureTest.kt
backend/README.md
backend/app/api/v1/conversations.py
backend/app/db/connection.py
backend/app/main.py
backend/app/services/memory_context.py
backend/tests/test_memory.py
```

Added:

```text
android/app/src/main/java/com/example/assistant/data/repo/CompanionGateway.kt
android/app/src/main/java/com/example/assistant/domain/CompanionPreferences.kt
android/app/src/main/java/com/example/assistant/ui/companion/CompanionChatCards.kt
android/app/src/main/java/com/example/assistant/ui/companion/CompanionConversation.kt
android/app/src/main/java/com/example/assistant/ui/companion/CompanionSettingsScreen.kt
android/app/src/main/java/com/example/assistant/ui/companion/CompanionViewModel.kt
android/app/src/test/java/com/example/assistant/ui/companion/CompanionFeatureTest.kt
backend/app/api/v1/companion.py
backend/app/services/companion_service.py
backend/tests/test_companion.py
review/stage16-companion-personalization.md
```

## Architecture and persistence

Existing ownership uses a validated X-Client-Id UUID, not a separate user/account table. The existing repository/Retrofit client obtains that same ID. Stage 15 already has a shared provider prompt composer and a navigation-entry-scoped check-in controller. Stage 16 extends those paths, adds a backend-backed Settings page following Memory Settings conventions, and adds ephemeral fields to the existing ChatUiState. No competing chat/account/navigation system was introduced.

An additive CREATE TABLE IF NOT EXISTS creates `companion_preferences`:

```text
client_id TEXT PRIMARY KEY
preferred_name TEXT NULL
address_style TEXT NOT NULL DEFAULT 'anna_ban'
humor_level TEXT NOT NULL DEFAULT 'medium'
response_length TEXT NOT NULL DEFAULT 'medium'
support_style TEXT NOT NULL DEFAULT 'balanced'
mood_check_in_enabled INTEGER NOT NULL DEFAULT 1 CHECK IN (0,1)
created_at TEXT NOT NULL
updated_at TEXT NOT NULL
```

No existing conversation, message or memory data is rewritten. API input is strictly typed and enum-validated. Parameterized upsert atomically replaces one owner's settings while retaining created_at. Repeated identical PUTs are safe. Existing-database upgrade/idempotent initialization are tested with temporary databases; the real developer database was not opened or migrated by this task. Restarting the backend normally applies the new table.

## Preferences and APIs

Both endpoints use the current X-Client-Id and project error envelope:

- `GET /api/v1/companion-preferences`: returns the complete typed settings object or safe defaults, with no write for a default GET.
- `PUT /api/v1/companion-preferences`: full validated replacement. Unknown fields/enums, invalid names, and non-boolean mood flags are rejected. Validation maps to the project's existing HTTP 400, not FastAPI's default 422. No AI/RAG/tool call occurs.

Options/defaults:

| Field | Options | Default |
|---|---|---|
| preferred_name | Optional trimmed NFC single-line nickname, up to 30 characters / four words | null |
| address_style | anna_ban (Anna – bạn), minh_ban (mình – bạn), chi_em (chị – em), em_anh (em – anh), em_chi (em – chị) | anna_ban |
| humor_level | low (Ít đùa), medium (Vừa phải), high (Tinh nghịch) | medium |
| response_length | short (Ngắn gọn), medium (Vừa phải), detailed (Chi tiết) | medium |
| support_style | balanced (Cân bằng), listen_first (Lắng nghe trước), advice_first (Ưu tiên lời khuyên), solve_together (Cùng tìm giải pháp) | balanced |
| mood_check_in_enabled | strict true/false | true |

Names reject control/format characters, newlines, markup, prompt-shaped imperative wording and paragraph-like input; letters/numbers and common name punctuation are allowed, including Hoàn and O'Reilly. SQL parameterization preserves quotes safely. Nicknames and preferences never overwrite personal memory. JSON preferences are bounded data, not system-authority instructions. Names are to be used naturally and sparingly, not every response. Gender is never inferred; address form is chosen explicitly by the user.

## Settings UI

Adds **Cá nhân hóa Anna** beside the existing Memory entry, with name field, four enum selectors, mood toggle and explicit **Lưu thay đổi**. Existing backend URL/FPS/font/TTS/voice/Memory controls remain intact. Values load from the backend through the current client ID. Loading/saving/success/error/retry states are explicit. Save is unavailable until an initial load succeeds; duplicate Save and edits during a save are blocked. A failed save retains the draft; retrying load also retains dirty edits. Back/gesture navigation asks before discarding unsaved changes and waits while saving.

Owner checks before/after requests reject stale results if identity changes; the old owner's values cannot be displayed/saved as the new owner. Labels and controls use existing Material themes, standard touch targets, Vietnamese accessibility semantics, scrollable adaptive layout and existing message-font size for nickname/selector values. No preference content is logged or copied into a new device preference database.

## Shared prompt hierarchy and companion policy

Both existing Gemini/Groq providers already invoke `provider_system_prompt`; no provider-specific personalization code or generation signature change is needed. Ordinary real-AI generation now scopes a validated preferences ContextVar alongside the existing memory ContextVar. Both reset in finally on success, fallback and exception. The shared composer has this order:

1. Safety/system rules and unchanged JSON/allowed-emotion contract.
2. Original stable Anna personality.
3. Companion conversation policy.
4. Bounded, validated preferences JSON and trusted enum-derived style guidance.
5. Explicit memory-confirmation rule and Stage 15 untrusted memory JSON.
6. Separate labeled RAG context.
7. Existing provider conversation history and current message.

Low humor avoids jokes unless requested; medium permits occasional gentle humor; high is playful only in suitable lighthearted context. Serious emotional disclosures always suppress humor, including high mode. No ridicule of distress, failure, appearance, identity, trauma or sensitive disclosures.

Short normally means 2–3 concise sentences; medium 4–6 where appropriate; detailed allows fuller explanations or steps without repetition. Safety content, citations, action instructions and essential clarifications must not be truncated to fit the length preference. Explicit selected address/length rules replace only Anna's defaults, not safety/personality/JSON requirements.

Balanced offers a choice; listen-first reflects/validates before advice; advice-first acknowledges and gives about 2–3 practical suggestions; solve-together clarifies and proposes one manageable step. An explicit current request safely overrides this default. The policy recognizes the three exact chip messages. Emotional responses acknowledge the specific feeling, avoid overwhelming solution lists, and ask at most one gentle follow-up.

Anna is explicitly an AI companion, not a human or replacement for friends/family/teachers/counselors/professionals. The policy forbids dependency, exclusive-understanding claims, shaming absence, diagnosis and manipulation using memories. Immediate danger/self-harm calls for calm support, a trusted nearby person and appropriate local emergency/professional help, with no diagnosis, jokes, web hotline lookup or internal-policy disclosure. Companion behavior does not replace professional help.

Weather, deterministic time/quick replies, actions, memory commands and memory check-ins retain their existing responses and bypass preference/provider injection. Quota fallback, provider selection, timeout handling, RAG retrieval and persistence/idempotency remain unchanged. Stage 15 prompt-order assertion now checks memory before RAG as required here; it still tests isolation, caps and separation.

## Mood check-in lifecycle

No backend mood/check-in record or automatic chat message is created by showing a card. The Stage 15 entry controller reports true (memory delivered), false (empty), or null (failed). Only an empty result can lead to a mood card. Preferences must then load successfully with mood enabled. A newly created conversation never requests this path; an existing conversation restored/selected into a genuine navigation entry does.

The existing SettingsStore atomically reserves one string marker `mood_shown_date_<client UUID>` for the device-local calendar date. Only that date marker is stored; no mood value/history/trend is stored separately. Reservation occurs immediately before presentation to suppress rapid switching/concurrent-entry duplication. Dismissal and selection retain that marker. Recomposition/rotation retain the current ChatViewModel/card; returning to another entry on the same date cannot produce a new daily card. A new local date may qualify on a later genuine entry; there is no midnight polling/timer. Identity changes use a separate key.

Memory reminders take priority: delivered or failed/unknown Stage 15 results suppress mood. Conversation identity, pending/sending state and whether the user has already begun a turn are checked before and after claiming the date. A late entry result cannot pop a card into an already-engaged conversation. Entry/controller scope and generation checks cancel/ignore stale results on switching. Network failure never blocks chat.

Card text: **Hôm nay bạn cảm thấy thế nào?** Options send these exact messages only on explicit tap:

```text
Rất vui      → Hôm nay mình cảm thấy rất vui.
Khá ổn       → Hôm nay mình cảm thấy khá ổn.
Bình thường  → Hôm nay mình cảm thấy bình thường.
Hơi buồn     → Hôm nay mình cảm thấy hơi buồn.
Căng thẳng   → Hôm nay mình đang cảm thấy căng thẳng.
```

The card is dismissible with **Để sau**, renders inside the existing scrolling message panel, and does not move/resize the character or change panel dimensions, keyboard/IME handling or input controls. Appearance does not request focus, send, read or animate. Selection uses the normal send/request-id/persistence/TTS/typewriter/animation flow, with a synchronous selection-busy/consumed guard. Existing typed drafts are restored immediately after starting that send and remain editable after it completes; no silent draft replacement or confirmation is needed because the original draft is preserved. Offline/sending/retry states reject taps.

## Support choices and catalog

A pure cue detector NFC-normalizes Vietnamese, case and whitespace, requires a self-reference plus a listed distress cue, and excludes common educational/meta/music/physics wording. It covers buồn, thất vọng, mất động lực, căng thẳng, áp lực, mệt mỏi, lo lắng, cô đơn, khó chịu and quá tải. Explicit Unicode letter/mark/number boundaries work on both Android ICU and desktop JVM; the unsupported Android UNICODE_CHARACTER_CLASS flag is not used. Local Android SDK source was consulted for that compatibility check, with no external request.

After a new matching assistant response (without an action), the latest response ID activates:

```text
Chỉ cần lắng nghe → Anna chỉ cần lắng nghe mình thôi nhé.
Cho mình lời khuyên → Anna cho mình một vài lời khuyên nhé.
Cùng tìm giải pháp → Anna cùng mình tìm cách giải quyết nhé.
```

Only the latest matching turn owns choices. A newer user turn clears them; selecting once hides/consumes them and disables double tap. Like mood choices, explicit taps send through the existing lifecycle and preserve the current draft. Before that tap, chips are only UI state and do not start TTS/animation or persist a psychological label. Existing chat DTOs remain unchanged.

The existing Cảm xúc category gains exact prompts `Hôm nay mình bị điểm thấp và cảm thấy thất vọng.` and `Anna ơi, lúc này mình chỉ muốn được lắng nghe thôi.` Both require backend/AI/Internet, not RAG. Catalog is 32 questions in seven categories. Demo đầy đủ appends the disappointment prompt as step 12, after the unchanged save-name/list-memory sequence. Quick demo (4) and no-quota demo (6) are unchanged. Picker selection is still draft-only.

## Verification and audit

Backend:

```powershell
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider tests/test_companion.py
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider tests
.\.venv\Scripts\python.exe -m compileall -q app tests
```

- Focused: **42 passed, 0 failed/errors/skipped**.
- Full: **921 passed, 0 failed/errors/skipped** (all 879 Stage 15 tests retained).
- Compileall: success, exit 0. Existing FastAPI/Starlette HTTPX TestClient deprecation warning only.
- Includes defaults/upsert/persistence/owner isolation, special-character parameters, invalid fields/enums/names/booleans, upgrade preservation, every style, hierarchy/data bounds, safety/support rules, Gemini/Groq parity, context reset/fallback and route bypasses.

Android:

```powershell
$env:JAVA_HOME = "C:\Program Files\Android\Android Studio\jbr"
$env:ANDROID_HOME = "$env:LOCALAPPDATA\Android\Sdk"
.\gradlew.bat testDebugUnitTest
.\gradlew.bat assembleDebug
```

- Final XML: **257 tests, 257 passed, 0 failed, 0 errors, 0 skipped**, across 18 suites.
- Includes 21 new companion tests and all 236 Stage 15 regressions, with additive catalog expectations updated.
- Settings state/save/error/duplicate prevention/name/enums/owner changes; daily date/identity/restoration/eligibility; five mood mappings; Stage 15 outcome priority; Unicode cues/negative cases; chip mappings/consumption/draft retention; and catalog draft-only behavior are covered.
- `assembleDebug`: **BUILD SUCCESSFUL**.
- Local APK: `D:\nam5\semester_1\advance_android\01_trolyAI\troLyAo_ani_integration\android\app\build\outputs\apk\debug\app-debug.apk`; exists, ignored/untracked, not installed or committed.
- `git diff --check`: passed; exact staged diff reviewed before commit.

No real `.env`, user database, nickname/preference or personal-memory contents were read/edited. Only supplied demo names/prompts and fake test data appear in source/tests/docs. No API key, dependency, signing/backend URL/local configuration change, character asset modification, database artifact or APK/ZIP/build output is staged. No WorkManager, AlarmManager, FCM, background/foreground service, polling, notification/GPS permission or system notification was added. Existing memory parsing was not changed; polite-suffix Stage 15.1 remains deferred. No live Gemini/Groq/RAG/embedding/Weather or other external API request occurred; only authorized Git remote operations used the network. Main was untouched.

Full pre-commit `git status --short` (untracked directories contain only the exact files above):

```text
 M android/app/src/main/java/com/example/assistant/MainActivity.kt
 M android/app/src/main/java/com/example/assistant/data/local/SettingsStore.kt
 M android/app/src/main/java/com/example/assistant/data/remote/ChatApi.kt
 M android/app/src/main/java/com/example/assistant/data/repo/ChatRepository.kt
 M android/app/src/main/java/com/example/assistant/ui/chat/ChatScreen.kt
 M android/app/src/main/java/com/example/assistant/ui/chat/ChatViewModel.kt
 M android/app/src/main/java/com/example/assistant/ui/demo/DemoQuestionCatalog.kt
 M android/app/src/main/java/com/example/assistant/ui/memory/ConversationEntryCheckIn.kt
 M android/app/src/main/java/com/example/assistant/ui/settings/SettingsScreen.kt
 M android/app/src/test/java/com/example/assistant/ui/demo/DemoCatalogTest.kt
 M android/app/src/test/java/com/example/assistant/ui/demo/DemoScenarioControllerTest.kt
 M android/app/src/test/java/com/example/assistant/ui/memory/MemoryFeatureTest.kt
 M backend/README.md
 M backend/app/api/v1/conversations.py
 M backend/app/db/connection.py
 M backend/app/main.py
 M backend/app/services/memory_context.py
 M backend/tests/test_memory.py
?? android/app/src/main/java/com/example/assistant/data/repo/CompanionGateway.kt
?? android/app/src/main/java/com/example/assistant/domain/CompanionPreferences.kt
?? android/app/src/main/java/com/example/assistant/ui/companion/
?? android/app/src/test/java/com/example/assistant/ui/companion/
?? backend/app/api/v1/companion.py
?? backend/app/services/companion_service.py
?? backend/tests/test_companion.py
?? review/stage16-companion-personalization.md
```

Final post-commit/push status must be empty and is verified in the delivery response.

## Physical-device checklist

1. Restart the backend normally for the additive table. Open Settings → Cá nhân hóa Anna; configure preferred name **Hoàn**, Save, leave/reopen and verify persistence. Test Back confirmation with unsaved edits and a failed save without losing edits.
2. Test relevant address styles (Anna–bạn, mình–bạn, chị–em, em–anh, em–chị) with ordinary AI chat. Verify no gender inference and occasional rather than constant nickname usage.
3. Compare low/high humor with a lighthearted prompt; check that low avoids unsolicited jokes.
4. Compare short/detailed response length with the same normal explanatory question.
5. Test all four support defaults and explicit current requests overriding them.
6. With mood enabled and no due memory reminder, enter an existing conversation on an eligible device-local date; verify one compact mood card. New chats must not show it immediately.
7. Rotate, open Settings/return, dismiss/re-enter another conversation; verify no new daily card. Confirm preference-off suppresses it and backend-off does not block opening chat.
8. Test all five mood options across controlled disposable test profiles/dates, verifying exact mapped normal messages and one send per tap. Preserve real app data/client identity; do not clear real data just to force daily resets. Unit tests exercise all mappings without resets.
9. Send `Hôm nay mình bị điểm thấp và cảm thấy thất vọng.`
10. Verify the three support choices appear only for the latest matching reply; educational questions such as `Giải thích áp lực khí quyển cho mình` should not show them.
11. Tap **Chỉ cần lắng nghe** twice quickly; verify exactly one explicit message, no unsolicited long checklist, and preservation of any existing typed draft.
12. Repeat with **Cho mình lời khuyên** and **Cùng tìm giải pháp** after fresh emotional turns; verify approximately 2–3 practical suggestions or one interactive first step as appropriate.
13. With high humor selected, use a serious but non-emergency emotional disclosure and verify a calm, non-playful response. Safety/prompt wording requires real provider verification; no live provider call was made by the agent.
14. Save a Stage 15 event with `Nhắc mình khi mở ứng dụng từ hôm nay`, leave/re-enter and verify the memory reminder takes priority and no mood card appears in that entry. Verify memory check-in remains one-time.
15. Smoke-test memory/Memory Settings, Weather, RAG, timer, Calendar, Maps, normal chat, TTS/stop/replay, typewriter/skip, microphone, animations, FPS/font Settings and Demo Question menu. Full demo adds only the final companion step; picker selections never auto-send.
16. Close the app; verify no background notification or ongoing service. Test normal/max font sizes and keyboard open/closed without moving/resizing the character or input panel.

## Known limitations

- No background notification or always-running service. Mood is considered only on genuine existing-conversation entry, not periodic checks or a midnight refresh.
- Mood shown-date state is device-local and client-scoped; no mood history/trend is built. Explicit selected mood sentences remain ordinary chat history as requested.
- The date marker is reserved before rendering to prevent duplicate rapid entries; cancellation, a user turn or process death at that instant can consume a day without a visible card. No retry loop is added.
- Support detection is conservative rule-based and can miss context or suppress legitimate wording. It is not a classifier API, diagnosis or psychological label.
- Preferences guide AI; exact wording still depends on the provider. External provider personalization and emotional-response quality require a real AI request during user device testing.
- Companion behavior does not replace professional help. Prompt rules improve boundaries but do not constitute an absolute guarantee of model behavior.
- Existing UUID ownership is reused; no new authentication/account system is introduced. Name validation is intentionally restrictive and preferences do not rewrite explicit personal memory.
