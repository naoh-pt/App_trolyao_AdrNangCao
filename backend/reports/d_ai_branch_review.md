# Review: `feature/d-ai` AI integration

Reviewed on 2026-10-03 from `main` without switching the current worktree. `git fetch origin` found `origin/feature/d-ai` at `539c3d7`. The merge base with current `origin/main` is `1668e29`; the three-dot diff contains only the added `backend/ai_service.py`. The review report is the only file created in the current worktree and is uncommitted.

## Findings by severity

### High

1. **The new service is not connected to the API endpoint, so merging this branch does not enable real AI.** The branch's `backend/app/api/v1/conversations.py:25,295` imports and invokes `app.services.mock_ai`. The added `backend/ai_service.py` is not imported. The merge candidate against current main likewise only adds the new file, leaving the endpoint call unchanged. `POST /api/v1/conversations/{id}/messages` therefore continues returning the mock response. The HTTP/Android contract itself is untouched, but the integration is not active. **Fix:** wire the AI implementation into the endpoint while retaining an explicit mock selection for offline development and member A; add an endpoint test proving which implementation is selected.

2. **Conversation history text is dropped when constructing the provider request.** The backend supplies context items as `{"role", "text", "emotion"}` (`backend/app/api/v1/conversations.py:275-277` on current main; same contract in the branch endpoint). `backend/ai_service.py:29-31` reads each item's `content` key, so every prior turn becomes an empty content string. Roles are otherwise copied, and the endpoint builds context from only the selected conversation's last ten rows in chronological order, so I found no cross-conversation history leak. **Impact:** after wiring, the provider receives the current message but not the prior conversation text. **Fix:** map `msg["text"]` to provider `content` and add a mocked-provider test asserting roles, contents, order, and conversation isolation.

3. **Provider errors do not map to the backend's structured 503/504 exceptions, and the effective timeout can exceed the 35-second request wait.** `backend/ai_service.py:33-38` sets a 30-second timeout, but `:49-51` catches every exception and raises plain `Exception("LLM_UNAVAILABLE")`. The endpoint's generic handler maps that to HTTP 500; it does not distinguish timeouts. The current SDK documentation says requests retry twice by default, including timeouts, so 30 seconds is a per-attempt timeout rather than a 35-second total deadline. The exact SDK version is not declared or installed here; current official guidance documents the retry behavior and permits request-level timeout configuration ([OpenAI Python SDK retry and timeout documentation](https://github.com/openai/openai-python#retries)). **Impact:** a provider timeout can keep the request owner past the 35-second wait and error responses do not match the documented structured codes. **Fix:** add and pin a compatible SDK; choose a total retry/deadline budget below 35 seconds (for example, disable SDK retries and use a bounded single attempt); catch provider timeout exceptions as `LLMTimeoutException` (504), other provider failures as `LLMUnavailableException` (503), and avoid replacing these with plain exceptions. The endpoint calls AI before its SQLite write transaction, so these failures do not save a partial user/assistant pair.

### Medium

4. **Provider output validation is incomplete before the backend boundary.** `backend/ai_service.py:40-47` substitutes a normal-looking placeholder when JSON omits `reply`, so the current main endpoint's nonempty-string guard (`backend/app/api/v1/conversations.py:280-285`) accepts and can save a fabricated success. A non-string `emotion` raises at `.lower()` (`ai_service.py:42`) and falls into finding 3's plain-exception path. Empty/non-string replies are rejected by the current main endpoint boundary when the service is wired; missing reply and non-string emotion are not safely handled by this service. Unknown string emotions and missing emotion are normalized to `neutral`. **Fix:** require a JSON object with a nonblank string `reply`; normalize absent, non-string, and unknown emotions to `neutral`; raise the existing structured LLM exception for malformed output.

5. **The OpenAI package and setup instructions are missing, so the new module cannot import in the reviewed environment.** `backend/ai_service.py:5` imports `openai`, but the branch's `backend/requirements.txt:1-4` adds no OpenAI dependency. `pip show openai` reported “Package(s) not found”, and importing `ai_service` with `OPENAI_API_KEY` cleared failed with `ModuleNotFoundError: openai`. The branch has no tracked `.env.example`, and `backend/README.md` does not explain key/model configuration. The existing handoff example uses `OPENAI_MODEL=gpt-4o-mini` (`backend/reports/member_c_handoff.md:228-233`), while the service defaults to `gpt-3.5-turbo` (`ai_service.py:8`). **Fix:** declare and pin the compatible SDK, add a placeholder-only `.env.example`, document safe Windows environment setup, and align the documented/default model. Do not commit `.env`.

6. **The existing tests do not exercise the new AI code.** The branch adds no test files. Existing `backend/tests/test_messages.py:9,91-125` patches and verifies `app.services.mock_ai`; no test imports `ai_service`, inspects the provider request, or checks provider success, timeout, failure, malformed JSON, mock fallback, endpoint wiring, or idempotency through the real-service adapter. The passing suite therefore verifies the existing mock path only. **Fix:** inject or mock the SDK client and add offline tests for each of those adapter and endpoint paths; keep a test confirming same-ID retries and atomic persistence.

### Low

7. **Raw provider exception text is printed.** `backend/ai_service.py:49-50` writes `str(e)` to stdout. I found no hardcoded API key, and the branch tree contains no tracked `.env` or `.env.example`; the service reads the key from `OPENAI_API_KEY` (`:7`) and does not explicitly print that variable. Whether a particular SDK exception includes sensitive provider details is unverified, but logging arbitrary provider text creates that risk. **Fix:** log a sanitized exception class/status and a request correlation ID, without raw provider response text or request content.

8. **The added file has a formatting defect.** `backend/ai_service.py:36` has trailing whitespace, and the file has no final newline. `git diff --check origin/main...origin/feature/d-ai` reports the trailing whitespace. **Fix:** remove the trailing whitespace and add the final newline.

## Verified behavior and untested claims

- **Verified from source:** `generate_reply(context, message) -> Tuple[str, str]` exists (`ai_service.py:21`). `OPENAI_API_KEY` and `OPENAI_MODEL` are read from environment variables (`:7-10`); no secret value is hardcoded in the branch diff. The endpoint context contains role/text/emotion from the selected conversation and is ordered oldest to newest (`backend/app/api/v1/conversations.py:265-278` on current main). The service copies roles but loses prior-turn content because of the key mismatch. The existing mock service and mock endpoint mode remain available in current main; this branch does not switch the endpoint to the new service.
- **Verified from source and local environment:** a timeout argument of 30 seconds is passed at both client construction and request call (`ai_service.py:10,33-38`). The `openai` SDK is absent from `backend/requirements.txt` and the available backend virtual environment. The new module import fails without that package. There is no provider call in this review.
- **Not verified:** successful request against OpenAI, exact runtime compatibility with a particular SDK release, actual provider timeout duration under retries, authentication/provider exception payload contents, and provider JSON behavior. No API key was read or printed. The provider was never called.
- **Repository hygiene:** the branch tree lists only `backend/ai_service.py` as an addition relative to the merge base. No `.env` or `.env.example` is tracked on `origin/feature/d-ai`; no environment file contents were inspected. The branch diff contains no key literal.

## Commands and results

- `git status --short --branch` → `main...origin/main`, clean before report creation.
- `git fetch origin` → succeeded after allowing Git metadata/network access; fetched `origin/feature/d-ai`.
- `git merge-base origin/main origin/feature/d-ai` → `1668e29419f18fbfda81a5d8fc1f27c52b425338`.
- `git diff --name-status origin/main...origin/feature/d-ai` → only `A backend/ai_service.py`.
- `git diff --check origin/main...origin/feature/d-ai` → trailing whitespace warning at `backend/ai_service.py:36`.
- `pip show openai` → package not found. Safe import probe with `OPENAI_API_KEY` set to empty → `openai_installed False`, `ai_service_import_error openai`.
- In a temporary detached worktree at `origin/feature/d-ai`, with `OPENAI_API_KEY` set to empty: `& 'D:\nam5\semester_1\advance_android\troLyAo_ani\backend\.venv\Scripts\python.exe' -m pytest -q -p no:cacheprovider` → **23 passed, 1 Starlette/httpx deprecation warning, 1.99 s**. These are mock/backend tests and do not cover `ai_service.py`.
- Removed the temporary worktree; `git worktree list` shows only the project worktree on `main`.
- No source code, tests, README, requirements, or branch refs were modified. This report is uncommitted in the current `main` working tree.

## Verdict

**Blocked.** The branch does not connect the real service to the API, drops prior-turn text, lacks its SDK dependency/setup, and does not map provider failures to the documented exceptions. Merge only after the high and medium findings are fixed and covered by offline tests.
