# Stage 4 Review Report: Provider Abstraction & Groq Fallback

**Branch:** `fix/d-ai-demo-readiness`  
**Date:** 2026-10-09  
**Status:** Completed (Stage 4 Compatibility & Timeout Cleanup Verified, 328 Passing Tests, 0 Regressions)

---

## 1. Environment & Dependency Specifications

- **Python Version:** 3.11.9 (`.\backend\.venv\Scripts\python.exe --version`)
- **Installed Groq SDK Version:** `1.7.0` (official Groq Python SDK 1.x line)
- **Groq Dependency Range in `backend/requirements.txt`:** `groq>=1.7.0,<2.0.0`
- **Installed Google GenAI SDK:** `google-genai>=1.0.0,<2.0.0` (1.52.0)
- **Active Chat Generation Models:**
  - Gemini: `gemini-3.5-flash`
  - Groq: `openai/gpt-oss-120b` (replaces deprecated `llama-3.3-70b-versatile`)
- **Active Embedding Model:** `gemini-embedding-2` (dedicated to Gemini RAG)

---

## 2. Provider Architecture Summary

Stage 4 introduces a minimal, clean, and maintainable generation-provider abstraction under `backend/app/services/providers/`:

```
backend/app/services/providers/
├── __init__.py           # get_provider_service(), set_provider_service(), exports
├── base.py               # BaseProvider abstract base class
├── config.py             # ProviderConfig dataclass & strict validation (timeouts, budget, names)
├── gemini_provider.py    # GeminiProvider (Google GenAI SDK, lazy client, emotion normalization)
├── groq_provider.py      # GroqProvider (official groq Python SDK 1.x, lazy client, json_object mode)
└── provider_service.py   # ProviderService orchestrator & fallback policy
```

### Key Architectural Boundaries
1. **Separation of Concerns:** Route code in `app/api/v1/conversations.py` and `ai_service.py` has no direct coupling to provider SDKs. `ai_service.generate_reply` delegates directly to `get_provider_service().generate_reply(...)`.
2. **Backward Compatibility:** `ai_service.py` preserves `generate_reply` signature and references `client` so existing test fixtures continue to function seamlessly.
3. **Anna Character Centralization:** Anna's persona, system instructions, and emotion rules remain centralized in `app/services/personality.py`. Both Gemini and Groq inject `ANNA_SYSTEM_PROMPT` into their respective system message channels.
4. **Independent RAG Embeddings:** RAG document embedding and retrieval remain strictly Gemini-based (`gemini-embedding-2`) in `app/services/rag_service.py` and are not affected by generation provider selection.
5. **No Startup Network Calls:** SDK clients (`genai.Client` and `groq.Groq`) are initialized lazily inside provider instances, preventing network attempts or crashes on import when API keys are absent.

---

## 3. Supported Provider Configurations

Configuration is managed via environment variables and loaded through `backend/app/config.py` and `app/services/providers/config.py`:

| Variable | Default Value | Description |
|---|---|---|
| `AI_PRIMARY_PROVIDER` | `gemini` | Primary generation provider (`gemini` or `groq`) |
| `AI_FALLBACK_PROVIDER` | `groq` | Fallback generation provider (`groq`, `gemini`, or `none`) |
| `GEMINI_API_KEY` | `""` | Google AI Studio API key |
| `GEMINI_MODEL` | `gemini-3.5-flash` | Gemini model name |
| `GROQ_API_KEY` | `""` | Groq API key |
| `GROQ_MODEL` | `openai/gpt-oss-120b` | Groq model name (`openai/gpt-oss-120b`) |
| `RAG_TIMEOUT_MS` | `9000` | Timeout per embedding HTTP request (9 seconds) |
| `GEMINI_GENERATION_TIMEOUT_MS`| `28000` | Timeout per Gemini generation request (28 seconds) |
| `GROQ_TIMEOUT_MS` | `15000` | Timeout per Groq generation request (15 seconds) |
| `AI_TOTAL_TIMEOUT_MS` | `55000` | Maximum total allowed timeout budget (55 seconds) |

### Supported Modes:
- **Gemini Primary + Groq Fallback (Default Demo Mode):** Best balance of quality and resilience.
- **Groq Primary + Gemini Fallback:** Low-latency primary with Gemini fallback.
- **Single Provider Mode:** `AI_FALLBACK_PROVIDER=none` (or empty), disabling fallback.
- **Offline Mock Mode:** `USE_REAL_AI=false` routes requests to local mock generator without network or API keys.

---

## 4. Disabling SDK Automatic Retries & Request Sequence

To prevent SDK retry mechanisms from multiplying execution time and exceeding the demo budget:

1. **Groq Generation Client:**
   - Initialized with `max_retries=0`.
   - `timeout` parameter explicitly converted from milliseconds to seconds: `float(self.timeout_ms) / 1000.0` (15.0s).
2. **Gemini Generation Client:**
   - Configured with `types.HttpOptions(api_version="v1", timeout=self.timeout_ms, retry_options=types.HttpRetryOptions(attempts=1))`.
   - Retry attempt count: exactly **1 attempt** (0 retries).
3. **Gemini RAG Embedding Client:**
   - Configured with `types.HttpOptions(api_version="v1", timeout=RAG_TIMEOUT_MS, retry_options=types.HttpRetryOptions(attempts=1))`.
   - Retry attempt count: exactly **1 attempt** (0 retries).

### Expected Request Execution Sequence:
- **Step 1:** RAG embedding: at most one provider attempt (<= 9,000 ms).
- **Step 2:** Primary generation: at most one provider attempt (<= 28,000 ms).
- **Step 3:** Fallback generation: at most one provider attempt if primary fails with an eligible error (<= 15,000 ms).

---

## 5. Fallback Matrix & Observed Behavior

| Primary Provider Result | Fallback Provider Result | System Outcome | HTTP Code | Emotion | Sources |
|---|---|---|---|---|---|
| Gemini Succeeds | Not called | Gemini response returned | 200 | Normalized | RAG / `[]` |
| Gemini Quota (429) | Groq Succeeds | Groq response returned | 200 | Normalized | RAG / `[]` |
| Gemini Timeout (504) | Groq Succeeds | Groq response returned | 200 | Normalized | RAG / `[]` |
| Gemini 5xx / Network (503) | Groq Succeeds | Groq response returned | 200 | Normalized | RAG / `[]` |
| Groq Succeeds (as Primary)| Not called | Groq response returned | 200 | Normalized | RAG / `[]` |
| Groq Fails | Gemini Succeeds | Gemini response returned | 200 | Normalized | RAG / `[]` |
| Primary Fails | Fallback Disabled (`none`) | Original error propagated | 429/503/504 | - | - |
| Primary Quota (429) | Fallback Quota (429) | Anna friendly apology reply | 200 | `sad` | `[]` |
| Primary Timeout | Fallback Timeout | `LLMTimeoutException` | 504 | - | - |
| Primary Network/5xx | Fallback Network/5xx | `LLMUnavailableException` | 503 | - | - |
| Primary Auth Failure | Fallback Succeeds | Fallback response returned | 200 | Normalized | RAG / `[]` |
| Primary Auth Failure | Fallback Disabled / Fails | `LLMUnavailableException` | 503 | - | - |
| Programming Error | Not called | Bug exception propagated | 500 | - | - |
| Quick Reply ("xin chào")| Neither called | Deterministic local reply | 200 | Defined | `[]` |
| Idempotency Replay | Neither called | Cached DB response returned | 200 | Original | Original |

*Design Choice Documentation:* Primary authentication failure (missing or invalid key) triggers fallback if a secondary provider is configured and usable, providing high availability during live demos if an API key expires. If fallback is disabled or also fails, a controlled 503 `LLM_UNAVAILABLE` is raised.

---

## 6. Timeout Budget Calculation and Rationale

The sequential execution budget is configured as:

$$\text{RAG Embedding (9,000 ms)} + \text{Gemini Generation (28,000 ms)} + \text{Groq Generation (15,000 ms)} = 52,000\text{ ms} \le 55,000\text{ ms}$$

- **RAG Timeout:** 9,000 ms ensures embedding generation completes or fails quickly without exhausting the chat budget.
- **Gemini Timeout:** 28,000 ms allows thorough reasoning while preserving headroom for the 15,000 ms Groq fallback.
- **Groq Timeout:** 15,000 ms provides ample time for `openai/gpt-oss-120b` generation on Groq's low-latency LPU infrastructure.
- **Validation Guard:** `read_provider_config` calculates worst-case sequential execution time and rejects configurations that exceed `AI_TOTAL_TIMEOUT_MS` at startup without leaking secrets.
- **Clarification on Budget vs. Wall-Clock Deadline:** The 52,000 ms figure is the **sum of individual provider timeout configurations**. It is **not** an enforced whole-request wall-clock cancellation deadline because Python processing, SQLite locks, Chroma vector search, network connection setup, and operating system scheduling may add extra time.
- **Android Client Timeout Recommendation:** The Android client OkHttp read timeout should be set to **at least 65,000 ms** during integration testing to prevent premature client-side disconnections while fallback is completing.

---

## 7. Personality, Emotion, and Quick Reply Preservation

- **Personality:** Both `GeminiProvider` and `GroqProvider` inject the full `ANNA_SYSTEM_PROMPT` into their respective system instructions. Anna's cheerfulness, school context (Học viện Kỹ thuật Mật mã), and boundaries are maintained across both LLMs.
- **Emotion Rules:** Both providers parse JSON responses and invoke `normalize_emotion(result.get("emotion"))`, restricting emotions strictly to the four Android-compatible states: `neutral`, `happy`, `sad`, `surprised`. Missing, unknown, or whitespace-padded emotions cleanly normalize to `neutral` or stripped lowercase values.
- **Quick Replies:** Deterministic local replies (`get_quick_reply`) continue to run before any provider invocation. Standard greetings, gratitude, and identity queries bypass all providers entirely.
- **Friendly Quota Apology:** When both providers encounter quota exhaustion, Anna's friendly quota message ("Anna đang hơi mệt một chút vì nhiều bạn hỏi cùng lúc quá...") is returned with emotion `sad` and empty `sources: []`, committed atomically to SQLite with request idempotency.

---

## 8. RAG Embedding Separation Confirmation

- RAG embeddings in `app/services/rag_service.py` continue to use `genai.Client` and `gemini-embedding-2`.
- `GroqProvider` is strictly a text generation provider and has no dependencies on the RAG vector store or ChromaDB.
- When RAG context is retrieved, it is appended identically to the system instruction prompt passed to whichever generation provider executes.

---

## 9. Test Strategy & Test Counts

All tests are 100% offline, use isolated SQLite databases, and make zero network calls.

### Test Suites:
1. `tests/test_provider_config.py` (30 tests):
   - Case-insensitive provider normalization (`gemini`, `groq`, `none`, empty).
   - Unknown provider rejection without secret leakage.
   - Timeout budget validation and arithmetic checks.
   - Backward-compatible `read_timeout_config` validation.
   - Default Groq model validation (`openai/gpt-oss-120b`).
   - Deprecated model absence check (`llama-3.3-70b-versatile` absent).
2. `tests/test_provider_contracts.py` (40 tests):
   - Structured JSON parsing and schema enforcement for both Gemini and Groq.
   - Emotion normalization (missing, invalid, uppercase, whitespace).
   - Empty reply and malformed JSON safety.
   - Provider exception mapping (429 -> quota, timeout -> timeout, 401/5xx -> unavailable).
   - Prompt, history ordering, and RAG context transmission.
   - Groq `max_retries=0` and timeout millisecond-to-second conversion verification.
   - Gemini generation `HttpRetryOptions(attempts=1)` single-attempt verification.
   - Gemini embedding `HttpRetryOptions(attempts=1)` single-attempt verification.
3. `tests/test_provider_fallback.py` (23 tests):
   - Fallback eligibility rules (programming bugs excluded, transient/quota errors included).
   - Full fallback matrix execution (Gemini -> Groq, Groq -> Gemini, dual failures).
   - Route-level integration: fallback returns 200, dual quota returns Anna friendly apology, quick reply bypass, idempotency caching.
4. Pre-existing test suite (235 tests):
   - All 235 pre-existing tests pass with zero regressions.

**Targeted Stage 4 Tests:** **93 passed** (30 + 40 + 23).  
**Total Full Test Suite:** **328 passed**, 0 failed.

---

## 10. Verification Checklist Results

- [x] Branch is `fix/d-ai-demo-readiness`.
- [x] Groq dependency updated to `groq>=1.7.0,<2.0.0` (installed v1.7.0 in `.venv`).
- [x] Deprecated `llama-3.3-70b-versatile` replaced with `openai/gpt-oss-120b` across all configs, docs, and code.
- [x] Automatic SDK retries disabled: Groq `max_retries=0`, Gemini generation and embedding `HttpRetryOptions(attempts=1)`.
- [x] Sequential timeout budget adheres to 55,000 ms constraint ($9\text{s} + 28\text{s} + 15\text{s} = 52\text{s} \le 55\text{s}$).
- [x] `.env.example` and `backend/.env.example` updated with empty secret values.
- [x] `backend/README.md` updated with dual provider documentation, single-worker constraints, and accurate timeout explanation.
- [x] Zero Android files modified.
- [x] Zero real external API calls executed during tests (all offline fakes/mocks).
- [x] No live API / model availability test was performed.
- [x] No test hooks or magic strings in runtime code.
- [x] No git commit, merge, or push performed.

---

## 11. Deployment & Demo Instructions

### Starting the Backend for Demo:
```powershell
cd d:\nam5\semester_1\advance_android\01_trolyAI\troLyAo_ani\backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1
```

### Running Test Verification:
```powershell
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider tests/test_provider_config.py tests/test_provider_contracts.py tests/test_provider_fallback.py
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider tests
.\.venv\Scripts\python.exe -m compileall -q app tests
```

---

## 12. Remaining Operational Risks

1. **No Live API Verification:** All tests were conducted 100% offline using mock SDK clients. Live availability of `openai/gpt-oss-120b` under the user's specific Groq organization/tier and the Gemini model must be verified in staging with real API keys.
2. **Single-Worker Demo Constraint:** Idempotency locking via in-process concurrency controls requires running Uvicorn with `--workers 1`. A distributed locking mechanism (e.g. Redis) would be required for multi-worker production.
3. **Android Client Timeout:** If both RAG and primary Gemini generation timeout before Groq succeeds, total response time may reach 37–52 seconds. Ensure the Android OkHttp client timeout is set to at least 65 seconds to prevent premature client-side aborts during provider fallback.
