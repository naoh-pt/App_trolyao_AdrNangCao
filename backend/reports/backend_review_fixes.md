# Backend review fixes — 2026-10-03

The fixes target the confirmed findings in `backend/reports/backend_code_review.md`. The `/api/v1` paths, request bodies, normal success status codes, response shapes, client scoping, and SQLite development database path remain the same. No real LLM was called and the development database was not opened for these tests.

## Exact files changed

| File | Change |
| --- | --- |
| `backend/app/api/v1/conversations.py` | Validate AI output, normalize emotion, recheck idempotency under request ownership, recheck the conversation inside `BEGIN IMMEDIATE`, distinguish foreign-key failures, and sort mixed legacy/new timestamps correctly. |
| `backend/app/services/request_guard.py` | New per-`request_id` process-local lock registry with a 35-second wait and reference-counted cleanup. |
| `backend/app/db/connection.py` | Set WAL during initialization only, close the initialization connection, and bound each SQLite busy wait to 2 seconds. Permit FastAPI's thread handoff for per-request connections. |
| `backend/app/exceptions.py` | Add structured `LLM_UNAVAILABLE`, `REQUEST_IN_PROGRESS`, and `DATABASE_BUSY` responses for the new failure paths. |
| `backend/app/main.py` | Register the SQLite operational-error handler. |
| `backend/app/utils/time.py` | Emit UTC ISO 8601 timestamps with microsecond precision and `Z`. |
| `backend/tests/test_review_fixes.py` | Add 16 focused regression cases using temporary SQLite databases and the actual FastAPI route. |
| `backend/README.md` | Document retry, lock-wait, timestamp, and single-worker behavior. |
| `backend/reports/member_c_handoff.md` | Correct the earlier completeness claims and update the A/D integration guidance and test count. |
| `backend/reports/backend_review_fixes.md` | This report. |

`backend/reports/backend_code_review.md` was created during the preceding review and left unchanged in this fix pass.

## Before and after

| Scenario | Before | After |
| --- | --- | --- |
| AI returns empty, whitespace, non-string, or malformed pair | Empty text could be committed with HTTP 200; malformed pair could return 500. | HTTP 503 `LLM_UNAVAILABLE`; no message or idempotency record is written. |
| AI emotion is missing, non-string, or outside the four allowed values | Value passed through to response and database. | Backend returns and stores `neutral`. |
| Two simultaneous same-ID requests in one process | Both could call AI; SQLite allowed only one pair to commit. | One request owns the ID; the other waits and reads the committed pair. A 35-second wait limit returns HTTP 503 `REQUEST_IN_PROGRESS`. The SQLite primary key and transaction remain the final duplicate-write guard. |
| Conversation deleted while AI runs | Foreign-key failure became HTTP 500. | Inside `BEGIN IMMEDIATE`, the server rechecks ownership and returns HTTP 404 `NOT_FOUND`; no orphaned messages are saved. Foreign-key failures are considered separately from ID conflicts. |
| Conversation updated within the same second | Seconds-only `updated_at` could leave the older chat below a newer-created chat. | Microsecond UTC timestamps preserve recency. Conversation and message queries normalize older seconds-only timestamps during reads, so existing rows remain correctly comparable. Message ordering still uses timestamp and `rowid` as a deterministic tie-breaker. |
| SQLite writer holds the lock | Busy/locked failure could become HTTP 500 after a 15-second wait. WAL was set on every connection. | Each SQLite operation waits at most 2 seconds, then HTTP 503 `DATABASE_BUSY` with `Retry-After: 1`; WAL is set during startup initialization. Client retries retain the same `request_id` and text. |

## Verification

- Complete suite: from `backend/`, `.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider` → **39 passed, 1 Starlette/httpx deprecation warning, 7.27 s**. The original 23 tests continue to pass. The 16 new parameterized cases cover invalid AI replies, emotion normalization, forced overlapping same-ID retries with an AI invocation count, bounded lock wait and registry cleanup, deletion during AI, mixed old/new timestamp ordering, and SQLite busy on create/send with a successful retry.
- Focused live HTTP flow: started one Uvicorn process on `127.0.0.1` with `SQLITE_DB_PATH` pointing to a temporary database and the mock AI. Health, create, send, same-ID retry, list messages, delete, and post-delete read returned **200, 200, 200, 200, 200, 204, 404**; retry returned the identical message pair. The process was terminated and the temporary database removed after the check.
- `git diff --check` returned no whitespace errors. No Android code, project plan, source report, or development database was changed; no commit or push was made.

## Remaining limits

- The per-key guard is in memory and protects only a **single Uvicorn worker/server process**. Multiple workers or server processes can still both call a paid LLM for the same ID, although SQLite's unique key prevents duplicate committed pairs. Run one worker for this laptop demo.
- If the owner fails before commit, a waiting retry can make a fresh AI call after acquiring the key. A timeout after the remote provider accepted a request may also be billed before a later retry. The backend does not claim exactly-once remote execution.
- The backend does not impose an LLM call deadline itself. Member D must implement the documented timeout and raise `LLMTimeoutException` or `LLMUnavailableException` for provider failures. The 35-second in-process wait assumes a roughly 30-second provider deadline.
- The live flow used localhost and mock AI. Real Android/LAN and paid-provider integration remain to be checked by members A and D.
