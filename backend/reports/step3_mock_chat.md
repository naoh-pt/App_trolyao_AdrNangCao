# Báo cáo thực hiện: Gửi Tin nhắn, Tích hợp Mock AI & Xử lý Idempotency (Milestone 3 - Thành viên C)

**Ngày thực hiện:** 02/10/2026  
**Thành viên đảm nhiệm:** Thành viên C (Backend & Lưu trữ)  
**Tài liệu kế hoạch tham chiếu:** `KE_HOACH_TRO_LY_AO_ANDROID-1.md` (giữ nguyên không sửa đổi)

---

## 1. Mục tiêu công việc của Milestone 3

Hoàn thành mốc kỹ thuật số 3 cho backend:
- Triển khai endpoint `POST /api/v1/conversations/{conversation_id}/messages` cho phép gửi tin nhắn và nhận phản hồi từ Mock AI.
- Tích hợp mô-đun Mock AI độc lập (`app.services.mock_ai`) với interface `generate_reply(context, message) -> (reply, emotion)`, trả về phản hồi tiếng Việt dự đoán được và biểu cảm hợp lệ (`neutral`, `happy`, `sad`, `surprised`).
- Truyền ngữ cảnh chứa tối đa 10 tin nhắn gần nhất của đúng cuộc trò chuyện (sắp xếp từ cũ đến mới), không lẫn lộn giữa các cuộc trò chuyện.
- Lưu trữ nguyên tử (atomic transaction) cả tin nhắn người dùng và tin nhắn trợ lý ảo trong SQLite, đồng thời cập nhật `updated_at` của cuộc trò chuyện.
- Đảm bảo tính lũy thỏa (idempotency):
  - Gửi lại cùng `request_id` và cùng nội dung tin nhắn sẽ trả về đúng cặp tin nhắn đã lưu ban đầu (cùng ID, cùng timestamp).
  - Gửi lại cùng `request_id` nhưng khác nội dung tin nhắn sẽ trả về lỗi HTTP 409 Conflict với mã lỗi `REQUEST_ID_CONFLICT`.
  - Không giữ khóa ghi SQLite trong lúc chờ phản hồi AI. Xử lý chính xác hai yêu cầu gần như đồng thời (race condition): chỉ 1 cặp được commit, yêu cầu kia sẽ đọc và trả về cặp đã commit.
- Giữ nguyên endpoint `GET /api/v1/health` (`{"status":"ok"}`), các endpoint CRUD đã có từ Milestone 2 và toàn bộ 12 test cases trước đó.

---

## 2. Danh sách tệp tin đã tạo và thay đổi

| Đường dẫn tệp | Trạng thái | Mô tả chi tiết |
| --- | --- | --- |
| `backend/app/services/__init__.py` | Tạo mới | Khởi tạo package dịch vụ `app.services`. |
| `backend/app/services/mock_ai.py` | Tạo mới | Mô-đun Mock AI độc lập triển khai interface `generate_reply(context, message) -> (reply, emotion)` với phản hồi tiếng Việt và các biểu cảm chuẩn. Hỗ trợ hook mô phỏng lỗi (503) và timeout (504) khi test. |
| `backend/app/exceptions.py` | Cập nhật | Bổ sung các ngoại lệ chuẩn: `InvalidMessageException` (400), `InvalidRequestIdException` (400), `RequestIdConflictException` (409), `LLMUnavailableException` (503), `LLMTimeoutException` (504). |
| `backend/app/db/connection.py` | Cập nhật | Bổ sung bảng `idempotency_records` với khóa chính `request_id`, khóa ngoại cascade theo `conversations` và `messages`. |
| `backend/app/schemas/conversation.py` | Cập nhật | Thêm `SendMessageRequest` và `SendMessageResponse` (chứa `user_message` và `assistant_message`). |
| `backend/app/api/v1/conversations.py` | Cập nhật | Cài đặt endpoint `POST /conversations/{id}/messages`, tích hợp xác thực, idempotency, gọi AI và atomic commit. Cập nhật deterministic tie-breaker `ORDER BY created_at ASC, rowid ASC` cho endpoint `GET messages`. |
| `backend/tests/test_messages.py` | Tạo mới | 11 bài kiểm thử tự động toàn diện cho Milestone 3. |
| `backend/README.md` | Cập nhật | Cập nhật tài liệu hướng dẫn gửi tin nhắn bằng PowerShell và giải thích cơ chế Idempotency. |
| `backend/reports/step3_mock_chat.md` | Tạo mới | Báo cáo chi tiết Milestone 3 (tệp này). |

---

## 3. Thay đổi Cơ sở dữ liệu (Database Schema)

Để hỗ trợ kiểm tra tính lũy thỏa (idempotency) và đảm bảo tính toàn vẹn dữ liệu khi cascade xóa, bảng `idempotency_records` được thêm vào SQLite:

```sql
CREATE TABLE IF NOT EXISTS idempotency_records (
    request_id TEXT PRIMARY KEY,
    client_id TEXT NOT NULL,
    conversation_id TEXT NOT NULL,
    normalized_message TEXT NOT NULL,
    user_message_id TEXT NOT NULL,
    assistant_message_id TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
    FOREIGN KEY (user_message_id) REFERENCES messages(id) ON DELETE CASCADE,
    FOREIGN KEY (assistant_message_id) REFERENCES messages(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_idempotency_lookup
    ON idempotency_records(client_id, conversation_id, request_id);
```

**Đặc điểm thiết kế:**
- `request_id` là `PRIMARY KEY`, đảm bảo ràng buộc duy nhất tuyệt đối ở cấp độ cơ sở dữ liệu.
- `FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE` đảm bảo khi xóa cuộc trò chuyện qua `DELETE /conversations/{id}`, toàn bộ bản ghi idempotency tương ứng sẽ được tự động dọn dẹp sạch sẽ.
- Lưu trữ `normalized_message` (tin nhắn đã được trim) để đối chiếu khi client gửi lại request.

---

## 4. Cơ chế Xử lý Idempotency & Xử lý Tranh chấp Đồng thời

Yêu cầu đề bài: *Không giữ write lock của SQLite khi đang gọi AI; nếu hai request đồng thời cùng gửi một request ID, chỉ một cặp được commit và request kia phải đọc lại cặp đã commit.*

### Quy trình triển khai:
1. **Kiểm tra nhanh trước khi gọi AI (Fast Path):**
   - Đọc bảng `idempotency_records` với `request_id`.
   - Nếu đã tồn tại:
     - Nếu `client_id` hoặc `conversation_id` không khớp: Trả về HTTP 409 Conflict.
     - Nếu `normalized_message` khớp: Đọc ngay cặp tin nhắn đã lưu (`user_message_id`, `assistant_message_id`) và trả về HTTP 200 ngay lập tức mà không gọi AI lần 2.
     - Nếu `normalized_message` không khớp: Trả về HTTP 409 Conflict (`REQUEST_ID_CONFLICT`).
2. **Gọi AI ngoài transaction (Non-blocking):**
   - Lấy ngữ cảnh 10 tin nhắn gần nhất.
   - Gọi `mock_ai.generate_reply(context, message)` hoàn toàn bên ngoài transaction SQLite, không giữ bất kỳ lock nào.
3. **Commit nguyên tử và bắt xung đột (Atomic Commit & Race Handling):**
   - Mở transaction `with db:`.
   - Lưu `user_message`, `assistant_message`, `idempotency_records` và cập nhật `updated_at` của cuộc trò chuyện.
   - Nếu có hai request gần như đồng thời cùng lọt qua bước 1 và gọi AI:
     - Request thứ nhất vào transaction và commit thành công.
     - Request thứ hai khi cố gắng chèn `request_id` vào `idempotency_records` sẽ bị kích hoạt `sqlite3.IntegrityError` (do vi phạm `PRIMARY KEY` duy nhất).
     - Khối `with db:` tự động rollback toàn bộ dữ liệu của request thứ hai (không để lại tin nhắn rác).
     - Khối `except sqlite3.IntegrityError:` của request thứ hai sẽ truy vấn lại bản ghi mà request thứ nhất vừa commit, đọc ra cặp tin nhắn chiến thắng và trả về cho client với mã HTTP 200.

---

## 5. Ví dụ Request / Response thực tế

### 5.1. Gửi tin nhắn thành công (`POST /api/v1/conversations/{id}/messages`)
- **Request:**
  ```http
  POST /api/v1/conversations/11800094-835f-4da4-a283-85efe1b1f398/messages HTTP/1.1
  Host: 127.0.0.1:8000
  X-Client-Id: 33333333-3333-4333-8333-333333333333
  Content-Type: application/json

  {
    "request_id": "44444444-4444-4444-8444-444444444444",
    "message": "Xin chao"
  }
  ```
- **Response (HTTP 200 OK):**
  ```json
  {
    "user_message": {
      "id": "63bd0c2f-9234-44d3-988a-b9a5ab0b7e2a",
      "role": "user",
      "text": "Xin chao",
      "emotion": null,
      "created_at": "2026-10-02T15:33:10Z"
    },
    "assistant_message": {
      "id": "f0d7b35f-6bea-4b66-b245-2cc0c0a18a87",
      "role": "assistant",
      "text": "Mình đã nhận được tin nhắn của bạn về 'Xin chao'. Mình sẵn sàng hỗ trợ bạn!",
      "emotion": "neutral",
      "created_at": "2026-10-02T15:33:10Z"
    }
  }
  ```

### 5.2. Thử lại cùng request ID (Idempotent Retry)
- **Request:** Gửi lại y hệt request trên.
- **Response (HTTP 200 OK):** Trả về đúng `user_message` (id: `63bd0c2f...`) và `assistant_message` (id: `f0d7b35f...`) với cùng timestamp. Số lượng bản ghi trong cơ sở dữ liệu không đổi.

### 5.3. Sử dụng lại request ID với nội dung khác
- **Request:** Gửi `request_id: 44444444-4444-4444-8444-444444444444` với nội dung `"Nội dung khác"`.
- **Response (HTTP 409 Conflict):**
  ```json
  {
    "error": {
      "code": "REQUEST_ID_CONFLICT",
      "message": "Request ID đã được sử dụng với nội dung tin nhắn khác"
    }
  }
  ```

### 5.4. Lỗi mô phỏng AI (503 / 504)
- Khi AI lỗi hoặc timeout, không có tin nhắn nào được ghi vào cơ sở dữ liệu:
  ```json
  {
    "error": {
      "code": "LLM_UNAVAILABLE",
      "message": "Không thể kết nối AI"
    }
  }
  ```

---

## 6. Kết quả Kiểm thử (Test Suite Results)

Lệnh thực thi toàn bộ test suite:
```powershell
.\.venv\Scripts\python.exe -m pytest -v
```

Kết quả: **23/23 bài kiểm thử ĐẠT (100% Passed)**:

| File kiểm thử | Bài kiểm thử | Mục đích kiểm tra | Kết quả |
| --- | --- | --- | --- |
| `test_conversations.py` | `test_health_check_preserved` | Giữ nguyên endpoint health | **PASSED** |
| `test_conversations.py` | `test_create_conversation_default_title` | Tạo hội thoại tiêu đề mặc định | **PASSED** |
| `test_conversations.py` | `test_create_conversation_custom_title` | Tạo hội thoại tiêu đề tùy chỉnh | **PASSED** |
| `test_conversations.py` | `test_missing_and_malformed_client_id` | Kiểm tra header X-Client-Id | **PASSED** |
| `test_conversations.py` | `test_malformed_conversation_id` | Kiểm tra UUID URL sai | **PASSED** |
| `test_conversations.py` | `test_list_conversations_ordered` | Sắp xếp updated_at giảm dần | **PASSED** |
| `test_conversations.py` | `test_client_isolation` | Cách ly dữ liệu 2 client | **PASSED** |
| `test_conversations.py` | `test_empty_messages_list` | Danh sách rỗng khi chưa có tin nhắn | **PASSED** |
| `test_conversations.py` | `test_messages_ordered_oldest_first` | Tin nhắn cũ nhất xếp trước | **PASSED** |
| `test_conversations.py` | `test_delete_conversation_and_cascade` | Xóa hội thoại cascade tin nhắn | **PASSED** |
| `test_conversations.py` | `test_404_behavior_nonexistent_uuid` | Trả về 404 NOT_FOUND | **PASSED** |
| `test_conversations.py` | `test_persistence_after_reopening_database` | Dữ liệu bền vững sau khi mở lại DB | **PASSED** |
| `test_messages.py` | `test_send_message_success` | Gửi tin nhắn thành công, nhận cặp tin nhắn hợp lệ | **PASSED** |
| `test_messages.py` | `test_message_ordering_and_tie_breaker` | Thứ tự tin nhắn chuẩn xác, user luôn trước assistant | **PASSED** |
| `test_messages.py` | `test_last_10_context` | Chỉ truyền tối đa 10 tin nhắn gần nhất làm ngữ cảnh cho AI | **PASSED** |
| `test_messages.py` | `test_repeated_request_id_idempotency` | Thử lại cùng request ID không chèn trùng dữ liệu | **PASSED** |
| `test_messages.py` | `test_same_request_id_different_text_conflict` | Dùng lại request ID với text khác trả về 409 Conflict | **PASSED** |
| `test_messages.py` | `test_near_simultaneous_retries` | Kiểm tra 2 luồng đồng thời: commit đúng 1 cặp | **PASSED** |
| `test_messages.py` | `test_another_clients_conversation` | Không gửi tin nhắn vào hội thoại của client khác (404) | **PASSED** |
| `test_messages.py` | `test_invalid_inputs` | Kiểm tra tin nhắn rỗng, > 2000 ký tự, thiếu request ID | **PASSED** |
| `test_messages.py` | `test_mock_failure_no_partial_save` | AI lỗi (503/504) không lưu tin nhắn nào | **PASSED** |
| `test_messages.py` | `test_persistence_after_reopening_sqlite` | Tin nhắn và idempotency tồn tại sau khi mở lại SQLite | **PASSED** |
| `test_messages.py` | `test_deletion_cascade_messages_and_idempotency` | Xóa hội thoại cascade xóa cả tin nhắn và idempotency | **PASSED** |

---

## 7. Vấn đề tồn đọng & Giao diện cho Thành viên D (LLM Integration)

- **Vấn đề tồn đọng trong Milestone 3:** Không có. Tất cả các yêu cầu về nghiệp vụ, hợp đồng API, tính lũy thỏa và kiểm thử đều hoàn tất 100%.
- **Bàn giao cho Thành viên D (Tích hợp LLM thực tế):**
  - Thành viên D chỉ cần thay thế hàm `generate_reply(context, message)` trong tệp [backend/app/services/mock_ai.py](file:///d:/nam5/semester_1/advance_android/troLyAo_ani/backend/app/services/mock_ai.py) (hoặc tạo file `ai_service.py` tương đương) bằng code gọi OpenAI API thực tế với `OPENAI_API_KEY` và `OPENAI_MODEL`.
  - Toàn bộ cơ chế kiểm tra ngữ cảnh 10 tin nhắn, lưu trữ SQLite, kiểm tra tính lũy thỏa và quản lý transaction của Thành viên C đã hoàn chỉnh và sẵn sàng vận hành.
