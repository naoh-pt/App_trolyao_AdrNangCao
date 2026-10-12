# D-AI Demo Readiness — Stage 0, 1 and 2 Report

## 1. Final verdict

**READY FOR REVIEW.** Stage 0 passed, Stage 1 backend changes and Stage 2 offline tests are implemented on `fix/d-ai-demo-readiness`. This is ready for code review, not an integration merge or a claim that the current Android 45-second timeout is solved. All 89 backend tests passed with fake/mock provider behavior.

## 2. Stage 0 branch verification

- Repository root: `D:/nam5/semester_1/advance_android/01_trolyAI/troLyAo_ani`; `.git/`, `android/`, `backend/`, and `review/` were present.
- Initial branch/commit: `integration/local-ai-demo` at `18810fa`. Both `git diff --name-only` and `git diff --cached --name-only` were empty: no pre-existing tracked or staged changes.
- Initial `git status --short`:

  ```text
  ?? android/android_stage6a_sources.zip
  ?? android/review/character_animation_stage4a_layered_chat_layout.md
  ?? android/review/character_animation_stage4b_ime_transparent_panel.md
  ?? review/
  ```

- `git fetch origin --prune` initially failed on `.git/FETCH_HEAD` permissions; the approved retry succeeded. `origin/feature/d-ai` remained `a5a36f444ea8ee111aca3da8bf116b4c0d4dbee8`, exactly the reviewed RAG commit. `git merge-base --is-ancestor a5a36f4 origin/feature/d-ai` succeeded; there were no additional commits or divergence.
- `fix/d-ai-demo-readiness` did not exist, so it was created directly from `origin/feature/d-ai`. Current HEAD remains `a5a36f4`; no commit was made. `integration/local-ai-demo` was not modified or merged.
- Switching to the backend-only branch causes the preserved local Android directory to appear as `?? android/` in short status. The pre-existing ZIP, Markdown reports, and other Android-local untracked artifacts were not edited, deleted, or overwritten.

## 3. Scope implemented

- Separate, validated SDK HTTP timeouts for generation and embedding; legacy `GEMINI_TIMEOUT_MS` remains an alias when the new generation setting is absent. Both root and backend examples now show the safe 38 s + 9 s configuration.
- Controlled RAG failures for opening/counting/querying Chroma and for missing, inconsistent, or malformed result data. The conversation route logs a category without raw exception text, then generates a normal reply when RAG is unavailable.
- Disabled RAG no longer invokes the retrieval wrapper from the conversation route; empty collection skips embedding; below-threshold results produce no RAG context.
- Backend README documents a one-worker demo, timeout limitations, and the future Android timeout relationship. No distributed lock, Android change, Anna personality, Groq support, or unrelated UI work was added.

## 4. Files changed

| File | Reason |
|---|---|
| `.env.example` | Align the repository-root timeout example with the backend's 38 s generation + 9 s embedding defaults; leave the key field empty. |
| `backend/app/config.py` | Parse and validate generation/embedding timeout values and combined budget; preserve legacy alias. |
| `backend/ai_service.py` | Use generation-specific SDK client timeout. |
| `backend/app/services/rag_service.py` | Use separate embedding SDK client; wrap expected Chroma and malformed-result failures as controlled RAG errors. |
| `backend/app/exceptions.py` | Give controlled RAG errors a safe category for logging. |
| `backend/app/api/v1/conversations.py` | Skip retrieval when RAG is disabled and log safe failure category before normal AI generation. |
| `backend/.env.example` | Demonstrate separate demo timeout settings; placeholders remain placeholders. |
| `backend/README.md` | Explain timing, one-worker constraint, SDK deadline limitation, and consistent `.venv` commands. |
| `backend/tests/conftest.py` | Force no real Gemini key and disable real AI/RAG by default in tests. |
| `backend/tests/test_timeout_config.py` | New pure config validation tests. |
| `backend/tests/test_rag_retrieval.py` | New in-memory Chroma/embedding fake tests. |
| `backend/tests/test_rag_conversation_route.py` | New real-mode route tests with fake AI/RAG and temporary SQLite. |
| `review/d-ai-demo-readiness-stage1-2.md` | This report. |

No file under `android/`, previous report, real `.env`, dependency file, or Git history was edited.

## 5. Timeout design

The installed `google-genai` 1.75.0 SDK exposes `types.HttpOptions(timeout: Optional[int])`; its field description says milliseconds. Separate `genai.Client` instances use the values below. Config is checked when `app.config` loads. Error messages name the invalid timeout/budget and never interpolate environment values or secrets.

| Operation | Config variable | Default | Maximum/validation | Behavior on timeout |
|---|---|---:|---:|---|
| Gemini generation | `GEMINI_GENERATION_TIMEOUT_MS`; legacy `GEMINI_TIMEOUT_MS` if new variable absent | 38,000 ms | Integer, 1–45,000 ms | Existing AI service maps timeout to controlled `LLM_TIMEOUT`/HTTP 504. |
| Query embedding / each import embedding call | `RAG_TIMEOUT_MS` | 9,000 ms | Integer, 1–15,000 ms | Embedding error becomes categorized `RAGUnavailableException`; chat falls back to normal generation. Import reports RAG unavailable. |
| Combined configured provider calls for one chat | Sum of above | 47,000 ms | At most 55,000 ms | Invalid configuration raises clear `ValueError` at import/startup. |

The new generation setting wins over the legacy alias if both are present. An old explicit 60,000 ms value now causes a clear startup configuration error unless changed; silently preserving it would violate the demo budget. The current Android read timeout is still 45 seconds, so a slow response may fail on the current app. The future Android integration target is about 65 seconds, leaving nominal room above the configured 55-second provider sum. This is **not a strict end-to-end deadline**: Chroma calls, Python/SQLite work, SDK retries if any, and cancellation after client disconnect are not bounded by this configuration. PDF ingestion may call embedding once per chunk and is outside the chat timing budget.

## 6. RAG fallback behavior

| Case | Behavior |
|---|---|
| RAG disabled | Route does not call `retrieve`; mock mode remains independent. |
| Empty collection | Returns `[]` before embedding; generation receives no RAG context. |
| Below relevance threshold / valid empty query result | Returns `[]`; generation receives no RAG context. |
| Valid relevant chunks | Preserves document/page/text/score, builds prompt context, generates and persists sources as before. |
| Embedding timeout/failure or missing key | Controlled `RAGUnavailableException` with `embedding`/`missing_key` category; route logs the category and tries normal generation. If generation also lacks a key, its existing controlled 503 remains. |
| Chroma open/count/query error, including dimension mismatch | Controlled `collection_open`, `collection_count`, or `collection_query` category; route continues without RAG. |
| Missing arrays, unequal lengths, invalid metadata/text/IDs, nonfinite distance | Controlled `invalid_result` category; route continues without RAG. |
| Generation failure after RAG fallback | Existing controlled AI 503/504, not mislabeled as RAG failure; no partial message pair is stored. |

Only expected external/format boundaries catch `Exception`; no `BaseException` catch was added. Warnings include a fixed category, not raw SDK errors, traceback, conversation text, or response bodies.

## 7. API compatibility

No endpoint path, HTTP method, request field, response field, or allowed emotion value was removed or renamed. Sending still accepts `request_id` and `message` with `X-Client-Id` and conversation ID in the path. Success still returns `user_message`, `assistant_message`, and the additive `sources` list. Android can ignore `sources`; `assistant_message.text` remains nonblank and emotion remains normalized to `neutral`, `happy`, `sad`, or `surprised`. RAG failure that permits normal generation keeps the same success schema. No Android file was changed.

## 8. Tests added

- `backend/tests/test_timeout_config.py`: defaults, legacy alias, new variable priority, valid budgets, invalid integer/float, zero/negative/out-of-range values, combined-budget violation, and secret-free configuration errors.
- `backend/tests/test_rag_retrieval.py`: disabled RAG, empty collection, valid Vietnamese query/metadata and prompt, irrelevant result, embedding timeout/provider failure via fakes, missing key, Chroma open/count/query/dimension failures, missing/unequal arrays, invalid metadata, invalid/nonfinite distance, valid empty arrays, and controlled exception categories. No persistent Chroma client is created.
- `backend/tests/test_rag_conversation_route.py`: relevant context passed to generation and sources persisted, empty RAG result, controlled RAG fallback with no 500/traceback, AI 503/504 with no messages, disabled RAG not retrieved, Android-compatible fields/additive sources, emotion normalization, same-request-ID replay without a second provider call, and missing key error. Provider functions are monkeypatched; SQLite uses the existing temporary test fixture.
- Existing tests were not deleted, weakened, skipped, or rewritten. The test fixture sets `GEMINI_API_KEY` to an empty process environment value before importing the app, so a developer key in `backend/.env` is not used by tests.

## 9. Test results

| Command | Result |
|---|---|
| `backend/.venv/Scripts/python.exe -m pip install -r backend/requirements.txt` | Initial sandbox run could not resolve `google-genai`; approved retry installed requirements **only in `backend/.venv`**. No global install. |
| From `backend`: `$env:PYTHONDONTWRITEBYTECODE='1'; .\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider tests` | **89 passed, 0 failed, 0 skipped, 1 warning** in 8.55 s on the final cleanup run. Warning: Starlette deprecation involving httpx TestClient. Earlier run before three additional fake cases: 86 passed. |
| From `backend`: set `PYTHONPYCACHEPREFIX` under system temp, then `.\.venv\Scripts\python.exe -m compileall -q app tests` | Passed; no project pycache was intentionally created. |
| `git diff --check` | Exit 0; only Git's LF/CRLF working-copy notices. |

No code test failed in the final run; no test was blocked after the virtualenv installation. No real Gemini/Groq/embedding call, real key, or persistent Chroma database was used. No backend server was started.

## 10. Previous findings status

| Finding | Status | Evidence |
|---|---|---|
| DUI-001 timeout mismatch | **PARTIAL** | Separate 38 s + 9 s defaults and ≤55 s configured sum in `config.py`, with config tests. Current Android remains 45 s, and no strict whole-request deadline exists. |
| DUI-002 Chroma errors return 500 | **FIXED for covered retrieval failures** | `rag_service.retrieve` categorizes open/count/query/result failures; route falls back. Fake tests cover each boundary and HTTP 200 fallback. Unexpected programmer bugs outside these boundaries are intentionally not hidden. |
| DUI-003 multi-worker duplicate calls | **DOCUMENTED FOR DEMO / OPEN** | README specifies `--workers 1` and explains process-local idempotency. No distributed lock was attempted. |
| DUI-007 missing RAG/real-mode tests | **FIXED for Stage 2 scope** | Three new offline test files; 89 backend tests passed, including RAG retrieval/route/config scenarios. No external provider integration test was run. |

## 11. Remaining risks

- Android still waits 45 seconds; its later 65-second change is outside this branch. Chroma work and full request cancellation lack a strict deadline. Therefore the full DUI-001 end-to-end condition remains partial.
- A multi-worker deployment can still duplicate paid provider calls for one `request_id`; demo must run one worker.
- PDF ingestion remains synchronous in an async upload handler and reads the whole upload before enforcing 15 MB; large or hostile PDFs and ingestion cost are outside this stage.
- Chroma and SQLite remain separate stores without atomic cross-store commit; orphaned chunks are possible after rollback failure.
- Provider error classification/logging in `ai_service.py` remains broader work; this stage sanitizes the new RAG fallback warning only.

## 12. Git status and diff summary

Current branch: `fix/d-ai-demo-readiness`; HEAD remains `a5a36f4`. `git diff --stat` covers nine modified tracked files, including the root `.env.example` (152 insertions, 43 deletions); it does not include three new untracked backend test files or this report. `git diff --check` passed. `git status --short` also reports `?? android/` and `?? review/` because the backend-only d-ai branch does not track the existing Android integration tree and prior review reports. All pre-existing untracked Android/ZIP/Markdown files remain untouched. No tracked Android path differs from HEAD, and no real `.env`, SQLite/Chroma database, PDF, log, ZIP, cache, or coverage artifact was added by this task. Nothing is staged, committed, merged, or pushed.

## 13. Recommended next step

Review the backend changes and tests on this fix branch. For a local demo, use the documented single-worker command and keep RAG data small/trusted. After review, change Android's read timeout on the integration branch, test the complete timing with fake delays, then integrate via the team's normal process. Handle multi-worker idempotency and the remaining ingestion/storage risks before production use. Do not begin Anna personality, Groq, RAG content preparation, or integration merge as part of this stage.
