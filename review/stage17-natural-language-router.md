# Stage 17 — Natural-language routing and manual mood check-in

Verdict: **READY FOR DEVICE TEST WITH DISCLOSED LOCAL-DATA INCIDENT**.

## Source and preservation

- Repository: `D:\nam5\semester_1\advance_android\01_trolyAI\troLyAo_ani_integration`.
- Published Stage 16 source: `feature/stage16-companion-personalization` at `bdf833f7f878ea93a95c03c852c410d1f07421c6`; local/remote matched after fetch; initial tree/index clean. Stage 16 report and Stage 15/16 implementations inspected.
- Backup: `backup/stage16-before-stage17-20261021`, created and pushed at that exact SHA; remote SHA confirmed with `git ls-remote`.
- Working branch: `feature/stage17-natural-language-router`, created from that SHA, not main.
- Local and remote main remain `c547e1070bab84faef73cbff479b4db7588b8f62`.
- Release preparation resumed with explicit user acceptance of the disclosed local-data incident. The Stage 17 source commit and feature-only push are verified in the delivery response. No branch deleted or history rewritten.

## Disclosed local-data incident and accepted audit outcome

An existing test-isolation defect was discovered during focused regression testing. Two legacy route tests in `tests/test_assistant_action_service.py` use a module-level `TestClient` without requesting the `client`/temporary-database fixture. Before the harness correction, these tests reached the configured local SQLite database. Conversation creation returned HTTP 200 (therefore test conversation rows were committed); sending the action then returned HTTP 500. The agent must **not claim the real database was untouched**.

One reproducing development command, from backend:

```powershell
.\.venv\Scripts\python.exe -m pytest -q -x -p no:cacheprovider tests/test_stage17_router.py tests/test_assistant_action_service.py --tb=short
```

Result before isolation correction: 100 passed, 1 failed; `test_route_timer_returns_action_and_persists` received HTTP 500 instead of 200. Inspection showed that this client bypassed the fixture and startup initialization for the new tables. The preceding focused batch also exercised the legacy map route test. File metadata confirmed recent writes to ignored `backend/tro_ly_ao.db`. No test-record deletion or destructive repair was attempted.

Correction: make the existing temporary-database fixture automatic for every test, including module-level clients. Add an automatic network guard against accidental external socket connections. All subsequent verification uses temporary databases. No existing test assertion was weakened or removed.

The user stopped the backend and backed up `backend/tro_ly_ao.db` outside the repository. A subsequently authorized, strictly read-only audit used SQLite `mode=ro&immutable=1` with `query_only=ON`; no WAL existed and the database hash was unchanged during the audit. Queries were limited to exact test markers and related ownership/count metadata; unrelated personal message content was not inspected.

The incident window contained two empty `Test Actions` conversations at `2026-10-21T17:11:07.910046Z` and `2026-10-21T17:11:36.595405Z`, plus one empty default-title Maps candidate at `2026-10-21T17:11:08.282065Z`. For all three, created_at equalled updated_at; each distinct owner had only that conversation, zero messages, zero request records, zero memories and zero preferences. The source tests generate random UUIDs, so the generic empty Maps candidate's test ownership and separation from the Android device client ID could not be proven. Targeted inspection found no destructive effect; without a pre-incident baseline it does not prove that every unrelated record was unchanged.

The user explicitly reviewed and accepted these three harmless empty rows and the ownership ambiguity, authorized release preparation to continue, and required that all rows remain in place. No database record was deleted, edited, migrated, restored, vacuumed, cleaned or reset during the audit or release resumption. The audit does **not** change the fact that the earlier test run touched the local database. Keep the external backup and both test-isolation safeguards. Device verification remains outstanding; this acceptance authorizes the feature commit/push, not integration into main.

## Exact changed and added files

Modified:

1. `android/app/src/main/java/com/example/assistant/ui/chat/ChatScreen.kt`
2. `android/app/src/main/java/com/example/assistant/ui/chat/ChatViewModel.kt`
3. `android/app/src/main/java/com/example/assistant/ui/companion/CompanionConversation.kt`
4. `backend/app/api/v1/conversations.py`
5. `backend/app/db/connection.py`
6. `backend/app/services/memory_context.py`
7. `backend/app/services/providers/gemini_provider.py`
8. `backend/app/services/providers/groq_provider.py`
9. `backend/tests/conftest.py`

Added:

10. `android/app/src/test/java/com/example/assistant/ui/companion/ManualMoodTest.kt`
11. `backend/app/services/intent_normalization.py`
12. `backend/app/services/intent_proposal.py`
13. `backend/app/services/pending_calendar.py`
14. `backend/tests/test_stage17_router.py`
15. `review/stage17-natural-language-router.md`

## Routing and normalization

Ownership, message/request validation and idempotency replay still precede processing. A process-local conversation lock serializes turns as well as the existing request lock. Pending Calendar cancellation/continuation is checked first. Existing anchored quick-reply, explicit-memory and action/weather grammars remain deterministic and bypass generation. Their non-overlapping matchers retain the existing action bypass without a quick-reply lookup for matched actions, preserving prior regression contracts. Quick replies first try the original stripped message (including existing punctuation behavior), then normalized surface form if necessary. Original text is still used for history, RAG/provider input and request-id equality.

The shared pure adapter accepts at most 2,000 input characters, NFC-normalizes, collapses whitespace, trims terminal punctuation, and removes bounded wake/polite wrappers. Comparisons use case-insensitive patterns; extracted text retains case and accents. It recognizes Anna/Anna ơi/Này Anna, làm ơn, nhé/nha/với/giúp mình/giúp tôi/được không/cho mình and terminal vậy. Explicit “nhớ giúp mình là” becomes the existing explicit-save grammar; it never infers memory from ordinary statements. Wake handling preserves grammatical Anna subjects such as “Anna là ai”. A greeting followed by a real query is unwrapped rather than answered as only a greeting.

Covered variants include local time, polite explicit memory/event reminders, Maps search/directions, Calendar creation, relative timers and tomorrow rain queries. Existing service parsers and date interpretation are reused rather than replaced. Educational examples concerning mind maps, history, scientific weather, mechanical clocks, atmospheric pressure and quoted dates do not become actions. Standalone “Ngày mai” only completes Calendar when compatible pending state exists; otherwise it follows ordinary chat.

## Same-call AI proposal

Both Gemini and Groq optionally parse `intent_proposal` from their existing generated JSON response. `GeneratedReply` remains a two-element tuple for existing callers and fakes, with internal validated metadata. Provider orchestration/fallback and timeout budgets are unchanged. There is no classifier endpoint, classifier provider call, or second successful generation request. Ordinary chat uses its existing one generation path; deterministic commands use none.

Strict shape: exactly `intent`, `confidence`, `slots`. Intent allowlist: `normal_chat`, `set_timer`, `create_calendar_event`, `map_search`, `weather_query`, `local_time_query`. Confidence must be a finite non-Boolean number from 0.80 through 1. Each intent has its own slot-key allowlist. Values must be nonblank strings of at most 200 characters, without nested data/control characters, URI schemes, package identifiers, code delimiters or obvious executable/SQL commands. Invalid proposals are ignored and retain the normal reply. Acceptance is additionally gated by feature-like original wording and educational-question guards.

All accepted fields are converted to a fixed command template and reparsed through trusted existing services. Calendar proposals require all three fields and server date/time validation. Timer duration uses bounded numeric units. Weather date expressions are allowlisted; Maps uses the existing safe place parser. Memory inference and executable payloads are excluded. Public Android DTOs/response fields remain unchanged; Calendar/Maps/timer still return confirmation actions and never launch an activity from the server.

## Pending Calendar schema and lifecycle

Additive `CREATE TABLE IF NOT EXISTS pending_actions` stores owner/conversation primary key, fixed Calendar intent, bounded slot JSON, missing-slot JSON, UTC created/updated/expiry timestamps and conversation FK cascade. Slots are only original-case `title`, `date_text`, `time_text`, each at most 200 characters. Idle TTL is ten minutes after a compatible slot update; unrelated messages do not extend it. No background expiry task runs.

Explicit Calendar commands alone create pending state. The existing Calendar date/time grammar extracts fields and validates date/time expressions; incomplete fields produce deterministic missing-only questions without action DTOs. Date-only/time-only follow-ups merge safely; a missing title accepts a conservative short event phrase beginning học/họp/ôn/làm/đi/thi/gặp. Combined answers can complete multiple slots. Dates use the existing Vietnam UTC+07:00 parser, including weekdays and explicit dates; default event duration remains 30 minutes and past times remain invalid.

Complete new Calendar or other validated action replaces pending state. Cancellation phrases Thôi/Bỏ qua/Hủy/Hủy tạo lịch/Không cần nữa clear existing state and return the requested cancellation sentence. Without state they do not claim cancellation. Expired state is ignored and removed on the next successful turn. Completion consumes state only with message/idempotency commit. Invalid or unrelated continuation preserves the old slots and asks for the missing information; no AI/provider request is made while asking this clarification. The user can cancel or issue a complete new action.

Planning does not mutate SQLite. Under `BEGIN IMMEDIATE`, the route re-reads Calendar state before applying changes and persists both messages, pending mutation, replay linkage and action snapshot atomically. Transaction failure rolls all of them back. Process-local serialization plus the SQLite recheck prevents stale completion across requests/workers.

The second additive table, `message_action_snapshots`, links each new assistant message to validated action JSON or explicit null. This is necessary because standalone follow-ups cannot reconstruct the completed action on replay. Retries return the same action without consuming pending state again or regenerating tool results. Legacy responses without snapshots retain their original deterministic reconstruction behavior. Existing conversation/message/memory data is not rewritten by the migration code. Upgrade/idempotent initialization is tested on temporary databases only.

## Manual mood UI

A core Material Face icon in the existing chat top bar has accessible label `Cập nhật tâm trạng`. No input-row control or existing panel/character dimension changes. It clears focus and hides the keyboard, then opens a compact Material bottom sheet with the existing five `MoodChoice` labels/mappings plus `Để sau`. Opening/dismissal changes only manual selector state, sends nothing and does not start speech, animation or reveal.

Selection consumes the same guarded companion selection state and normal send/request-id flow as Stage 16, preserving the typed draft. Busy/offline/retry states disable selection; selectionBusy and the normal sending guard prevent double taps. ViewModel state survives normal rotation/recomposition; a user turn closes the sheet. Manual choice can reopen after daily dismissal or earlier selection, independent of automatic eligibility. No daily marker is reset or written by manual opening/dismissal/selection. Automatic entry eligibility, client/date isolation and Stage 15 memory-reminder priority remain unchanged.

## Verification

Focused development verification after corrections:

- New routing plus existing Calendar/memory/companion/weather files: **542 passed**, one existing warning.
- New routing plus action/map/quick/time/provider-contract/fallback files: **377 passed** at that development revision; later new tests also included in final full run.
- Focused Android companion package: passed (existing 21 tests plus 5 new manual-mood tests).
- Release-resumption isolation check: `pytest -q -p no:cacheprovider tests/test_assistant_action_service.py::test_route_timer_returns_action_and_persists tests/test_assistant_action_service.py::test_route_map_search_returns_action` — **2 passed**, one existing deprecation warning. Both legacy route tests now run under the automatic temporary-database fixture and external-network guard; the real database was not opened for this check. No full suites were rerun.
- Earlier development failures exposed surface-adapter compatibility issues and the legacy database-isolation defect described above; all failing assertions pass after correction.

Final full suites run once after implementation stabilized:

```powershell
# backend
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider tests
.\.venv\Scripts\python.exe -m compileall -q app tests
# android; existing Android Studio JBR and SDK environment
.\gradlew.bat testDebugUnitTest
.\gradlew.bat assembleDebug
```

- Backend: **1,011 passed, 0 failed, 0 errors, 0 skipped**, 1 warning, 92.29 seconds. Warning: existing Starlette TestClient/httpx deprecation. Includes 90 new Stage 17 cases and all prior regressions. Compileall exit 0.
- Android XML: **262 total, 262 passed, 0 failures, 0 errors, 0 skipped**, 19 suites; five new manual-mood tests. Full unit Gradle build successful.
- `assembleDebug`: **BUILD SUCCESSFUL**.
- Local APK: `D:\nam5\semester_1\advance_android\01_trolyAI\troLyAo_ani_integration\android\app\build\outputs\apk\debug\app-debug.apk`; exists, ignored and untracked, never installed.
- `git diff --check`: passed; Git emitted only normal LF/CRLF conversion notices.
- Index empty; no APK/ZIP/database/.env/local.properties tracked or staged. No dependency, manifest, permission, asset, backend-URL, TTS, STT, reveal, FPS, font or layout-dimension change.
- Real `.env`, secrets and signing files were not manually read/printed/edited or committed. No real personal-memory contents were inspected or logged. No background notification/service, mood history or external dependency added.
- **Zero real external AI, RAG, embedding, Weather, Maps or Calendar calls.** Provider tests use fakes; Weather tests use fake transports; final suite additionally blocks accidental external sockets. Git network operations only fetch/push/verify repository refs.
- The local database **was touched** by the earlier legacy tests. Its external backup, read-only audit, remaining ownership ambiguity and explicit user acceptance are disclosed above. The user now authorizes the Stage 17 feature commit/push while preserving every database record. No full suite/build was rerun during release resumption: the corrected final results above remain applicable because production/test code was unchanged.

## Pre-commit git status --short

```text
 M android/app/src/main/java/com/example/assistant/ui/chat/ChatScreen.kt
 M android/app/src/main/java/com/example/assistant/ui/chat/ChatViewModel.kt
 M android/app/src/main/java/com/example/assistant/ui/companion/CompanionConversation.kt
 M backend/app/api/v1/conversations.py
 M backend/app/db/connection.py
 M backend/app/services/memory_context.py
 M backend/app/services/providers/gemini_provider.py
 M backend/app/services/providers/groq_provider.py
 M backend/tests/conftest.py
?? android/app/src/test/java/com/example/assistant/ui/companion/ManualMoodTest.kt
?? backend/app/services/intent_normalization.py
?? backend/app/services/intent_proposal.py
?? backend/app/services/pending_calendar.py
?? backend/tests/test_stage17_router.py
?? review/stage17-natural-language-router.md
```

After the authorized source/report commit, the required final status is empty (nothing staged or unstaged); the actual post-push result is checked and returned in the delivery response.

## Known limitations

- The local-data incident remains part of the release history: the database was backed up, three empty rows were accepted by the user, and the generic Maps candidate's ownership remains unproven. There is no claim that the real database was untouched or that unrelated historical modifications can be ruled out absolutely.
- Normalization handles a bounded set of wrappers, not unrestricted Vietnamese language. Terminal polite words can be linguistically ambiguous; quoted/complex requests may remain normal chat or require clearer wording.
- AI intent extraction depends on provider output and deliberately rejects uncertain/unsafe/unsupported proposals. No real AI behavior was tested. Existing RAG retrieval may precede a provider proposal because it remains part of the same normal generation path.
- Only Calendar has persistent slot completion. Arbitrary unrelated messages while pending receive a deterministic clarification until cancelled or replaced with a complete supported action. Title follow-ups are intentionally conservative.
- Pending expiry is lazy and idle-based. Conversation serialization is process-local with an atomic database recheck for Calendar writes; this remains the current single-worker demo architecture.
- Manual mood selection has no history/analytics/background behavior. Automatic mood markers remain device-local; no repeated automatic popup is introduced. Device app/service availability still governs Calendar/Maps/TTS/microphone behavior.

## Physical-device checklist

1. Keep the external database backup and the accepted empty rows in place; use a disposable backend database for further automated/dev tests. Restart the backend normally when intentionally applying the additive schema.
2. Send `Anna ơi, mấy giờ rồi nhé?`; verify a local time answer. Send `Xin chào Anna, cho mình hỏi ngày mai Hà Nội có mưa không?`; verify the weather query is not swallowed by greeting handling (user-controlled live device test only).
3. Test `Mở bản đồ tìm Hồ Gươm giúp mình với.`, `Anna dẫn mình đến Học viện Kỹ thuật Mật mã nhé.`, `Nhắc mình học bài sau 5 phút nhé.`; verify existing confirmation buttons and single launches.
4. Send `Làm ơn tạo lịch học Android lúc 8 giờ tối ngày mai giúp mình.`; confirm title/date/time before opening Calendar.
5. Send `Tạo lịch học Android lúc 8 giờ tối` → `Ngày mai`; verify missing-date question then exactly one Calendar confirmation action. Reverse with `Tạo lịch học Android vào ngày mai` → `8 giờ tối`.
6. Test `Tạo cho mình một lịch` → `Học Android` → `Thứ Hai tuần sau` → `7 giờ 30 sáng`; also `Ngày kia`, `Thứ Bảy tuần này`, `Ngày 25 tháng 10`, and `Tối mai lúc 8 giờ` with applicable current dates.
7. Test each cancellation phrase, invalid `25 giờ`/`20:75`, unrelated chat, conversation switching and expiry after ten idle minutes. Verify pending state never crosses conversations and retry does not duplicate completion.
8. Send the polite explicit memory/event example ending `từ hôm nay nhé.`; confirm saved memory/reminder in Settings. Verify an ordinary personal statement is not saved and educational negative examples do not create actions.
9. With an unsent draft, tap `Cập nhật tâm trạng`; verify draft retained, keyboard stays hidden, character/panel stable, no send/TTS. Dismiss with `Để sau`, reopen, select one mood and tap twice quickly; verify one exact Stage 16 mood message and draft retention.
10. Reopen manual selection after automatic mood was already consumed/dismissed; test all five existing mappings. Rotate/open Settings/return; verify no repeated automatic card or automatic send, no daily-marker reset, and offline/sending guards. Verify a due memory reminder still suppresses only the automatic mood card.
11. Smoke-test Stage 15 memory/check-ins, Stage 16 personalization/support choices, Weather, RAG, provider/quota fallback, Calendar/Maps/timer, history, TTS/stop/replay, typewriter/skip, microphone, animations/FPS/font, Settings and Demo picker. Close the app and confirm no background notification.

Do not merge Stage 17 into main; await physical-device verification and explicit integration approval.
