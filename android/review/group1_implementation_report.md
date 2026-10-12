# Priority 1 Integration Fixes — Implementation Report

---

## 1. Executive Summary

This report documents the implementation and static verification of all Priority 1 integration fixes for the `VirtualAssistant` Android application. Key objectives accomplished include robust base URL normalization, safe Room database synchronization for empty server lists, deterministic message ordering for equal timestamps, persistence and header transmission of client IDs, duplicate request prevention with request ID handling, refined network/API error reporting in Vietnamese, and comprehensive static verification against the backend API contract. All added unit tests pass, and Gradle unit tests, assembleDebug, and lintDebug compile cleanly.

---

## 2. Files Changed

1. `app/build.gradle.kts`: Added `junit:junit:4.13.2` and `kotlinx-coroutines-test` for unit testing.
2. `app/src/main/java/com/example/assistant/data/local/SettingsStore.kt`: Implemented robust URL normalization logic and safe DataStore reading/writing.
3. `app/src/main/java/com/example/assistant/data/remote/ApiClient.kt`: Updated `forBase` to enforce URL normalization.
4. `app/src/main/java/com/example/assistant/data/local/Daos.kt`: Added `deleteAll()` to `ConversationDao` and added deterministic message ordering query to `MessageDao.observe`.
5. `app/src/main/java/com/example/assistant/data/repo/ChatRepository.kt`: Fixed Room synchronization for empty lists, refined error handling for specific IOExceptions and HTTP codes, and ensured base URL normalization on all API calls.
6. `app/src/main/java/com/example/assistant/ui/chat/ChatViewModel.kt`: Refined network error vs API error handling and request ID tracking.
7. `app/src/main/java/com/example/assistant/ui/settings/SettingsViewModel.kt`: Improved validation and feedback messages for backend settings.
8. `app/src/main/java/com/example/assistant/ui/history/HistoryViewModel.kt`: Guaranteed loading state reset in `finally` block.
9. `app/src/test/java/com/example/assistant/UnitTest.kt`: Added automated unit tests covering all required logic.
10. `review/group1_manual_test_checklist.md`: Created step-by-step manual test checklist.
11. `review/group1_implementation_report.md`: Created implementation report.

---

## 3. Base URL Behavior

Implemented `SettingsStore.normalize(raw: String): String?` with the following strict rules:
- Trims whitespace.
- Prepends `http://` if scheme (`http://` or `https://`) is absent.
- Strips trailing slashes.
- Strips trailing `/api/v1` (case-sensitively) if present.
- Ensures the URL terminates with exactly one trailing `/`.
- Validates URL syntax via `HttpUrl.toHttpUrlOrNull()` and verifies host non-emptiness.
- Rejects empty, whitespace-only, or malformed input with concise Vietnamese error feedback ("Địa chỉ backend không hợp lệ").

---

## 4. Room Synchronization Changes

- Handled empty lists in `refreshConversations()` and `refreshMessages(conversationId)`.
- When the server returns an empty conversation list (`items.isEmpty()`), the repository invokes `convDao.deleteAll()` inside a Room transaction.
- When the server returns an empty message list for a conversation (`items.isEmpty()`), the repository invokes `msgDao.deleteByConversation(conversationId)` inside a Room transaction.
- When non-empty, stale records outside `items.map { it.id }` are deleted via `deleteNotIn(...)`, and new items are upserted.
- All operations execute inside `db.withTransaction { ... }`.

---

## 5. Message-Ordering Changes

Updated the Room query in `MessageDao.observe`:
```sql
SELECT * FROM messages 
WHERE conversationId = :conversationId 
ORDER BY createdAt ASC, CASE WHEN role = 'user' THEN 0 ELSE 1 END ASC, id ASC
```
This guarantees that if a user message and assistant reply share the exact same backend timestamp (`createdAt`), the user message (`role = 'user'`) is always ordered before the assistant reply (`role = 'assistant'`).

---

## 6. Client ID Verification

- Verified `SettingsStore.clientId()` implementation:
  - Generates a UUID once per app installation.
  - Persists UUID in DataStore under `client_id` key.
  - Caches client ID in memory (`@Volatile cachedClientId`).
  - Reloads existing UUID from DataStore on app restarts.
  - Transmits UUID in header `X-Client-Id` across all protected endpoints (`conversations`, `messages`, `sendMessage`, `deleteConversation`, `createConversation`).

---

## 7. Request ID Verification

- Verified `ChatViewModel.send()` behavior:
  - Every new message assignment creates a new UUID `request_id`.
  - Rapid repeated taps are blocked synchronously by setting `sending = true` on main thread before launching sending coroutine.
  - Send button is disabled in UI while `sending` is `true` or offline.
  - Retrying a failed message retains its original `request_id` to prevent duplicate backend generation.
  - Starting a new message after success or clearing draft generates a brand-new `request_id`.
  - Coroutine cancellation (`CancellationException`) is explicitly rethrown in `ChatRepository`.

---

## 8. Network Error-Handling Changes

- Refined exception handling in `ChatRepository.call`:
  - `SocketTimeoutException` -> "Hết thời gian chờ phản hồi từ server (timeout)"
  - `ConnectException` -> "Không thể kết nối tới server (Connection refused). Kiểm tra xem backend đã chạy chưa."
  - `UnknownHostException` -> "Không tìm thấy địa chỉ server. Kiểm tra kết nối mạng hoặc IP backend."
  - Generic `IOException` -> "Không kết nối được tới server. Kiểm tra Wi-Fi và địa chỉ backend."
  - HTTP 400, 404, 409, 422, 500, 503, 504 mapped to Vietnamese messages, prioritizing structured error body `{ "error": { "code": "...", "message": "..." } }` when provided by backend.
  - Preserves local Room cache when network requests fail; does not wipe cache on network error.
  - Differentiates between offline/network errors and HTTP API responses (e.g. 500 error does not mark app offline).
  - Maintained HTTP read timeout at 45 seconds.

---

## 9. API Contract Verification

Validated Retrofit DTOs and endpoint signatures against backend contract:
- `GET /api/v1/health` -> `Response<HealthResponse>`
- `POST /api/v1/conversations` -> `Response<ConversationDto>`
- `GET /api/v1/conversations` -> `Response<ItemsResponse<ConversationDto>>`
- `GET /api/v1/conversations/{id}/messages` -> `Response<ItemsResponse<MessageDto>>`
- `POST /api/v1/conversations/{id}/messages` -> `Response<SendMessageResponse>` with `SendMessageRequest(request_id, message)`
- `DELETE /api/v1/conversations/{id}` -> `Response<Unit>` (handles HTTP 204 No Content)
- `Emotion.from(value)` handles `neutral`, `happy`, `sad`, `surprised`, and falls back to `NEUTRAL` for unknown or null strings.

---

## 10. Tests Added

Added 7 unit tests in `app/src/test/java/com/example/assistant/UnitTest.kt`:
1. `testBaseUrlNormalization`: Validates normalization rules.
2. `testBaseUrlRejection`: Validates rejection of invalid inputs.
3. `testEmotionFallback`: Validates fallback to `NEUTRAL`.
4. `testDeterministicMessageOrdering`: Validates user message comes before assistant response on equal timestamps.
5. `testEmptyListSynchronizationLogic`: Validates empty list clears local cache logic.
6. `testClientIdCreationLogic`: Validates client ID persistence logic.
7. `testRequestIdGenerationAndRetryLogic`: Validates request ID creation for new messages and reuse for retries.

---

## 11. Commands Executed and Results

1. Unit Tests:
   Command: `gradle_build("testDebugUnitTest")`
   Result: **BUILD SUCCESSFUL** (7 passed, 0 failed, 0 skipped)

2. Assemble Debug APK:
   Command: `gradle_build("app:assembleDebug")`
   Result: **BUILD SUCCESSFUL**

3. Lint Check:
   Command: `gradle_build("app:lintDebug")`
   Result: **BUILD SUCCESSFUL**

---

## 12. Items Requiring Physical Phone / Live Backend

- Live socket communication with physical laptop IP address on Wi-Fi network.
- End-to-end latency measurement during LLM streaming/response.
- Physical device screen rendering and keyboard IME layout transitions.

---

## 13. Known Limitations

- Offline support allows viewing existing cached chats from Room, but sending new messages requires an active backend connection.
- Retrying an un-sent message reuses the original `request_id`; if the user chooses "Sửa tin nhắn" (edit pending draft), sending the modified draft generates a new `request_id`.

---

## 14. Final Verdict

**`READY FOR MANUAL END-TO-END TEST`**
