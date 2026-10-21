# Backend stage 12: local time quick replies

Final verdict: **READY FOR REVIEW**

## Branch and baseline

- Branch: `feature/local-time-quick-replies`.
- Baseline / unchanged HEAD: `8121d510a845dac761438f6e597e68d8f1872b1d`.
- Initial working tree was clean, on `main`. `git fetch origin --prune` confirmed `origin/main` equals the expected baseline; no descendant update was necessary.
- Executed `git switch main`, `git pull --ff-only origin main` (already up to date), and created the requested new branch. It did not previously exist.
- Fetch and branch operations required sandbox approval because this worktree's Git metadata resides in the sibling repository.

## Exact changed and added files

| Status | File |
| --- | --- |
| Modified | `backend/app/services/quick_reply_service.py` |
| Added | `backend/tests/test_local_time_quick_reply.py` |
| Added | `review/backend-stage12-local-time-quick-replies.md` |

No route, schema, dependency, environment file, provider, RAG, database, or Android source changes.

## Supported intent phrases

Case, repeated whitespace, and existing terminal punctuation normalization apply. New intents additionally fold Vietnamese accents using standard-library Unicode decomposition, so common unaccented equivalents work. Legacy normalization, patterns, response text, and matching order remain unchanged.

- Time: `Mấy giờ rồi?`, `Mấy giờ?`, `Bây giờ là mấy giờ?`, `Hiện tại là mấy giờ`, including optional `rồi` and optional `là` after `bây giờ` / `hiện tại`.
- Date: `Hôm nay là ngày bao nhiêu?`, `Hôm nay ngày mấy?`, `Ngày hôm nay là ngày bao nhiêu`; accepts `hôm nay` / `ngày hôm nay`, optional `là`, then `ngày bao nhiêu` / `ngày mấy`.
- Weekday: `Hôm nay là thứ mấy?`, `Hôm nay thứ mấy`; also accepts `ngày hôm nay` and optional `là`.
- Time of day: `Bây giờ là buổi gì?`, `Hiện tại đang là buổi sáng hay tối?`; accepts `bây giờ` / `hiện tại`, optional `đang` and `là`, followed by `buổi gì` / `buổi sáng hay tối`.
- Optional wrappers: `Anna`, `Anna ơi` (optional comma), `cho mình hỏi` / `cho tôi hỏi`, and final `nhé` / `nha` / `ạ`. Examples: `Anna ơi, mấy giờ rồi?`, `Cho mình hỏi bây giờ là mấy giờ`, `Anna ơi, hôm nay ngày bao nhiêu?`.
- All new replies use existing emotion `happy`; the unchanged route returns `sources: []`.

## Conservative matching

Each new pattern uses `fullmatch` on the entire normalized question, with only the explicit wrappers above. No substring search or broad temporal keyword detection. Quoted phrases, appended clauses, future dates, educational/meta questions, school information, and action commands fall through.

Focused negative tests include every requested example:

- `Giải thích câu "mấy giờ rồi" bằng tiếng Anh`
- `Viết đoạn hội thoại có câu mấy giờ rồi`
- `Tại sao con người chia một ngày thành 24 giờ?`
- `Học phí hiện tại là bao nhiêu?`
- `Thư viện mở cửa lúc mấy giờ?`
- `Mấy giờ ngày mai tôi nên học bài?`
- `Nhắc tôi học bài sau 5 phút`
- `Đặt lịch học lúc 8 giờ tối`
- `Tạo lịch vào ngày mai`
- `Tìm đường đến trường lúc 7 giờ`

Additional negatives cover timer/map commands, appended reminder requests, mixed school/date questions, unaccented scheduling text, tomorrow's weekday, and `Còn bao lâu đến 8 giờ tối?`. Countdown behavior was not implemented.

## Timezone and deterministic clock

Uses only Python standard library: `timezone(timedelta(hours=7))`. Production obtains `datetime.now(VIETNAM_TZ)` only after a local time intent matches. No Windows local timezone, locale weekday names, timezone database, or external service is required.

`get_quick_reply(message)` remains the production call interface and returns the same optional `(text, emotion)` tuple. Tests and the manual demo pass the optional keyword-only `now` argument with a timezone-aware `datetime`. Injected values are converted with `astimezone(VIETNAM_TZ)`. Naive injected datetimes raise `ValueError`, avoiding accidental machine-local conversion. Existing non-time replies do not read the clock.

Weekdays use Python's Monday-first `weekday()` mapping: `thứ Hai`, `thứ Ba`, `thứ Tư`, `thứ Năm`, `thứ Sáu`, `thứ Bảy`, `Chủ nhật`. All seven are tested. UTC conversion across midnight, date, and weekday is tested.

| Vietnam time | Reply period |
| --- | --- |
| 05:00–10:59 | buổi sáng |
| 11:00–12:59 | buổi trưa |
| 13:00–17:59 | buổi chiều |
| 18:00–22:59 | buổi tối |
| 23:00–04:59 | ban đêm |

Tests cover both sides of every transition and midnight. These boundaries are documented in the service.

## Route, persistence, and provider evidence

The route is unchanged: saved-request replay → assistant action recognition → quick reply → history/RAG/AI only on no match. Thus reminders, calendar, and map retain precedence and their existing contracts. No database schema or persistence/idempotency implementation was modified.

For each of the four new intent groups, route tests enable the real-AI and RAG routing flags while replacing retrieval, prompt construction, embedding, AI orchestration entrypoints, mock AI, `ProviderService.generate_reply`, `GeminiProvider.generate_reply`, and `GroqProvider.generate_reply` with immediate test failures. All four tests pass without reaching these guards.

SQL tracing confirms no conversation history query occurs. Tests also verify HTTP 200, exact existing Android response field sets, valid message UUIDs, emotion and timestamps, empty sources, exact persisted user/assistant rows, linked idempotency records, no source records, and identical replay without duplicate inserts. Replay disables quick-reply execution entirely, proving the stored answer is reused independently of a later clock value.

Existing quick-reply and action tests pass unchanged, including timer/map route behavior and action replay. Android, speech, animation, AI fallback policy, RAG/ingestion/embeddings, reminder/calendar/map behavior, persistence and request ownership logic were untouched.

## Verification

Run from `backend`:

```powershell
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider tests/test_local_time_quick_reply.py tests/test_quick_reply.py tests/test_messages.py tests/test_assistant_action_service.py
# 194 passed, 1 warning in 4.34s

.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider tests
# 416 passed, 1 warning in 39.34s

.\.venv\Scripts\python.exe -m compileall -q app tests
# Exit 0; no output
```

Full result: **416 passed, zero failures** = previous 352 tests plus 64 new tests. The single warning is an installed Starlette/httpx TestClient deprecation; no dependency changes were made.

Environment note: this checkout initially lacked `backend/.venv`. Created an ignored local Python 3.11 venv with `--without-pip` and an ignored `.pth` entry pointing to the sibling checkout's existing site-packages. No dependency installation/download or sibling environment modification occurred. Test fixtures use isolated SQLite databases and fake/mock provider implementations.

From the repository root, `git diff --check` passed with exit 0; `git status --short`, `git diff --stat`, `git diff --name-status`, and `git diff --cached --name-status` were checked. Ordinary diff output includes the tracked service modification (63 insertions, 2 deletions); the two added files remain untracked and are listed explicitly here and in status.

## Manual deterministic demonstration

Executed locally with `now=datetime(2026, 10, 12, 19, 34, tzinfo=VIETNAM_TZ)`:

```text
Mấy giờ rồi? => ('Bây giờ là 19 giờ 34 phút nhé!', 'happy')
Hôm nay là ngày bao nhiêu? => ('Hôm nay là ngày 12/10/2026 nhé!', 'happy')
Hôm nay là thứ mấy? => ('Hôm nay là thứ Hai, ngày 12/10/2026 nhé!', 'happy')
Bây giờ là buổi gì? => ('Bây giờ là buổi tối nhé!', 'happy')
```

The fixed demo date exists only in tests/demo, never in production responses. PowerShell's pipeline output encoding was explicitly set to UTF-8 for Vietnamese input.

## Final workspace status and confirmations

Full `git status --short`:

```text
 M backend/app/services/quick_reply_service.py
?? backend/tests/test_local_time_quick_reply.py
?? review/backend-stage12-local-time-quick-replies.md
```

- Android was untouched; no API request/response fields changed.
- Reminder/calendar/map contracts and implementation were untouched; existing action precedence remains intact.
- No real Gemini, Groq, embedding, or other external API calls occurred. Only the explicitly requested Git fetch/pull contacted the Git remote. Demonstration and verification used local code, local databases, and mocked providers.
- Nothing was staged, committed, merged, or pushed. `git diff --cached --name-status` is empty, and HEAD remains the baseline SHA.
