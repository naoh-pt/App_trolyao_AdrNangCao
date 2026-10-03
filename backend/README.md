# Tro Ly Ao Backend — Hướng dẫn cài đặt & Khởi chạy (Milestone 3)

Dự án backend FastAPI cho ứng dụng Trợ lý ảo Android 2D (Nhóm thành viên C phụ trách Backend & Lưu trữ).
Milestone 3 tích hợp tính năng gửi tin nhắn và nhận phản hồi từ Mock AI (`POST /conversations/{id}/messages`), đảm bảo tính lũy thỏa (idempotency), lưu trữ nguyên tử và cung cấp ngữ cảnh 10 tin nhắn gần nhất.

---

## 1. Yêu cầu hệ thống

- Hệ điều hành: Windows 10/11
- Python: Phiên bản 3.11 trở lên (kiểm tra bằng lệnh `py -3.11 --version`)

---

## 2. Di chuyển vào thư mục backend

Mở Windows PowerShell và chuyển vào thư mục `backend`:

```powershell
cd d:\nam5\semester_1\advance_android\troLyAo_ani\backend
```

---

## 3. Môi trường ảo (Virtual Environment) & Cài đặt thư viện

Nếu chưa tạo môi trường ảo:
```powershell
py -3.11 -m venv .venv
```

Cài đặt các thư viện cần thiết:
```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

---

## 4. Kích hoạt môi trường ảo (Tùy chọn)

### Kích hoạt:
```powershell
.\.venv\Scripts\Activate.ps1
```

### Xử lý khi PowerShell chặn kích hoạt script (ExecutionPolicy):
Bạn có thể:
1. **Chạy trực tiếp qua `.venv` (Khuyên dùng):** Gọi trực tiếp `.\.venv\Scripts\python.exe <lệnh>` mà không cần kích hoạt script.
2. Hoặc mở quyền cho phiên làm việc hiện tại:
   ```powershell
   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process
   .\.venv\Scripts\Activate.ps1
   ```

---

## 5. Chạy bộ kiểm thử tự động (Automated Tests)

Chạy toàn bộ 39 test cases (bao gồm các ca hồi quy sau code review) với cơ sở dữ liệu tạm thời (được cô lập hoàn toàn, không ảnh hưởng đến database phát triển):

```powershell
.\.venv\Scripts\python.exe -m pytest -v
```

---

## 6. Khởi chạy Server FastAPI

Lắng nghe trên host `0.0.0.0` tại cổng `8000` (cho phép cả Android Emulator `10.0.2.2` và thiết bị thật qua LAN kết nối):

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## 7. Các API Endpoints & Ví dụ kiểm tra (PowerShell)

Tất cả các API nghiệp vụ yêu cầu header `X-Client-Id` chứa chuỗi UUID hợp lệ (ngoại trừ endpoint `/health`).

### 1. Kiểm tra sức khỏe hệ thống (`GET /api/v1/health`)
```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/health" -Method Get
```
**Kết quả:**
```json
{"status":"ok"}
```

---

### 2. Tạo cuộc trò chuyện mới (`POST /api/v1/conversations`)

```powershell
$conv = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/conversations" `
  -Method Post `
  -Headers @{"X-Client-Id"="d3b07384-d113-46fb-a0f2-51ab3e43f550"}
$convId = $conv.id
Write-Output "ID cuộc trò chuyện: $convId"
```
**Kết quả:**
```json
{
  "id": "e2a39a7b-3b6b-4e94-a14a-81a1727ea1a0",
  "title": "Cuộc trò chuyện mới",
  "created_at": "2026-10-02T15:20:00Z",
  "updated_at": "2026-10-02T15:20:00Z"
}
```

---

### 3. Gửi tin nhắn & Nhận câu trả lời từ Mock AI (`POST /api/v1/conversations/{id}/messages`)

Gửi tin nhắn với `request_id` (UUID) và nội dung `message`:
```powershell
$body = '{"request_id":"c6b840e2-6325-4c07-84eb-9d62057d5440","message":"Xin chào trợ lý ảo"}'

$reply = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/conversations/$convId/messages" `
  -Method Post `
  -Headers @{"X-Client-Id"="d3b07384-d113-46fb-a0f2-51ab3e43f550"} `
  -ContentType "application/json; charset=utf-8" `
  -Body $body

$reply | ConvertTo-Json -Depth 5
```
**Kết quả (HTTP 200 OK):**
```json
{
  "user_message": {
    "id": "718a0d38-dafc-42bb-b72d-1733ee467ed7",
    "role": "user",
    "text": "Xin chào trợ lý ảo",
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

---

### 4. Kiểm tra tính lũy thỏa (Idempotency)

- Khi gửi lại **cùng `request_id`** và **cùng nội dung tin nhắn**, server trả về cặp tin nhắn đã lưu trước đó (cùng ID, cùng timestamp), không chèn thêm dữ liệu thừa.
- Nếu gửi lại **cùng `request_id`** nhưng **khác nội dung tin nhắn**, server trả về lỗi xung đột **HTTP 409 Conflict**:
  ```json
  {
    "error": {
      "code": "REQUEST_ID_CONFLICT",
      "message": "Request ID đã được sử dụng với nội dung tin nhắn khác"
    }
  }
  ```
- Trong một tiến trình Uvicorn, các request trùng `request_id` được xử lý lần lượt: request chờ đọc lại kết quả đã lưu trước khi gọi AI. Chờ tối đa 35 giây; quá hạn trả HTTP 503 `REQUEST_IN_PROGRESS`. Cơ chế này nằm trong bộ nhớ tiến trình, **không** ngăn hai lời gọi AI ở nhiều worker hoặc nhiều tiến trình server. Chạy một worker cho bản demo này. SQLite vẫn dùng khóa chính duy nhất và transaction để ngăn lưu cặp tin nhắn trùng.
- Nếu SQLite bị busy/locked, server chờ tối đa 2 giây cho mỗi thao tác rồi trả HTTP 503 `DATABASE_BUSY`, kèm `Retry-After: 1`. Android giữ nguyên `request_id` và nội dung khi thử lại. Nếu AI không trả về câu trả lời dạng chuỗi có nội dung, server trả 503 `LLM_UNAVAILABLE` và không lưu cặp tin nhắn. Emotion thiếu/lạ được chuẩn hóa thành `neutral`.
- Timestamp phản hồi vẫn là UTC ISO 8601 hậu tố `Z`, hiện có phần microsecond để sắp xếp chính xác các chat hoạt động trong cùng một giây. Tin nhắn vẫn xếp cũ trước mới; khi timestamp bằng nhau, thứ tự ghi quyết định vị trí.

---

### 5. Lấy danh sách tin nhắn (`GET /api/v1/conversations/{id}/messages`)

Trả về danh sách tin nhắn theo thứ tự từ cũ nhất đến mới nhất:
```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/conversations/$convId/messages" `
  -Method Get `
  -Headers @{"X-Client-Id"="d3b07384-d113-46fb-a0f2-51ab3e43f550"} | ConvertTo-Json -Depth 5
```
**Kết quả:**
```json
{
  "items": [
    {
      "id": "718a0d38-dafc-42bb-b72d-1733ee467ed7",
      "role": "user",
      "text": "Xin chào trợ lý ảo",
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

---

### 6. Xóa cuộc trò chuyện (`DELETE /api/v1/conversations/{id}`)

Xóa cuộc trò chuyện và cascade xóa tin nhắn, cùng các bản ghi idempotency:
```powershell
curl.exe -i -X DELETE "http://127.0.0.1:8000/api/v1/conversations/$convId" `
  -H "X-Client-Id: d3b07384-d113-46fb-a0f2-51ab3e43f550"
```
**Kết quả:** HTTP `204 No Content`.

---

### 7. Swagger UI
- Truy cập trình duyệt: `http://localhost:8000/docs`
