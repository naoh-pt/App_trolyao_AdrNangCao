# Báo cáo thực hiện: Lưu trữ SQLite & Quản lý Hội thoại (Milestone 2 - Thành viên C)

**Ngày thực hiện:** 02/10/2026  
**Thành viên đảm nhiệm:** Thành viên C (Backend & Lưu trữ)  
**Tài liệu kế hoạch tham chiếu:** `KE_HOACH_TRO_LY_AO_ANDROID-1.md` (giữ nguyên không sửa đổi)

---

## 1. Mục tiêu công việc của Milestone 2

Hoàn thành mốc kỹ thuật số 2 cho backend:
- Tích hợp SQLite lưu trữ dạng tệp tin bên trong `backend/` (`backend/tro_ly_ao.db`), được loại trừ tự động qua `.gitignore` (`*.db`). Dữ liệu tồn tại bền vững sau khi khởi động lại server.
- Xây dựng schema bảng `conversations` và `messages` có liên kết khóa ngoại (`FOREIGN KEY ... ON DELETE CASCADE`), bật `PRAGMA foreign_keys = ON;` và `PRAGMA journal_mode = WAL;`.
- Triển khai đầy đủ các endpoint theo quy chuẩn API:
  - `POST /api/v1/conversations`: Kiểm tra `X-Client-Id` (UUID), sinh UUID server, lưu vào DB và trả về `id`, `title`, `created_at`, `updated_at`.
  - `GET /api/v1/conversations`: Kiểm tra `X-Client-Id` (UUID), trả về `{"items":[...]}` chỉ chứa hội thoại của client đó, sắp xếp theo `updated_at` giảm dần.
  - `GET /api/v1/conversations/{id}/messages`: Kiểm tra `X-Client-Id`, trả về `{"items":[]}` với hội thoại chưa có tin nhắn, định dạng model sẵn sàng cho tin nhắn (`id`, `role`, `text`, `emotion`, `created_at`) sắp xếp theo thời gian cũ nhất trước. Trả về 404 nếu không tìm thấy hoặc thuộc client khác.
  - `DELETE /api/v1/conversations/{id}`: Kiểm tra `X-Client-Id`, xóa hội thoại và cascade xóa các tin nhắn liên quan, trả về HTTP 204. Trả về 404 nếu không tìm thấy hoặc thuộc client khác.
- Chuẩn hóa định dạng lỗi: `{"error":{"code":"...","message":"..."}}`. Tuyệt đối không để lộ traceback.
- Định dạng thời gian: Chuẩn UTC ISO 8601 với hậu tố `Z` (ví dụ: `2026-10-02T15:20:00Z`).
- Giữ nguyên endpoint `GET /api/v1/health` trả về đúng `{"status":"ok"}`.
- Xây dựng bộ test tự động toàn diện với cơ sở dữ liệu tạm cô lập, không ảnh hưởng cơ sở dữ liệu phát triển.

---

## 2. Danh sách tệp tin đã tạo và cập nhật

| Đường dẫn tệp | Trạng thái | Mô tả chi tiết |
| --- | --- | --- |
| `backend/app/config.py` | Tạo mới | Cấu hình đường dẫn cơ sở dữ liệu `DATABASE_PATH` và hỗ trợ biến môi trường `SQLITE_DB_PATH`. |
| `backend/app/exceptions.py` | Tạo mới | Định nghĩa cấu trúc lỗi chuẩn `{"error":{"code":...,"message":...}}`, các lớp ngoại lệ `InvalidClientIdException`, `InvalidIdException`, `ConversationNotFoundException` và handler xử lý ngoại lệ ngăn chặn rò rỉ traceback. |
| `backend/app/utils/time.py` | Tạo mới | Tiện ích `utc_now_iso()` sinh chuỗi thời gian chuẩn UTC ISO 8601 kết thúc bằng `Z`. |
| `backend/app/db/__init__.py` | Tạo mới | Khởi tạo package `app.db`. |
| `backend/app/db/connection.py` | Tạo mới | Quản lý kết nối SQLite, kích hoạt `foreign_keys`, chế độ `WAL`, thiết lập `row_factory = sqlite3.Row`, khởi tạo bảng và cung cấp dependency `get_db()`. |
| `backend/app/schemas/__init__.py` | Tạo mới | Khởi tạo package `app.schemas`. |
| `backend/app/schemas/conversation.py` | Tạo mới | Khai báo các Pydantic models: `ConversationCreate`, `ConversationResponse`, `ConversationListResponse`, `MessageResponse`, `MessageListResponse`, `ErrorResponse`. |
| `backend/app/api/dependencies.py` | Tạo mới | Dependencies kiểm tra tính hợp lệ của UUID trong header `X-Client-Id` và path parameter `conversation_id`. |
| `backend/app/api/v1/conversations.py` | Tạo mới | Xử lý logic 4 endpoints quản lý hội thoại (`POST`, `GET`, `GET messages`, `DELETE`). |
| `backend/app/main.py` | Cập nhật | Bổ sung lifespan khởi tạo DB, gắn các exception handlers, đăng ký `conversations_router` vào prefix `/api/v1`. |
| `backend/requirements.txt` | Cập nhật | Bổ sung thư viện cho test: `pytest>=8.0.0,<9.0.0` và `httpx>=0.27.0,<1.0.0`. |
| `backend/tests/__init__.py` | Tạo mới | Khởi tạo package `tests`. |
| `backend/tests/conftest.py` | Tạo mới | Cấu hình fixtures cho pytest, tạo file SQLite tạm thời độc lập cho từng phiên test, override dependency `get_db` để bảo vệ database phát triển. |
| `backend/tests/test_conversations.py` | Tạo mới | 12 ca kiểm thử tự động kiểm tra đầy đủ mọi hành vi nghiệp vụ và bảo mật cách ly. |
| `backend/README.md` | Cập nhật | Cập nhật hướng dẫn chạy test, khởi động server và các ví dụ gọi API bằng PowerShell / curl. |
| `backend/reports/step2_conversations.md` | Tạo mới | Báo cáo chi tiết Milestone 2 (tệp này). |

---

## 3. Cấu trúc Cơ sở dữ liệu (SQLite Schema)

Cơ sở dữ liệu được tạo tự động khi ứng dụng khởi chạy (`init_db`) với 2 bảng liên kết:

```sql
-- 1. Bảng quản lý cuộc trò chuyện
CREATE TABLE IF NOT EXISTS conversations (
    id TEXT PRIMARY KEY,
    client_id TEXT NOT NULL,
    title TEXT NOT NULL DEFAULT 'Cuộc trò chuyện mới',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- Chỉ mục tối ưu truy vấn danh sách hội thoại theo client và thời gian cập nhật
CREATE INDEX IF NOT EXISTS idx_conversations_client_updated
    ON conversations(client_id, updated_at DESC);

-- 2. Bảng quản lý tin nhắn (chuẩn bị sẵn cho Milestone 3)
CREATE TABLE IF NOT EXISTS messages (
    id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL,
    role TEXT NOT NULL,
    text TEXT NOT NULL,
    emotion TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
);

-- Chỉ mục tối ưu truy vấn tin nhắn theo thứ tự thời gian tăng dần
CREATE INDEX IF NOT EXISTS idx_messages_conv_created
    ON messages(conversation_id, created_at ASC);
```

**Cơ chế bảo vệ dữ liệu:**
- Khóa ngoại `FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE` được kích hoạt thông qua `PRAGMA foreign_keys = ON;` trên mọi kết nối. Khi xóa cuộc trò chuyện, toàn bộ tin nhắn liên quan sẽ tự động được xóa sạch.
- Định dạng khóa chính `id` và `client_id` là UUID string.
- Thời gian lưu trữ dưới dạng chuỗi ISO 8601 UTC kết thúc bằng `Z`.

---

## 4. Ví dụ Request / Response thực tế từ Endpoints

### 4.1. Kiểm tra sức khỏe (`GET /api/v1/health`)
- **Request:**
  ```http
  GET /api/v1/health HTTP/1.1
  Host: 127.0.0.1:8000
  ```
- **Response (HTTP 200 OK):**
  ```json
  {"status":"ok"}
  ```

### 4.2. Tạo cuộc trò chuyện mới (`POST /api/v1/conversations`)
- **Request:**
  ```http
  POST /api/v1/conversations HTTP/1.1
  Host: 127.0.0.1:8000
  X-Client-Id: 11111111-1111-4111-8111-111111111111
  Content-Type: application/json

  {"title": "Kế hoạch tuần này"}
  ```
- **Response (HTTP 200 OK):**
  ```json
  {
    "id": "9156ae5b-2ca5-4f7a-8d66-29e77b03d828",
    "title": "Kế hoạch tuần này",
    "created_at": "2026-10-02T15:17:38Z",
    "updated_at": "2026-10-02T15:17:38Z"
  }
  ```

### 4.3. Lấy danh sách cuộc trò chuyện (`GET /api/v1/conversations`)
- **Request:**
  ```http
  GET /api/v1/conversations HTTP/1.1
  Host: 127.0.0.1:8000
  X-Client-Id: 11111111-1111-4111-8111-111111111111
  ```
- **Response (HTTP 200 OK):**
  ```json
  {
    "items": [
      {
        "id": "9156ae5b-2ca5-4f7a-8d66-29e77b03d828",
        "title": "Kế hoạch tuần này",
        "created_at": "2026-10-02T15:17:38Z",
        "updated_at": "2026-10-02T15:17:38Z"
      }
    ]
  }
  ```

### 4.4. Lấy tin nhắn của cuộc trò chuyện chưa có tin nhắn (`GET /api/v1/conversations/{id}/messages`)
- **Request:**
  ```http
  GET /api/v1/conversations/9156ae5b-2ca5-4f7a-8d66-29e77b03d828/messages HTTP/1.1
  Host: 127.0.0.1:8000
  X-Client-Id: 11111111-1111-4111-8111-111111111111
  ```
- **Response (HTTP 200 OK):**
  ```json
  {
    "items": []
  }
  ```

### 4.5. Xóa cuộc trò chuyện (`DELETE /api/v1/conversations/{id}`)
- **Request:**
  ```http
  DELETE /api/v1/conversations/9156ae5b-2ca5-4f7a-8d66-29e77b03d828 HTTP/1.1
  Host: 127.0.0.1:8000
  X-Client-Id: 11111111-1111-4111-8111-111111111111
  ```
- **Response (HTTP 204 No Content):** Không có nội dung trả về.

### 4.6. Phản hồi lỗi khi thiếu hoặc sai `X-Client-Id`
- **Request:**
  ```http
  POST /api/v1/conversations HTTP/1.1
  Host: 127.0.0.1:8000
  ```
- **Response (HTTP 400 Bad Request):**
  ```json
  {
    "error": {
      "code": "INVALID_CLIENT_ID",
      "message": "Header X-Client-Id là bắt buộc"
    }
  }
  ```

### 4.7. Phản hồi lỗi khi truy cập cuộc trò chuyện của Client khác (hoặc không tồn tại)
- **Request:**
  ```http
  GET /api/v1/conversations/9156ae5b-2ca5-4f7a-8d66-29e77b03d828/messages HTTP/1.1
  Host: 127.0.0.1:8000
  X-Client-Id: 22222222-2222-4222-8222-222222222222
  ```
- **Response (HTTP 404 Not Found):**
  ```json
  {
    "error": {
      "code": "NOT_FOUND",
      "message": "Cuộc trò chuyện không tồn tại"
    }
  }
  ```

---

## 5. Kết quả Kiểm thử (Test Suite & Live Verification)

### 5.1. Kiểm thử tự động với Pytest

Lệnh thực thi:
```powershell
.\.venv\Scripts\python.exe -m pytest -v
```

Kết quả: **12/12 bài kiểm thử ĐẠT (100% Passed)**:

| Tên bài test | Nội dung kiểm tra | Kết quả |
| --- | --- | --- |
| `test_health_check_preserved` | Đảm bảo `GET /api/v1/health` tiếp tục trả về `{"status":"ok"}` HTTP 200 | **PASSED** |
| `test_create_conversation_default_title` | Tạo chat với tiêu đề mặc định `"Cuộc trò chuyện mới"`, UUID hợp lệ, timestamp kết thúc bằng `Z` | **PASSED** |
| `test_create_conversation_custom_title` | Tạo chat với tiêu đề tùy chỉnh | **PASSED** |
| `test_missing_and_malformed_client_id` | Thiếu hoặc sai định dạng header `X-Client-Id` trả về HTTP 400 `INVALID_CLIENT_ID` | **PASSED** |
| `test_malformed_conversation_id` | ID hội thoại trong đường dẫn không phải UUID trả về HTTP 400 `INVALID_ID` | **PASSED** |
| `test_list_conversations_ordered` | Danh sách hội thoại sắp xếp theo `updated_at` giảm dần (mới nhất lên đầu) | **PASSED** |
| `test_client_isolation` | Tính cô lập: Client A không thấy, không đọc và không xóa được hội thoại của Client B (trả về 404) | **PASSED** |
| `test_empty_messages_list` | Hội thoại mới tạo trả về `{"items": []}` | **PASSED** |
| `test_messages_ordered_oldest_first` | Kiểm tra schema và thứ tự tin nhắn theo thời gian tăng dần (`ASC`) | **PASSED** |
| `test_delete_conversation_and_cascade` | Xóa hội thoại trả về 204 và cascade xóa sạch tin nhắn trong bảng `messages` | **PASSED** |
| `test_404_behavior_nonexistent_uuid` | UUID không tồn tại trả về HTTP 404 `NOT_FOUND` | **PASSED** |
| `test_persistence_after_reopening_database` | Dữ liệu SQLite tồn tại bền vững sau khi đóng và mở lại kết nối | **PASSED** |

### 5.2. Kiểm thử thực tế trên máy chủ sống (Live Server Verification)

Đã khởi động server thực tế bằng:
```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```
- Gọi thực tế qua `curl.exe` và `Invoke-RestMethod`.
- Kiểm thử lưu trữ bền vững: Tạo cuộc trò chuyện, tắt hoàn toàn tiến trình server, khởi động lại server trên port 8000, gọi `GET /api/v1/conversations` kiểm tra -> Dữ liệu hội thoại vẫn được đọc ra nguyên vẹn từ tệp `tro_ly_ao.db`.

---

## 6. Vấn đề tồn đọng & Kế hoạch Milestone 3

- **Vấn đề tồn đọng:** Không có. Tất cả yêu cầu của Milestone 2 đã hoàn thành trọn vẹn, không có lỗi tiềm ẩn.
- **Sẵn sàng cho Milestone 3:**
  - Bảng `messages` đã được tạo sẵn cấu trúc và liên kết khóa ngoại.
  - Endpoint gửi tin nhắn `POST /api/v1/conversations/{id}/messages` sẽ được triển khai trong Milestone 3 cùng với việc tích hợp dịch vụ AI (Mock AI hoặc LLM).
