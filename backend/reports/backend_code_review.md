# Independent backend code review — 2026-10-03

Scope: project plan, `backend/README.md`, milestone 1–3 reports, `member_c_handoff.md`, source, and tests. Source code and observed behavior take precedence over report claims. No real LLM or development database was used.

## Findings, ordered by severity

### Critical

None found.

### High

1. **An empty AI reply is committed as a successful message pair.** `backend/app/api/v1/conversations.py:295-318` unpacks the AI result and inserts `reply_text` without checking its type or trimmed content; `backend/app/db/connection.py:40` only requires non-NULL text. With a temporary database and a patched AI returning `("", "neutral")`, POST returned **200** with an empty `assistant_message.text` and saved both messages. This violates the plan's rule to report an error when the answer is missing, and leaves Android no retryable error. Validate a nonempty string after trim before starting the write transaction; map a missing/invalid reply to a structured 503, and persist neither message. Add an endpoint test for empty, whitespace, and non-string replies.

2. **Concurrent retries can make duplicate AI calls.** `backend/app/api/v1/conversations.py:227-295` checks `request_id` before calling AI, but reserves nothing in SQLite until `:320-330`. Two requests can both miss the record and call the paid service. A barrier-controlled temporary-database check observed **two AI calls**, two HTTP 200 responses with the same message IDs, and only two stored messages. The unique primary key and `IntegrityError` recovery at `:354-400` prevent duplicate committed pairs in that observed race, but do not prevent duplicate AI calls or their cost; if one call fails while the other succeeds, the failing caller can receive an error instead of the winning result. Reserve the request ID with an explicit pending state and an ownership/lease policy before calling AI, then make concurrent retries wait for or read the completed result. Define recovery for crashed owners and timeouts. Test overlapping calls with a barrier and assert the AI invocation count.

### Medium

3. **The backend does not enforce the emotion contract at its boundary.** `backend/app/api/v1/conversations.py:295,318,349` forwards `reply_emotion` unchanged, and `backend/app/schemas/conversation.py:34` permits any string or `null`. A patched AI returning `("answer", "unknown")` produced HTTP 200 and persisted `"unknown"`. The plan requires unfamiliar or missing emotions to become `neutral`; the handoff currently assigns that duty only to member D. Normalize and validate at the API boundary as defense against a malformed replacement service, and test unknown/missing/non-string emotion values.

4. **Deleting a conversation during the AI call yields HTTP 500 instead of a stable chat error.** `backend/app/api/v1/conversations.py:219-225` checks ownership before the AI call at `:295`; the write at `:305-318` happens later. In a temporary-database check, the AI stub deleted that conversation on a separate connection; the POST returned **500 `INTERNAL_ERROR`**. The foreign key correctly rejects the orphaned inserts and `with db:` rolls back, but `:354-400` catches the resulting `IntegrityError` as an idempotency race, finds no winner, and reraises it. Recheck conversation existence/ownership inside the write transaction and map a lost conversation to 404; distinguish foreign-key failures from request-ID conflicts. Test the deletion race.

5. **Conversation recency ordering can be wrong within one second.** `backend/app/utils/time.py:6-8` truncates UTC time to seconds, while `backend/app/api/v1/conversations.py:82` resolves equal `updated_at` by the conversation's creation `rowid`. If chat A is created, then B, then A receives a message within the same second, B stays first even though A was most recently active. A fixed-clock temporary-database check reproduced this. Store finer-grained UTC timestamps (or a monotonic activity sequence) and sort by actual activity; retain a deterministic tie-breaker. Test create/create/send inside one second.

6. **SQLite busy/lock failures fall through to a generic 500.** `backend/app/db/connection.py:14-17` sets a 15-second busy timeout and runs `PRAGMA journal_mode = WAL` on every connection. `backend/app/api/v1/conversations.py:301-400` only handles `sqlite3.IntegrityError`, while `backend/app/exceptions.py:87-92` turns all other errors, including `sqlite3.OperationalError: database is locked`, into 500. This is a code-path inference, not a reproduced lock test. A concurrent write or long-held lock can therefore return an undifferentiated error after the wait, and a client retry may call AI again. Initialize WAL once, handle busy/locked failures with a documented retryable response and bounded retry policy, and add a lock-contention test using two connections.

### Low

7. **The existing concurrency test overstates what it establishes.** `backend/tests/test_messages.py:194-228` sends two requests from threads, then checks equal IDs and a two-message count. It has no barrier to force both requests through the pre-AI lookup and no AI call counter, so it can pass through the sequential fast path. The targeted barrier check above confirms the untested duplicate-call behavior. Add synchronization and assert one AI invocation if that is the intended guarantee. The other tests use the real FastAPI route with a temporary DB through `backend/tests/conftest.py:13-36`; direct SQL setup in `backend/tests/test_conversations.py:159-177,246-270` verifies storage/query behavior but does not itself prove endpoint persistence after process restart.

## Verified behavior and limits of verification

- **Verified by source and existing tests:** `/api/v1` routes plus `/health`, normal HTTP 200/204/400/404/409/503/504 shapes, UUID parsing for client/path/request IDs, UTC `Z` timestamps, client-scoped access to conversations, last-ten-message query for the selected conversation in oldest-to-newest order, atomic pair/idempotency/`updated_at` write under `with db:`, foreign keys enabled on connections, rollback on an insertion failure, persistence across a new SQLite connection, and delete cascade for messages and idempotency records. The mock has the documented two-argument interface and returns Vietnamese replies with valid emotions on its ordinary branches. This is a code/test verification, not a claim that every edge case is covered.
- **Not independently verified from the milestone/handoff reports:** the reported live Uvicorn and physical Android/LAN checks; a full server-process restart; actual OpenAI integration, 30-second timeout, API-key handling under a future member D implementation, and real-service exception mapping. The current mock's sentinel-triggered 503/504 paths are tested, but no real LLM was called. The handoff's claims of complete concurrency handling and no blocking defects are contradicted by findings 1–6. The plan's M3 real-device/real-LLM milestone is not established by this backend-only review.
- **Repository hygiene:** `git ls-files` showed no tracked `.env`, SQLite database, WAL sidecar, or virtual environment. `.gitignore` contains rules for `.venv/`, `.env`, `*.db`, `*.db-*`, and Python/test caches. `git status --short --ignored` showed the local development DB and virtual environment as ignored. No secret values were read or printed. This checks tracked names and ignore behavior; it does not audit external logs or a future AI module.

## Commands and actual results

- `git ls-files`, `git status --short --ignored`, `rg --files ...`, and read-only source/report inspection: completed. No tracked database, environment file, or virtual environment was found.
- From `backend/`: `.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider` → **23 passed, 1 Starlette/httpx deprecation warning, 2.48 s**. Pytest used isolated `tmp_path` databases. No development database was modified.
- Temporary-database FastAPI checks, with the AI function patched only inside the Python process: empty reply → 200 and saved; unknown emotion → 200 and saved; non-tuple result → 500 `INTERNAL_ERROR` without a saved pair; barrier-controlled same-ID retry → 2 AI calls, 2 responses at 200 with the same IDs, 2 messages stored; delete during AI → 500 `INTERNAL_ERROR`; fixed one-second clock → newer-created chat remained first after the older chat received a message. One preliminary probe held a SQLite connection open and failed during temporary-directory cleanup on Windows; the focused reruns closed connections and completed successfully.
- No production source code, project plan, or development database was changed. This report is the only workspace edit.

## Verdict

**Ready after listed fixes.** The normal mock path is usable for exploratory integration, but member A should not rely on the documented missing-reply/retry behavior and member D should not attach a paid LLM until the high-severity validation and concurrent-request ownership issues are addressed. Address the medium findings before claiming the API contract is complete.
