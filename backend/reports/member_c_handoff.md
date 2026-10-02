# Tài liệu Bàn giao Kỹ thuật Backend (Dành cho Thành viên A và Thành viên D)

**Người lập:** Thành viên C (Backend & Lưu trữ)  
**Ngày bàn giao:** 02/10/2026  
**Dự án:** Trợ lý ảo Android với nhân vật 2D (`troLyAo_ani`)  
**Tài liệu tham chiếu:** `KE_HOACH_TRO_LY_AO_ANDROID-1.md`  
**Trạng thái backend:** Đã hoàn thành toàn diện Milestones 1, 2 và 3. Sẵn sàng tích hợp.

---

## 1. Hướng dẫn Khởi chạy Server trên Laptop Windows

Thành viên A (hoặc bất kỳ ai chạy demo) có thể khởi chạy server backend trên Windows như sau:

```powershell
# 1. Di chuyển vào thư mục backend
cd d:\nam5\semester_1\advance_android\troLyAo_ani\backend

# 2. Cài đặt thư viện (nếu chưa cài)
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

# 3. Khởi chạy server FastAPI lắng nghe trên tất cả card mạng
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Địa chỉ kết nối từ Client:
- **Từ trình duyệt/Postman trên laptop:** `http://127.0.0.1:8000` (hoặc `http://localhost:8000`)
- **Tài liệu Swagger UI:** `http://127.0.0.1:8000/docs`
- **Từ Android Studio Emulator:** `http://10.0.2.2:8000/api/v1`
- **Từ điện thoại Android thật (chung Wi-Fi):** `http://<IP_LAN_CUA_LAPTOP>:8000/api/v1`  
  *(Kiểm tra IP laptop bằng `ipconfig` trong PowerShell. Mở cổng 8000 trên Windows Firewall nếu điện thoại không kết nối được).*

---

## 2. Hướng dẫn Tích hợp dành cho Thành viên A (Android Core & UI)

### 2.1. Quy chuẩn chung
1. **Base URL:** `http://<server-ip>:8000/api/v1`
2. **Header bắt buộc:**
   - Mọi request nghiệp vụ (tạo chat, lấy danh sách, gửi tin, lấy tin, xóa chat) **bắt buộc** phải gửi kèm header:
     ```http
     X-Client-Id: <UUID>
     ```
   - `client_id` cần được sinh một lần bằng `UUID.randomUUID().toString()` khi app mở lần đầu và lưu vào DataStore.
   - Endpoint kiểm tra kết nối `/health` không yêu cầu header này.
3. **Định dạng dữ liệu:** `Content-Type: application/json`.
4. **Định dạng thời gian:** Chuỗi ISO 8601 UTC với hậu tố `Z` (ví dụ: `2026-10-02T15:30:00Z`).

### 2.2. Quy tắc sinh và tái sử dụng `request_id` (Idempotency)
- **Khi gửi tin nhắn mới:** Mỗi khi người dùng bấm "Gửi", Android sinh một `request_id` ngẫu nhiên mới: `UUID.randomUUID().toString()`.
- **Khi mạng gặp sự cố / Timeout:**
  - Nếu Android gửi tin nhắn mà bị timeout hoặc mất kết nối mạng và người dùng bấm **"Thử lại" (Retry)**:
  - **Android PHẢI giữ nguyên `request_id` cũ** và **nội dung tin nhắn cũ**, tuyệt đối không sinh `request_id` mới.
  - Backend đã cài đặt cơ chế Idempotency: Khi nhận lại cùng `request_id`, backend sẽ không chèn tin nhắn kép vào database mà trả về đúng cặp tin nhắn cũ (cùng `id`, cùng `created_at`, cùng câu trả lời).
  - **Lưu ý:** Nếu gửi lại cùng `request_id` nhưng nội dung tin nhắn bị thay đổi, server sẽ trả về lỗi `HTTP 409 Conflict`.

### 2.3. Danh sách Endpoints và Ví dụ JSON

#### 1. Kiểm tra kết nối (`GET /api/v1/health`)
- Không cần header `X-Client-Id`.
- **Response HTTP 200:**
  ```json
  {"status":"ok"}
  ```

#### 2. Tạo cuộc trò chuyện mới (`POST /conversations`)
- **Headers:** `X-Client-Id: <UUID>`
- **Body (Tùy chọn):** `{}` hoặc `{"title": "Tiêu đề tùy chọn"}` (mặc định là `"Cuộc trò chuyện mới"`).
- **Response HTTP 200:**
  ```json
  {
    "id": "e2a39a7b-3b6b-4e94-a14a-81a1727ea1a0",
    "title": "Cuộc trò chuyện mới",
    "created_at": "2026-10-02T15:20:00Z",
    "updated_at": "2026-10-02T15:20:00Z"
  }
  ```

#### 3. Lấy danh sách cuộc trò chuyện (`GET /conversations`)
- **Headers:** `X-Client-Id: <UUID>`
- Chỉ trả về hội thoại thuộc client đó, sắp xếp theo `updated_at` mới nhất lên đầu.
- **Response HTTP 200:**
  ```json
  {
    "items": [
      {
        "id": "e2a39a7b-3b6b-4e94-a14a-81a1727ea1a0",
        "title": "Cuộc trò chuyện mới",
        "created_at": "2026-10-02T15:20:00Z",
        "updated_at": "2026-10-02T15:20:00Z"
      }
    ]
  }
  ```

#### 4. Lấy lịch sử tin nhắn của cuộc trò chuyện (`GET /conversations/{id}/messages`)
- **Headers:** `X-Client-Id: <UUID>`
- Trả về tin nhắn theo thứ tự cũ nhất trước (`ASC`). Nếu timestamp bằng nhau, tin nhắn người dùng luôn đứng trước câu trả lời của trợ lý ảo.
- **Response HTTP 200 (khi chưa có tin nhắn):**
  ```json
  {"items": []}
  ```
- **Response HTTP 200 (khi đã có tin nhắn):**
  ```json
  {
    "items": [
      {
        "id": "718a0d38-dafc-42bb-b72d-1733ee467ed7",
        "role": "user",
        "text": "Xin chào",
        "emotion": null,
        "created_at": "2026-10-02T15:30:00Z"
      },
      {
        "id": "71f955ed-a03d-4f34-b7dd-7f345e4940c8",
        "role": "assistant",
        "text": "Chào bạn! Rất vui được gặp bạn hôm nay. Mình có thể giúp gì cho bạn?",
        "emotion": "happy",
        "created_at": "2026-10-02T15:30:00Z"
      }
    ]
  }
  ```

#### 5. Gửi tin nhắn và nhận phản hồi AI (`POST /conversations/{id}/messages`)
- **Headers:** `X-Client-Id: <UUID>`
- **Body:**
  ```json
  {
    "request_id": "c6b840e2-6325-4c07-84eb-9d62057d5440",
    "message": "Xin chào"
  }
  ```
- **Response HTTP 200:**
  ```json
  {
    "user_message": {
      "id": "718a0d38-dafc-42bb-b72d-1733ee467ed7",
      "role": "user",
      "text": "Xin chào",
      "emotion": null,
      "created_at": "2026-10-02T15:30:00Z"
    },
    "assistant_message": {
      "id": "71f955ed-a03d-4f34-b7dd-7f345e4940c8",
      "role": "assistant",
      "text": "Chào bạn! Rất vui được gặp bạn hôm nay. Mình có thể giúp gì cho bạn?",
      "emotion": "happy",
      "created_at": "2026-10-02T15:30:00Z"
    }
  }
  ```
  *(Các giá trị emotion có thể trả về: `"neutral"`, `"happy"`, `"sad"`, `"surprised"`. Android UI dùng giá trị này để chuyển ảnh biểu cảm nhân vật).*

#### 6. Xóa cuộc trò chuyện (`DELETE /conversations/{id}`)
- **Headers:** `X-Client-Id: <UUID>`
- Xóa cuộc trò chuyện và cascade xóa toàn bộ tin nhắn.
- **Response HTTP 204 No Content** (không có body).

---

## 3. Bảng Mã Lỗi Chuẩn (Error Responses)

Tất cả các phản hồi lỗi từ server đều tuân theo đúng cấu trúc JSON:
```json
{
  "error": {
    "code": "<ERROR_CODE>",
    "message": "<Mô tả lỗi dễ hiểu>"
  }
}
```

| HTTP Status | Mã lỗi (`code`) | Tình huống xảy ra | Hành động phía Android |
| --- | --- | --- | --- |
| **400** | `INVALID_CLIENT_ID` | Thiếu hoặc header `X-Client-Id` không đúng chuẩn UUID. | Kiểm tra hàm sinh UUID trong DataStore. |
| **400** | `INVALID_ID` | ID hội thoại trên URL không phải là UUID. | Kiểm tra navigation parameter. |
| **400** | `INVALID_REQUEST_ID` | `request_id` trong body thiếu hoặc không phải UUID. | Đảm bảo sinh `UUID.randomUUID()`. |
| **400** | `INVALID_MESSAGE` | Nội dung tin nhắn để trống hoặc vượt quá 2000 ký tự. | Validate ô nhập tin nhắn trên UI trước khi gửi. |
| **400** | `BAD_REQUEST` | Cấu trúc JSON bị sai cú pháp. | Kiểm tra Retrofit serializer. |
| **404** | `NOT_FOUND` | Hội thoại không tồn tại hoặc thuộc client khác. | Quay về màn hình danh sách hội thoại. |
| **409** | `REQUEST_ID_CONFLICT` | Tái sử dụng `request_id` cũ nhưng đổi nội dung tin nhắn. | Sinh `request_id` mới khi gửi câu hỏi mới. |
| **503** | `LLM_UNAVAILABLE` | Lỗi dịch vụ AI (không kết nối được AI). | Báo lỗi và cho phép người dùng bấm "Thử lại". |
| **504** | `LLM_TIMEOUT` | Yêu cầu AI quá thời gian chờ (timeout). | Báo lỗi và cho phép người dùng bấm "Thử lại". |

---

## 4. Hướng dẫn Tích hợp dành cho Thành viên D (LLM Integration)

Thành viên D phụ trách thay thế Mock AI bằng dịch vụ OpenAI API thực tế. Toàn bộ hạ tầng lưu trữ SQLite, ngữ cảnh, giao dịch nguyên tử và Idempotency đã được Thành viên C hoàn thiện.

### 4.1. Vị trí mô-đun cần can thiệp
Tệp tin: `backend/app/services/mock_ai.py` (hoặc tạo `backend/app/services/ai_service.py` và cập nhật import tương ứng trong `backend/app/api/v1/conversations.py`).

### 4.2. Interface chính xác cần triển khai
```python
def generate_reply(context: List[Dict[str, Any]], message: str) -> Tuple[str, str]:
    """
    Args:
        context: Danh sách tối đa 10 tin nhắn gần nhất trong cùng cuộc trò chuyện,
                 được sắp xếp theo thứ tự thời gian từ cũ nhất đến mới nhất.
                 Mỗi phần tử là một dict:
                 {
                     "role": "user" | "assistant",
                     "text": "Nội dung tin nhắn",
                     "emotion": Optional[str]
                 }
        message: Chuỗi văn bản tin nhắn hiện tại của người dùng (đã được trim).

    Returns:
        Tuple[str, str]: (reply_text, emotion)
        Trong đó:
        - reply_text: Chuỗi câu trả lời tiếng Việt từ LLM.
        - emotion: Chuỗi thuộc tập giá trị bắt buộc: {"neutral", "happy", "sad", "surprised"}.
                   Nếu LLM trả về giá trị lạ hoặc thiếu, Member D chuẩn hóa về "neutral".

    Exceptions cần ném ra (để backend trả về mã lỗi HTTP chuẩn):
        - Ném `LLMUnavailableException` khi lỗi API key, lỗi mạng, hoặc HTTP 5xx từ OpenAI (sẽ trả về HTTP 503).
        - Ném `LLMTimeoutException` khi quá thời gian chờ (ví dụ quá 30 giây) (sẽ trả về HTTP 504).
    """
```

### 4.3. Quản lý Khóa API & Biến môi trường
- Tạo tệp `.env` tại thư mục `backend/` (đã được loại trừ bởi `.gitignore`, không bao giờ commit).
- Tạo tệp `.env.example` với nội dung mẫu:
  ```env
  OPENAI_API_KEY=your_openai_api_key_here
  OPENAI_MODEL=gpt-4o-mini
  ```
- Dùng `python-dotenv` hoặc đọc biến môi trường qua `os.getenv("OPENAI_API_KEY")`.

---

## 5. Báo cáo Kết quả Xác minh Kỹ thuật

Hệ thống đã trải qua hai hình thức kiểm thử độc lập:

### 5.1. Xác minh Thực tế qua HTTP (Live Server Verification)
Đã khởi động máy chủ Uvicorn trên `http://0.0.0.0:8000` và thực hiện chuỗi lệnh HTTP thực tế:
1. `GET /api/v1/health` -> Trả về HTTP 200 `{"status":"ok"}`.
2. `POST /api/v1/conversations` -> Tạo thành công hội thoại với UUID hợp lệ và timestamp UTC kết thúc bằng `Z`.
3. `POST /api/v1/conversations/{id}/messages` -> Gửi tin nhắn `"Xin chào trợ lý ảo"`, nhận về HTTP 200 với đầy đủ `user_message` và `assistant_message` (`emotion: "happy"`).
4. `POST /api/v1/conversations/{id}/messages` (Idempotent Retry) -> Gửi lại đúng `request_id` đó; server trả về chính xác cặp tin nhắn cũ (cùng ID tin nhắn, cùng timestamp).
5. `POST /api/v1/conversations/{id}/messages` (Conflict) -> Gửi lại `request_id` đó với nội dung tin nhắn khác; server trả về chính xác HTTP 409 Conflict với body: `{"error":{"code":"REQUEST_ID_CONFLICT","message":"..."}}`.
6. `GET /api/v1/conversations/{id}/messages` -> Xác nhận trong database chỉ tồn tại duy nhất 2 tin nhắn (1 user, 1 assistant), không có tin nhắn rác hoặc bản sao trùng lặp.
7. `GET /api/v1/conversations` -> Danh sách hội thoại của client hiển thị chính xác.
8. `DELETE /api/v1/conversations/{id}` -> Xóa hội thoại trả về HTTP 204 No Content.
9. `GET /api/v1/conversations/{id}/messages` sau khi xóa -> Trả về HTTP 404 Not Found.

### 5.2. Kiểm thử Tự động qua Pytest (Automated Test Suite)
Toàn bộ **23/23 bài kiểm thử ĐẠT 100%**:
- **12 bài kiểm thử Milestone 1 & 2 (`test_conversations.py`):** Kiểm tra health endpoint, CRUD hội thoại, sắp xếp giảm dần theo thời gian, cô lập tuyệt đối giữa các client, cascade xóa và lưu trữ bền vững sau khi mở lại SQLite.
- **11 bài kiểm thử Milestone 3 (`test_messages.py`):** Kiểm tra gửi tin nhắn thành công, thứ tự tin nhắn xác định (user luôn trước assistant), truyền chính xác ngữ cảnh 10 tin nhắn gần nhất, tính lũy thỏa khi lặp lại request ID, xung đột khi đổi nội dung tin nhắn, xử lý đồng thời 2 luồng gần như cùng lúc, kiểm tra đầu vào không hợp lệ, mô phỏng AI lỗi/timeout không lưu dữ liệu dở dang và cascade xóa bản ghi idempotency.

---

## 6. Kết luận Rà soát Lỗi (Defect Review)

- **Kết quả rà soát mã nguồn:**
  - Logic gửi tin nhắn, giao dịch nguyên tử `with db:`, ràng buộc `PRIMARY KEY` trên `idempotency_records`, và các exception handler hoạt động chuẩn xác theo kế hoạch đề ra.
  - Không có lỗi nghiêm trọng (blocking defects), không có hiện tượng rò rỉ transaction hoặc giữ write lock trong thời gian chờ AI.
  - Cơ sở dữ liệu và mã nguồn sạch sẽ, không chứa thông tin nhạy cảm.
- Backend của Thành viên C chính thức sẵn sàng chuyển giao cho Thành viên A và Thành viên D.
