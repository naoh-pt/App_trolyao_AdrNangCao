# Backend Stage 13.1c — Vietnamese calendar language parsing

Verdict: **READY FOR DEVICE TEST**

- Repository: `D:\nam5\semester_1\advance_android\01_troLyAI\troLyAo_ani_integration`.
- Branch throughout: `fix/android-stage13-1-external-actions`.
- Initial/base HEAD: `f73d92fde7ad03f7576eb2ed49898ef4934c1188`.
- Initial working tree was clean. The completed map punctuation fix is retained. No merge into main or branch/history rewriting occurred.
- Physical-device clarification accepted: `Tạo lịch học Android lúc 8 giờ tối ngày mai` already opens Calendar. **Android is untouched in this task**, including the launcher already present in the base. No new Android fallback work, APK build, or phone installation was performed.

## Root cause and previous grammar

Inspected the action service, route/serializers, existing action, map, quick-reply and request-ID/persistence tests before editing. Existing order is map → calendar → timer, followed by quick replies and history/RAG/AI only for non-actions.

The previous Calendar parser supported hôm nay and tomorrow variants only, with colon times or numeric giờ/h times. It searched for day-period words across the whole command, did not handle trưa, and treated 12 giờ đêm as noon. It had no weekday/week-relative/explicit-date grammar or injected clock. Separate regex title cleanup left prepositions such as `vào`, and a blank title silently became `Sự kiện mới`. Calendar trigger keywords could match inside explanatory sentences. Existing day/time checks could handle some word-order variations, but date coverage and extraction were insufficient; the functioning Android launch path was not the cause of these language gaps.

The route also regenerated an action on request-ID replay using the current wall clock. For relative dates this could shift an event, or remove its action once the requested time became past. The replay fix below is necessary to make deterministic parsing remain idempotent.

## Exact changed files

| Status | File |
| --- | --- |
| Modified | `backend/app/services/assistant_action_service.py` |
| Modified | `backend/app/api/v1/conversations.py` |
| Added | `backend/tests/test_calendar_language_parsing.py` |
| Added | `review/backend-stage13-1c-calendar-language-parsing.md` |

No API schemas, Android DTO field names, database schemas, dependencies, `.env`, provider routing, RAG, Android source, settings, image assets or local configuration changed.

## Grammar and extraction

Calendar recognition now starts at an explicit imperative prefix: đặt/tạo/lên/thêm lịch, or the existing nhắc tôi/mình/em/anh/chị/bạn form when an actual calendar date or `lúc <number>` is present. Existing optional xin/hãy prefixes remain. Relative timers still use the unchanged timer parser, including reminders mentioning a person named Mai.

One date and one time expression are matched. Date spans are blanked before matching time, preventing numeric dates from becoming hours/minutes. The same spans, including the adjacent syntactic `vào`/`lúc`, are removed from the original-case text to obtain the title. Date-before-time and time-before-date both work. Multiple date/time expressions, missing fields and malformed values clarify rather than guessing. Timer/map implementations, matching order and the default 30-minute Calendar duration are preserved.

Supported dates:

- `hôm nay`: Vietnam's current date.
- `ngày mai`, standalone `mai`, and existing `sáng/chiều/tối mai`: +1 day.
- `ngày kia`, optional `ngày mốt`: +2 days.
- `thứ 2`/`thứ hai`, `thứ 3`/`thứ ba`, `thứ 4`/`thứ tư`, `thứ 5`/`thứ năm`, `thứ 6`/`thứ sáu`, `thứ 7`/`thứ bảy`, `chủ nhật`.
- With Monday as day 0, `tuần này` selects that weekday in the current Monday–Sunday week; `tuần sau` and `tuần tới` select it in the next week. Past dates/times in an explicit current week clarify without rolling forward.
- Weekday + `tới` without a week chooses its nearest strictly future occurrence. Today is used if its requested time is future; otherwise that weekday is seven days later. This is the explicitly requested exception to the no-roll-forward rule for today/current-week dates.
- A bare weekday asks this week or next week. `cuối tuần này/sau/tới` asks Saturday or Sunday and creates no action.
- `25/10`, `25/10/2026`, `ngày 25 tháng 10`, `ngày 25 tháng 10 năm 2026`. Supplied years/dates must be valid and future. Without a year, choose the nearest valid future occurrence, including next year when this year's time has passed. Leap-day search covers the longest eight-year gap across a non-leap century. Partial or malformed supplied years are not silently discarded.

Supported time behavior:

| Expression | Result |
| --- | --- |
| `8 giờ sáng`, `8h sáng` | 08:00 |
| `3 giờ chiều` | 15:00 |
| `8 giờ tối`, `8h tối` | 20:00 |
| `12 giờ trưa` | 12:00 |
| `12 giờ đêm` | 00:00 |
| `20 giờ`, `20h` | 20:00 |
| `20:30`, `20h30` | 20:30 |
| `8h30 tối`, `8 giờ 30 tối` | 20:30 |

Colon notation remains explicit 24-hour time, including `08:00`; zero hour is unambiguous. Bare `8 giờ`, `8h`, `8h30` retain the product's morning/evening clarification rule. Hours above 23, minutes above 59, negative/fractional malformed times, conflicting day-period suffixes and incompatible periods such as 23 giờ sáng or 3 giờ trưa create no action. Periods are associated with the matched time/date phrase rather than searched globally.

## Timezone, validation and replay

`recognize_action(message, *, now=None)` accepts an aware datetime. The calendar parser converts injected clocks to the existing standard-library Vietnam fixed offset UTC+07:00; default production time uses that same offset. Naive injected clocks raise ValueError on otherwise valid calendar input. No locale, timezone database, network service or new dependency is needed.

An action requires a nonblank title with alphanumeric content, a valid aware start strictly after the reference clock, and a valid end exactly 30 minutes later and strictly after start. Overflow/invalid calendar dates produce a safe clarification. Explicit past hôm nay/current-week/year-qualified requests never become tomorrow/next week. Output is the unchanged ISO 8601 timestamp format with `+07:00`, which Android parses into epoch milliseconds using its existing DTO/dispatcher.

The route captures one clock before local recognition and persists that exact instant as the existing message/request timestamp for local actions. Non-action quick-reply/AI timestamp handling stays unchanged. `_saved_response` injects the saved user-message timestamp when reconstructing an action, preserving relative dates and original validation even if a retry occurs two weeks later. No new action table/column is added; the existing persistence contract still stores messages and request linkage and reconstructs actions on replay.

## Tests and bypass evidence

Fixed fixture: **2026-10-21 11:00:00 +07:00**. Required results pass:

- thứ 7 tuần này → **2026-10-24**.
- thứ 2 tuần sau → **2026-10-26**.
- chủ nhật tuần sau → **2026-11-01**.

All nine initial requested commands, six requested weekday examples and four explicit-date forms are tested with exact title/start/end results. Every weekday spelling/numeric form is exercised with all three week qualifiers and both orders (78 combinations). Additional tests cover today/tomorrow/mai/day-after-tomorrow/mốt in both orders, all time formats/conversions, ambiguity, blank title, malformed dates, month/year/leap-year rollovers, day-after-tomorrow across boundaries, Sunday→Monday, current weekday future/past, nearest weekday tới, yearless leap dates and explicit past times.

Conservative negatives include every requested ordinary question, explanatory/quoted calendar-command text, weekday definitions and library opening-time questions. Existing map punctuation commands and timers still pass, including relative timers with the name Mai.

For each of the 19 complete command examples, route tests run both real-AI flags false/true with RAG enabled. Retrieval, prompt construction, embedding, mock generation, Gemini, Groq, AI orchestration/get-provider and ProviderService generation are replaced by immediate test failures. Quick replies are also guarded. SQL tracing confirms the context-history SELECT never runs. All 38 complete-action cases pass without reaching those guards.

Route assertions check HTTP 200, exact existing response/message/action key sets and nullable fields, matching top-level/nested actions, exact valid title/start/end timestamps, happy emotion, empty sources, persisted complete user/assistant rows, linked request ID and no source records. A replay two weeks later returns identical response/actions with exactly two messages and one request record. Seven incomplete-command route cases also return HTTP 200 with safe clarification, no top-level/nested action button payload, empty sources, and generation/RAG guards untouched.

Executed from `backend`:

```powershell
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider tests/test_calendar_language_parsing.py tests/test_assistant_action_service.py tests/test_map_command_punctuation.py tests/test_messages.py
# 315 passed, 1 warning in 9.42s

.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider tests
# 696 passed, 1 warning in 38.25s

.\.venv\Scripts\python.exe -m compileall -q app tests
# Exit 0; no output
```

There are 227 added deterministic tests; all prior 469 backend tests remain and pass. The warning is the pre-existing installed Starlette/httpx TestClient deprecation. No real Gemini, Groq, RAG, embedding or other external API call occurred. Tests used local TestClient, isolated SQLite and injected/fake provider boundaries.

## Diff inspection and final status

Root `git diff --check` passes with no output. Inspected status, stat, name-status and the staged diff. `git diff f73d92fde7ad03f7576eb2ed49898ef4934c1188 -- android` is empty. Map and timer service blocks are unchanged; only Calendar parsing/clock injection and the necessary action replay timestamp integration changed. No generated file, secret, database or unrelated file is included.

Full reviewed `git status --short` before staging:

```text
 M backend/app/api/v1/conversations.py
 M backend/app/services/assistant_action_service.py
?? backend/tests/test_calendar_language_parsing.py
?? review/backend-stage13-1c-calendar-language-parsing.md
```

Publish only these four paths with commit message `fix(backend): expand Vietnamese calendar command parsing`, then push only `fix/android-stage13-1-external-actions`. No merge into main. The final post-publication `git status --short` must be empty and is checked in the completion response.

## Device-test commands

Restart the backend from this branch before sending new requests. Test the exact nine original commands and six weekday examples from the request, plus `Tạo lịch học vào ngày 25 tháng 10 năm 2027 lúc 20 giờ` as an explicit future-date example. Tap the Calendar button and inspect title, date, time and 30-minute duration before saving/canceling. Dates depend on the phone test's current Vietnam date, rather than the fixed test fixture above.

Also send `Tạo lịch học cuối tuần sau lúc 20 giờ`, `Tạo lịch học thứ bảy lúc 20 giờ`, `Tạo lịch học ngày mai lúc 8 giờ`, `Tạo lịch vào ngày mai lúc 20 giờ`, and `Tạo lịch học ngày mai lúc 25 giờ`: expect clarification with no Calendar action. Check a past time today similarly. Recheck `Tìm trên bản đồ Hồ Gươm.` and `Nhắc tôi học bài sau 5 phút` for map/timer regression. No Android reinstall is required for this backend-only change.
