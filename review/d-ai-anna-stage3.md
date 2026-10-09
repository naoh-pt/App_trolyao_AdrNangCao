# D-AI Stage 3 — Anna Personality and Local Replies

## 1. Final verdict

READY FOR REVIEW

## 2. Branch and starting state

- Current branch: `fix/d-ai-demo-readiness`.
- Starting commit: `b4fc618 (HEAD -> fix/d-ai-demo-readiness, origin/fix/d-ai-demo-readiness) fix(backend): stabilize RAG demo flow and add tests`.
- Working tree at start: Clean with respect to tracked files; pre-existing untracked files (`android/`, `review/d-ai-branch-review.md`, `review/d-ui-rag-branch-review.md`) remained untouched.
- Initial test suite: 89 passing tests.

## 3. Scope implemented

1. **Anna Stable Personality & System Instruction**:
   - Centralized prompt in `app.services.personality` (`ANNA_SYSTEM_PROMPT`).
   - Defined Anna as a cheerful, playful, friendly young female assistant supporting student life and study at Học viện Kỹ thuật Mật mã (KMA).
   - Moderate response length guidance (2–5 Vietnamese sentences default).
   - Strict adherence to retrieved RAG facts for school rules, tuition, scholarships, and schedules without fabrication.
   - Forbids claiming device actions without tools, maintains safety boundaries, and acts supportively without claiming to be a doctor.
   - Preserved structured JSON contract: `{"reply": "...", "emotion": "..."}`.

2. **Emotion Rules & Normalization**:
   - Strictly mapped to the 4 allowed emotions compatible with Android: `neutral`, `happy`, `sad`, `surprised`.
   - Prevented leaking Android UI states (`idle`, `talk`, `thinking`) into backend emotions.
   - Safe normalization helper `normalize_emotion()` defaults unknown/invalid/missing emotions to `neutral` while normalizing valid case/whitespace variations.

3. **Deterministic Local Quick Replies**:
   - Implemented conservative intent matching in `app.services.quick_reply_service`.
   - 5 intent groups: Greeting, Thanks, Goodbye, Identity, Capabilities.
   - Bypasses RAG retrieval and Gemini generation while preserving request validation, conversation ownership, SQLite persistence, and `request_id` idempotency.

4. **Friendly Quota / Rate-limit Fallback**:
   - Implemented structured error classification `is_quota_exhausted_exception()` targeting HTTP 429 and `RESOURCE_EXHAUSTED` status codes/attributes.
   - Replaced generic failure on quota exhaustion with Anna's warm, supportive message:
     *"Anna đang tạm hết lượt trả lời từ dịch vụ AI mất rồi. Bạn chờ một chút rồi thử lại nhé — mình vẫn ở đây!"*
   - Returns emotion `sad`, empty sources `sources: []`, persists messages to SQLite, and maintains idempotent replay.
   - Distinguishes quota from timeouts (504), server unavailable (503), authentication (401/403), and unknown errors without exposing raw tracebacks.
   - Quota tests strictly use monkeypatching and fake exceptions; no magic user input string triggers test hooks in runtime code.

5. **Automated Offline Testing**:
   - 146 targeted Stage 3 tests across 3 new test modules.
   - Complete backend suite expanded from 89 to 235 passing tests (100% offline, 0 real provider calls).

## 4. Files changed

1. `backend/app/services/personality.py` (New):
   - Centralizes Anna's system prompt constant (`ANNA_SYSTEM_PROMPT`), allowed emotions (`ALLOWED_EMOTIONS`), quota fallback text (`ANNA_QUOTA_FALLBACK_TEXT`), fallback emotion (`ANNA_QUOTA_FALLBACK_EMOTION`), and `normalize_emotion()` helper.

2. `backend/app/services/quick_reply_service.py` (New):
   - Implements normalized input preprocessing and conservative anchored regex matching for greeting, thanks, goodbye, identity, and capabilities intents.
   - Defines fixed friendly responses and emotions for each intent without calling external models.

3. `backend/app/exceptions.py` (Modified):
   - Added `LLMQuotaExhaustedException(APIException)` mapped to HTTP 429 (`QUOTA_EXHAUSTED`).
   - Added `is_quota_exhausted_exception()` helper for robust, structured classification of HTTP 429, `RESOURCE_EXHAUSTED` status strings, and Google GenAI SDK `ClientError(429)`.

4. `backend/ai_service.py` (Modified):
   - Imported `ANNA_SYSTEM_PROMPT` and `normalize_emotion()` from `app.services.personality`.
   - Updated exception handling to intercept quota/rate-limit errors via `is_quota_exhausted_exception()` and raise `LLMQuotaExhaustedException`.
   - Improved timeout detection to recognize `TimeoutError` instances regardless of message string.
   - Replaced raw string exception logging with sanitized class names to prevent secret or trace leakage.

5. `backend/app/api/v1/conversations.py` (Modified):
   - Added quick-reply check prior to context fetching and generation; quick-reply hits skip context queries, RAG retrieval, and AI generation.
   - Added structured quota exception interception around AI generation to activate Anna's friendly quota fallback (`ANNA_QUOTA_FALLBACK_TEXT`, `sad`, `sources: []`).
   - Maintained unified SQLite transaction, idempotency record generation, and response construction.

6. `backend/tests/test_review_fixes.py` (Modified):
   - Updated `_send()` default test dummy message from `"hello"` to `"câu hỏi kiểm tra"` so that tests evaluating mock AI error/ordering handling are not intercepted by the new greeting quick reply.

7. `backend/tests/test_personality_prompt.py` (New):
   - Unit tests for Anna personality system instruction contents, emotion rules, and emotion normalization.

8. `backend/tests/test_quick_reply.py` (New):
   - Unit tests for all 5 intent groups, case variations, whitespace, punctuation stripping, negative boundary tests for long queries, academic questions, school questions, unknown queries, and route persistence/idempotency tests.

9. `backend/tests/test_quota_fallback.py` (New):
   - Offline unit and route tests verifying structured 429/RESOURCE_EXHAUSTED classification via monkeypatching and fake exceptions, quota fallback schema, SQLite persistence, idempotency replay, non-quota error containment, and regression test ensuring literal `__TEST_QUOTA__` text is treated as regular user input.

10. `review/d-ai-anna-stage3.md` (New):
    - Stage 3 implementation and verification report.

*(Note: `backend/app/services/mock_ai.py` was restored to its exact pre-Stage-3 state after removing temporary test hook logic, leaving zero modification in git).*

## 5. Anna personality specification

- **Name**: Anna.
- **Role**: Cheerful, friendly, supportive virtual assistant on Android for study and student life at Học viện Kỹ thuật Mật mã (KMA).
- **Tone & Persona**: Warm, empathetic, occasionally lighthearted; uses "Anna" or "mình" and addresses user as "bạn".
- **Response Length**: Moderate (typically 2–5 Vietnamese sentences); expands only when user explicitly asks for detailed step-by-step guidance.
- **Factual Grounding**: Strictly follows retrieved RAG facts for school regulations, tuition, scholarships, and schedules; never fabricates administrative rules.
- **Safety Boundaries**: No claims of device execution without tools; empathetic listening without claiming medical or psychological authority; refuses unsafe/illegal requests.
- **Response Format**: Strictly valid JSON: `{"reply": "...", "emotion": "neutral" | "happy" | "sad" | "surprised"}`.

## 6. Emotion mapping

The backend supports only 4 emotion values compatible with Android character rendering:

| Situation | Emotion |
|---|---|
| Normal study/help response, objective facts, standard explanation | `neutral` |
| Greeting, praise, encouragement, light humor, good news | `happy` |
| Empathy for user sadness/disappointment, AI service quota fallback | `sad` |
| Genuine surprise, unexpected discovery, fascinating facts | `surprised` |

- **Normalization rule**: Any missing, null, invalid, or unrecognized emotion safely normalizes to `neutral`.
- **UI states**: `idle`, `talk`, and `thinking` are Android UI rendering states and are strictly excluded from backend emotion output.

## 7. Quick-reply design

| Intent | Example inputs | Response emotion | Calls RAG | Calls AI |
|---|---|---|---|---|
| **Greeting** | `chào`, `xin chào`, `chào Anna`, `hello`, `hi`, `chào bạn nhé` | `happy` | No | No |
| **Thanks** | `cảm ơn`, `cám ơn`, `cảm ơn Anna`, `thank you`, `thanks`, `cảm ơn bạn nhiều` | `happy` | No | No |
| **Goodbye** | `tạm biệt`, `bye`, `goodbye`, `tạm biệt Anna`, `hẹn gặp lại` | `happy` | No | No |
| **Identity** | `bạn là ai`, `bạn tên gì`, `tên của bạn là gì`, `Anna là ai`, `cậu là ai` | `happy` | No | No |
| **Capabilities** | `bạn làm được gì`, `bạn có thể giúp gì`, `Anna giúp được gì`, `bạn biết làm gì` | `happy` | No | No |

**Conservative Matching Safeguards**:
- Matches are anchored to the entire message (`^...$`) after lowercasing, space collapsing, and trailing punctuation stripping.
- Longer queries containing greeting keywords (e.g., `"chào Anna cho mình hỏi phòng đào tạo ở đâu"`) do not match quick replies and proceed to full RAG/AI processing.
- Factual and school questions (e.g., `"Quy chế đào tạo của trường?"`) never match quick replies.

## 8. Quota fallback behavior

### Errors classified as quota (`is_quota_exhausted_exception() == True`):
- Custom `LLMQuotaExhaustedException`.
- HTTP status code `429` (via `status_code`, `code`, or `http_status` attributes on exception or attached response).
- Structured status string `RESOURCE_EXHAUSTED` (via `status` or `reason` attribute, or within `details["error"]` / `details["status"]`).
- Official Google GenAI SDK `ClientError(429, ...)`.

### Errors NOT classified as quota:
- Authentication & permission errors: HTTP 401, 403, `PERMISSION_DENIED`, `UNAUTHENTICATED`.
- Timeouts: `TimeoutError`, `LLMTimeoutException`, `DEADLINE_EXCEEDED` (mapped to HTTP 504).
- Generic server errors: HTTP 500, 502, 503 `UNAVAILABLE` (mapped to HTTP 503 `LLM_UNAVAILABLE`).
- JSON decode errors (mapped to HTTP 503 `LLM_UNAVAILABLE`).
- Arbitrary strings simply containing the word "quota" in an error message without structured attributes.

### Fallback response:
- Returns HTTP 200 with standard schema:
  `user_message`, `assistant_message` (`text`: *"Anna đang tạm hết lượt trả lời từ dịch vụ AI mất rồi. Bạn chờ một chút rồi thử lại nhé — mình vẫn ở đây!"*, `emotion`: `"sad"`), `sources: []`.
- Persists user and assistant messages in SQLite.
- Records idempotency record; retrying the same `request_id` returns the committed reply without calling AI.
- Tests simulate quota solely via monkeypatching `mock_ai.generate_reply` or raising `LLMQuotaExhaustedException`. Runtime code contains no magic strings or test hooks.

## 9. API and Android compatibility

- **Endpoints**: Zero changes to existing paths (`/api/v1/conversations`, `/api/v1/conversations/{id}/messages`).
- **Request DTOs**: Unaltered (`request_id: UUID`, `message: str`).
- **Response DTOs**: Unaltered (`user_message`, `assistant_message`, `sources`).
- **Emotion schema**: Android character animations consume only `neutral`, `happy`, `sad`, `surprised`; all are guaranteed valid.
- **Idempotency**: Fully preserved for normal generation, quick replies, and quota fallbacks.

## 10. Tests added

1. `backend/tests/test_personality_prompt.py` (28 tests):
   - Anna name, KMA school context, 2–5 sentence length, allowed emotions, JSON requirement, Android UI state prohibition, truthfulness rule, emotion normalization.
2. `backend/tests/test_quick_reply.py` (95 tests):
   - All 5 intent groups, case variations, whitespace, punctuation stripping, negative boundary tests for long queries, academic questions, school questions, unknown queries, and route persistence/idempotency tests.
3. `backend/tests/test_quota_fallback.py` (23 tests):
   - Structured 429 and `RESOURCE_EXHAUSTED` detection, fake SDK exception checks, negative non-quota checks, `ai_service` exception transformation, route quota fallback schema/persistence/replay, and regression test ensuring literal `__TEST_QUOTA__` is treated as ordinary user text.

## 11. Test results

### Targeted Stage 3 test run:
```powershell
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider tests/test_personality_prompt.py tests/test_quick_reply.py tests/test_quota_fallback.py
```
Result: **146 passed, 1 warning in 0.78s**

### Full backend test suite:
```powershell
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider tests
```
Result: **235 passed, 1 warning in 9.21s** (baseline was 89 passed; net +146 new passing tests, 0 failures, 0 skips).

### Syntax & compilation:
```powershell
.\.venv\Scripts\python.exe -m compileall -q app tests
```
Result: **Exit code 0** (no syntax or compilation errors).

### Git diff check:
```powershell
git diff --check
```
Result: **Exit code 0** (clean formatting, no trailing whitespace or conflict markers).

## 12. Remaining risks

1. **Quota fallback is persisted for the same `request_id`**: Because the quota fallback is successfully committed with its `request_id`, retrying with the same `request_id` will return the stored fallback message.
2. **Retrying after provider recovery requires a new `request_id`**: Once upstream quota is restored, the client must generate a new `request_id` to prompt the AI service again.
3. **Real provider behavior has not yet been tested**: All tests run offline with mocks and fake exceptions; live Gemini API behavior, latency, and upstream quota limits remain subject to network and API key conditions in live deployments.
4. **Multi-worker idempotency remains outside this stage**: Process-local request ownership (`request_guard`) enforces concurrency control within the single-worker demo constraint established in Stages 1–2.

## 13. Git status

```
 M backend/ai_service.py
 M backend/app/api/v1/conversations.py
 M backend/app/exceptions.py
 M backend/tests/test_review_fixes.py
?? android/
?? backend/app/services/personality.py
?? backend/app/services/quick_reply_service.py
?? backend/tests/test_personality_prompt.py
?? backend/tests/test_quick_reply.py
?? backend/tests/test_quota_fallback.py
?? review/d-ai-anna-stage3.md
?? review/d-ai-branch-review.md
?? review/d-ui-rag-branch-review.md
```

## 14. Recommended next step

- User review of Stage 3 report and code changes.
- Upon approval, commit Stage 3 changes to `fix/d-ai-demo-readiness`.
