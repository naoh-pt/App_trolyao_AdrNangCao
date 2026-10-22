# Stage 15 — Explicit personal memory and conversation-entry check-ins

Verdict: **READY FOR DEVICE TEST**

- Repository: `D:\nam5\semester_1\advance_android\01_trolyAI\troLyAo_ani_integration`
- Verified base: `c547e1070bab84faef73cbff479b4db7588b8f62`, local main and origin/main matched with clean tree/index.
- Backup: `backup/pre-stage15-20261021`, created and pushed at exactly `c547e1070bab84faef73cbff479b4db7588b8f62`.
- Feature: `feature/stage15-personal-memory`; no merge or push to main.

## Exact changed and added files

Modified:

```text
android/app/src/main/java/com/example/assistant/MainActivity.kt
android/app/src/main/java/com/example/assistant/data/remote/ChatApi.kt
android/app/src/main/java/com/example/assistant/data/remote/Dtos.kt
android/app/src/main/java/com/example/assistant/data/repo/ChatRepository.kt
android/app/src/main/java/com/example/assistant/ui/chat/ChatViewModel.kt
android/app/src/main/java/com/example/assistant/ui/demo/DemoQuestionCatalog.kt
android/app/src/main/java/com/example/assistant/ui/settings/SettingsScreen.kt
android/app/src/test/java/com/example/assistant/ui/demo/DemoCatalogTest.kt
android/app/src/test/java/com/example/assistant/ui/demo/DemoScenarioControllerTest.kt
backend/README.md
backend/app/api/v1/conversations.py
backend/app/db/connection.py
backend/app/main.py
backend/app/services/providers/gemini_provider.py
backend/app/services/providers/groq_provider.py
```

Added:

```text
android/app/src/main/java/com/example/assistant/data/repo/MemoryGateway.kt
android/app/src/main/java/com/example/assistant/ui/memory/ConversationEntryCheckIn.kt
android/app/src/main/java/com/example/assistant/ui/memory/MemoryScreen.kt
android/app/src/main/java/com/example/assistant/ui/memory/MemoryViewModel.kt
android/app/src/test/java/com/example/assistant/ui/memory/MemoryFeatureTest.kt
backend/app/api/v1/memories.py
backend/app/services/memory_context.py
backend/app/services/memory_service.py
backend/tests/test_memory.py
review/stage15-personal-memory-checkins.md
```

## Existing architecture and migration

Backend ownership is the existing validated `X-Client-Id` UUID; there is no user/account table. Conversations, messages and request-id records already use SQLite transactions and a process-local request lock. The new table follows this ownership model using `client_id`, rather than inventing a separate user identifier. Android already obtains the same ID from SettingsStore and scopes ChatViewModel to a navigation entry. Room is a history cache, not the source of personal memory truth.

`init_db()` adds `personal_memories` using CREATE TABLE IF NOT EXISTS:

```text
id TEXT PRIMARY KEY
client_id TEXT NOT NULL
kind TEXT NOT NULL CHECK(profile/preference/general/event)
content TEXT NOT NULL CHECK(length BETWEEN 1 AND 300)
normalized_content TEXT NOT NULL
event_date TEXT NULL
remind_on TEXT NULL
reminded_at TEXT NULL
expires_at TEXT NULL
created_at TEXT NOT NULL
updated_at TEXT NOT NULL
UNIQUE(client_id, normalized_content)
```

Owner/order and owner/due-reminder indexes are added with CREATE INDEX IF NOT EXISTS. UUIDs and UTC ISO timestamps follow existing conventions; event/remind dates are Vietnam-local ISO dates. No existing table, conversation or message is migrated destructively; no Android Room migration is needed. Repeated initialization and upgrade from a database without the memory table preserve existing data in tests. **Only temporary databases were upgraded during verification; the real database was not opened for migration by this task.** Normal backend startup applies the additive schema to the developer database.

## Explicit policy, commands and sensitive data

Only anchored commands with `hãy nhớ:` / `hãy nhớ rằng` save memory. Optional Anna prefix is supported. Ordinary personal statements, ordinary conversational “nhớ”, computer-memory questions and educational text do not save or get intercepted.

Supported examples:

```text
Anna hãy nhớ: mình tên là Hoàn.
Anna hãy nhớ: mình thích học Android.
Hãy nhớ rằng mình đang học năm cuối.
Anna hãy nhớ: mình thi Android vào thứ Sáu tuần sau.
Anna nhớ gì về mình?
Bạn đang nhớ gì về mình?
Anna hãy quên việc mình thích học Android.
Hãy quên thông tin mình tên là Hoàn.
Anna hãy nhớ: mình thi Android vào thứ Sáu tuần sau. Nhắc mình khi mở ứng dụng từ hôm nay.
Anna hãy nhớ: mình thi Android vào thứ Sáu tuần sau. Nhắc mình khi mở ứng dụng từ ngày mai.
```

Text is NFC-normalized, whitespace-trimmed/collapsed, conversational terminal punctuation cleaned, and the initial self-reference normalized to “bạn”. Case-folded normalized content prevents duplicates per owner. Maximum 300 characters per item and 30 active memories per owner. Profile/preference memories remain until explicitly deleted. Names such as Mai and preferences mentioning Mai do not become relative-date events.

Likely passwords, OTPs (including OTP immediately followed by digits), API/private keys, access tokens/JWT-shaped strings and full payment-card-shaped numbers are rejected with a friendly local response. This is deterministic pattern filtering, **not perfect secret detection**. No actual user memories/secrets were read or committed; documentation and tests use the supplied demo prompts and fake fixtures. Normal user/assistant chat messages still persist as required, including rejected attempts, so users must not enter real secrets in chat.

Listing uses only active owned records in deterministic order. Forget chooses an exact normalized match first, otherwise one unique substring match. Zero/multiple matches ask for more specific wording or Memory Settings; never delete several records. Memory deletion never removes conversation history. Archived records can also be explicitly forgotten/deleted.

## Date parsing and one-time rules

Memory reuses the unchanged Calendar date matcher/resolver with an injectable aware clock and Vietnam UTC+07:00. No LLM or new competing date interpretation is used. Supported dates include hôm nay, ngày mai/mai, ngày kia, explicit weekday this/next week, and other unambiguous expressions already supported by Calendar. Tests freeze `2026-10-21 11:00 +07:00`, including rollover. Bare weekdays, ambiguous weekends, malformed dates, past dates and reminder dates after the event ask for clarification without saving an incomplete event.

The combined reminder clause uses the explicit form `. Nhắc mình khi mở ứng dụng từ <supported date>`. A description, valid event date and valid reminder-start date are required. `remind_on` is a date, never an alarm time. Eligibility is local today >= remind_on, unreminded and unexpired. Events expire at Vietnam midnight following their event date; they remain archived in the table and Settings instead of being silently deleted.

An existing record is never re-armed or rescheduled by a duplicate save. An expired duplicate asks the user to delete its old record explicitly before saving a new event. `reminded_at` is never cleared automatically, so each stored memory can deliver at most one check-in. Repeated reminders are outside this stage.

## APIs, routing and transaction behavior

New routes use the existing `X-Client-Id` dependency and normal error mapping:

- `GET /api/v1/memories`: typed `{items: [...]}` for owned active **and archived** records; includes `active`, type, content, event/remind dates and delivery status, excludes internal normalized text/client ID. Ordering is created_at then ID.
- `DELETE /api/v1/memories/{id}`: HTTP 204 for an owned record; another owner gets safe HTTP 404. No bulk endpoint: Android deletes a confirmed snapshot of individual owned IDs, including archived items.
- `POST /api/v1/conversations/{id}/check-in`: HTTP 200 `{message: null}` if none is due, or a typed normal MessageResponse. It does not create conversations.

Memory commands run after normal validation/ownership/request-id replay lookup and before action/quick-reply/Weather/history/RAG/AI processing. Actions retain their existing order for all non-memory commands. Memory mutation, user/assistant messages and idempotency record share the existing atomic transaction. Rollback tests prove a chat persistence failure cannot leave an orphan memory. Replay returns the original response before any memory mutation. Memory commands are excluded from action reconstruction on replay, preventing text like “sau 5 phút” inside a stored fact from inventing a timer action.

Check-in uses BEGIN IMMEDIATE, validates conversation ownership, selects at most one due owned record, writes one deterministic assistant message, updates reminded_at/updated_at and conversation updated_at, then commits. Concurrent requests serialize and cannot deliver the same record twice. A failure rolls back message and reminder claim together. Entering another conversation cannot redeliver a claimed memory. Event date is rendered explicitly in check-in text to avoid a stale “tuần sau” phrase changing meaning. No external tool/provider call exists in this endpoint.

## Android entry trigger, display and Settings

ChatViewModel performs one optional check-in for its **initial existing conversation**, after initial history loading. A new navigation entry/cold recreation is a genuine entry; ordinary Compose recomposition and rotation retain the same ViewModel/controller and cannot retrigger it. Manual refresh does not call check-in. New chats do not request check-in or create a conversation for a check-in. The existing app still starts on Home; selecting an existing history conversation qualifies as entry. No synthetic app-wide selected-conversation state was added.

The entry controller is viewModelScope-owned, cancels on replacement/leave, checks captured conversation ID and generation, and deduplicates returned message IDs. Disposed ViewModels cancel their jobs. Empty/network-failed check-ins do not affect the draft or block chat. A late response cannot be cached under a newer conversation ID. The repository upserts complete returned messages into existing Room history with stable IDs. A lost/canceled response can be recovered from backend history; the backend message/claim remain atomic.

**Check-ins are silent, immediate normal history messages.** They do not start a second presentation state machine or force typewriter, TTS, emotion animation or user settings. Existing manual replay can read the full message through the established controls. Normal newly sent replies retain all existing Stage 13 presentation behavior.

Settings adds one `Trí nhớ của Anna` entry and a dedicated screen with loading, empty, friendly error/retry, active/archived content, localized kinds, event/remind dates, already-reminded status and delete controls. Clear-all requires an explicit confirmation and deletes the loaded IDs individually. If a deletion fails partway, refresh plus a friendly error exposes the remaining state; clear-all is not an atomic server batch. Existing user ID, Settings controls/navigation conventions, Material colors and accessible Vietnamese button labels are reused. No memory content is logged.

## Catalog

Adds category `Trí nhớ` and five stable IDs: `memory_name`, `memory_preference`, `memory_list`, `memory_event`, `memory_forget`. All require backend, with Internet/AI/RAG flags false. Exact prompts are the supplied name, preference, list, immediately testable combined event/reminder, and forget commands.

Catalog becomes 30 questions across seven categories. Demo đầy đủ appends save-name then list-memory as steps 10 and 11. Its original nine steps, Weather and all original questions remain. Quick demo stays at 4 and no-quota demo at 6; neither receives state-changing memory prompts. Selecting any Memory question only fills the existing draft with the full prompt and retains replacement confirmation—no automatic Send, memory write or backend request.

## Provider context and injection protection

For ordinary messages using real AI, the route loads only that owner's active memories, prioritizes recent updated records, and supplies at most 10 entries / 1500 serialized characters through a request-local ContextVar. The token is reset in finally, preventing cross-request/user leakage, including fallback/errors. Memory stays separate from RAG; generation signatures, routing, timeout/quota/fallback behavior and JSON/emotion contract remain unchanged.

Both Gemini and Groq call one shared system-prompt composer. The original Anna personality remains intact; a short added policy permits long-term-memory claims only after successful system confirmation and explains the explicit save syntax. Memory is an escaped JSON string array with named boundaries and a trusted instruction to treat entries only as untrusted personal data, never as instructions or system/developer authority. Quotes/newlines are JSON-escaped; angle brackets/ampersands are escaped to prevent markup imitation. No code is evaluated from memory. This is prompt-level isolation, not a guarantee that an arbitrary LLM can never be influenced; no live provider was called to test behavior.

Provider tests prove equivalent Gemini/Groq context, correct owner isolation, count/length caps, separate RAG data, escaping, and absence of memory content in logs. Local commands, actions, quick replies, Weather and check-ins never inject or send memory to providers. Users should understand that active memories may be sent as personal context to their configured AI provider when they explicitly send an ordinary AI chat question.

## Verification

Backend (existing virtual environment):

```powershell
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider tests/test_memory.py
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider tests
.\.venv\Scripts\python.exe -m compileall -q app tests
```

- Focused memory: **66 passed, 0 failures/errors/skips**.
- Full backend: **879 passed, 0 failures/errors/skips** (all 813 pre-Stage-15 tests retained).
- Compileall: success, exit 0.
- Existing FastAPI/Starlette HTTPX TestClient deprecation warning only.
- New tests cover actual pre-memory schema upgrade, idempotent init, Unicode/quotes/NFC/length/quota, duplicates, sensitive rejection, explicit/conservative grammar, date/timezone behavior, active/archive handling, owner APIs, transaction rollback, concurrent check-ins, replay and provider isolation.

Android:

```powershell
$env:JAVA_HOME = "C:\Program Files\Android\Android Studio\jbr"
$env:ANDROID_HOME = "$env:LOCALAPPDATA\Android\Sdk"
.\gradlew.bat testDebugUnitTest
.\gradlew.bat assembleDebug
```

- XML: **236 tests, 236 passed, 0 failures, 0 errors, 0 skipped**, across 17 suites.
- Includes 17 new MemoryFeatureTest cases plus all 219 existing tests, with catalog expectations updated for the additive category/scenario steps.
- Covers DTOs, Settings load/list/empty/error/retry/delete/confirmed clear, entry-once/no-entry/empty/failure/cancellation/stale IDs/dedup, silent history-only behavior and exact Memory prompts/draft-only selection.
- `assembleDebug`: **BUILD SUCCESSFUL**.
- APK: `D:\nam5\semester_1\advance_android\01_trolyAI\troLyAo_ani_integration\android\app\build\outputs\apk\debug\app-debug.apk`; exists locally, ignored/untracked, not installed or committed.
- `git diff --check`: passed. Exact staged paths/diff reviewed before commit.

No real `.env`, secrets, user database contents or local configuration were inspected/edited. No tracked APK/ZIP/database/.env/local.properties artifacts; no generated file staged. No Gradle/dependency, manifest, Android background service, WorkManager, AlarmManager, FCM, polling or notification/GPS permission was added. No Weather/RAG/action/date-parser/personality source, assets, FPS/font settings, network URL, TTS/STT/typewriter/animation implementation was changed. Additions reuse existing chat/navigation/API plumbing. All automated external integrations used existing fakes/sentinels; **no live Gemini, Groq, RAG, embedding, Weather or other external API calls occurred**. Main remains at the base SHA.

Full pre-commit `git status --short` (new directories contain only the exact files listed above):

```text
 M android/app/src/main/java/com/example/assistant/MainActivity.kt
 M android/app/src/main/java/com/example/assistant/data/remote/ChatApi.kt
 M android/app/src/main/java/com/example/assistant/data/remote/Dtos.kt
 M android/app/src/main/java/com/example/assistant/data/repo/ChatRepository.kt
 M android/app/src/main/java/com/example/assistant/ui/chat/ChatViewModel.kt
 M android/app/src/main/java/com/example/assistant/ui/demo/DemoQuestionCatalog.kt
 M android/app/src/main/java/com/example/assistant/ui/settings/SettingsScreen.kt
 M android/app/src/test/java/com/example/assistant/ui/demo/DemoCatalogTest.kt
 M android/app/src/test/java/com/example/assistant/ui/demo/DemoScenarioControllerTest.kt
 M backend/README.md
 M backend/app/api/v1/conversations.py
 M backend/app/db/connection.py
 M backend/app/main.py
 M backend/app/services/providers/gemini_provider.py
 M backend/app/services/providers/groq_provider.py
?? android/app/src/main/java/com/example/assistant/data/repo/MemoryGateway.kt
?? android/app/src/main/java/com/example/assistant/ui/memory/
?? android/app/src/test/java/com/example/assistant/ui/memory/
?? backend/app/api/v1/memories.py
?? backend/app/services/memory_context.py
?? backend/app/services/memory_service.py
?? backend/tests/test_memory.py
?? review/stage15-personal-memory-checkins.md
```

Final post-commit/push `git status --short` must be empty and is checked in the delivery response.

## Physical-device checklist

1. Restart the existing backend normally to apply the additive schema; keep the existing client ID. Send `Anna hãy nhớ: mình tên là Hoàn.` and verify deterministic confirmation.
2. Send `Anna hãy nhớ: mình thích học Android.` and verify preference confirmation.
3. Send `Anna nhớ gì về mình?` and `Bạn đang nhớ gì về mình?`; verify the two records. Repeat a save and verify no duplicate.
4. Send an ordinary AI question, e.g. `Bạn có thể gọi mình bằng tên đã lưu và gợi ý cách học tối nay không?`; verify appropriate personal context without a false new-save claim. This user device step may use the configured provider; no live provider was called by the agent.
5. Restart the app and backend; verify saved information persists through list/Settings.
6. Open Settings → `Trí nhớ của Anna`; check loading/empty/list/type/date/status, Vietnamese text, large fonts and retry with backend unavailable.
7. Delete one memory; verify refresh and unchanged chat history. Test clear-all Cancel, then confirm only when ready to remove remaining demo memories.
8. If a second test client is available, verify it cannot list/delete the first client's memories or check in to its conversation.
9. Send `Anna hãy nhớ: mình thi Android vào thứ Sáu tuần sau. Nhắc mình khi mở ứng dụng từ hôm nay.` Verify it is an event with correct Vietnam dates and no Calendar/action/notification launch.
10. Leave the conversation and select it again from History.
11. Verify exactly one persisted check-in appears immediately as a normal history message, without forced speech/reveal/animation.
12. Leave/re-enter, rotate, refresh history, and enter a different conversation; verify no redelivery of that memory. If the response was lost while switching quickly, the persisted check-in remains recoverable in the original conversation's history.
13. Send `Mình đang học Android.` and verify the memory list does not grow and Anna does not falsely claim long-term storage.
14. Use **fake data only**: send `Anna hãy nhớ: mã OTP là 123456.` or a fake password-labelled statement; verify rejection and no personal-memory record. Do not enter a real secret; chat history still persists normally.
15. Smoke-test Weather, timer, Calendar, Maps, RAG, normal AI chat, TTS/stop/replay, typewriter/skip, microphone, animations, FPS/font Settings and the Demo Question menu. Verify Memory selections only fill the draft and full demo appends only name-save/list steps.

## Known limitations

- Memory saving is explicit; ordinary statements are never silently stored.
- Reminders occur only on a genuine existing-conversation entry, not repeated foreground/lifecycle callbacks, refresh, recomposition or rotation.
- Reminders are one-time per stored memory. The app cannot remind while closed; no background infrastructure exists.
- Repeated/system-level reminders require existing Calendar/timer or a future stage.
- Natural-language parsing is intentionally limited. Reminder clauses require supported explicit date wording; ambiguous input is clarified.
- Expired records remain manageable/archived and are excluded from context/check-ins; duplicate saves do not re-arm them. Creating a new same-content event requires explicit deletion and a new save.
- Client UUID ownership follows the existing project convention and is not a new authentication system. Sensitive-data detection is heuristic; memories are not encrypted at rest by this stage.
- Clear-all deletes a confirmed snapshot one ID at a time, not an atomic batch; concurrent newly saved records are not silently included.
- Check-in failures are nonblocking and do not retry/poll during the same entry. A server-committed response lost to cancellation is recovered through history.
- LLM context is bounded/escaped/untrusted, but prompt-level protection is not an absolute model-security guarantee. Phone UI, actual provider personalization and Android service behavior still require device verification.
