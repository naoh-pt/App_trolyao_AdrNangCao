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

## Cấu hình AI Provider (Stage 4: Gemini & Groq Fallback)

Backend hỗ trợ kiến trúc trừu tượng hóa provider sinh phản hồi (`ProviderService`), cho phép cấu hình linh hoạt giữa **Gemini** và **Groq**, tự động chuyển sang fallback khi provider chính gặp sự cố quota, timeout hoặc 5xx.

### 1. Thiết lập biến môi trường trong `backend/.env`

Tại thư mục `backend`, tạo file `.env` từ `.env.example`:

```env
# Lựa chọn provider sinh nội dung: 'gemini' hoặc 'groq'
AI_PRIMARY_PROVIDER=gemini

# Provider dự phòng khi provider chính gặp lỗi (quota, timeout, network):
# 'groq', 'gemini', hoặc 'none' (tắt fallback)
AI_FALLBACK_PROVIDER=groq

# Google AI Studio / Gemini API configuration
# Lưu ý: RAG embeddings luôn sử dụng Gemini độc lập với provider sinh phản hồi.
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-3.5-flash

# Groq API configuration
GROQ_API_KEY=your_groq_api_key
GROQ_MODEL=openai/gpt-oss-120b

# Budget thời gian (milliseconds): RAG (9s) + Gemini (28s) + Groq (15s) = 52s <= 55s
RAG_TIMEOUT_MS=9000
GEMINI_GENERATION_TIMEOUT_MS=28000
GROQ_TIMEOUT_MS=15000
AI_TOTAL_TIMEOUT_MS=55000

USE_REAL_AI=true
```

### 2. Các tổ hợp Provider được hỗ trợ

1. **Gemini chính + Groq dự phòng (Mặc định cho Demo):**
   - `AI_PRIMARY_PROVIDER=gemini`
   - `AI_FALLBACK_PROVIDER=groq`
   - Yêu cầu cấu hình cả `GEMINI_API_KEY` và `GROQ_API_KEY`. Khi Gemini bị 429 quota hoặc timeout, Groq tự động tiếp quản xử lý.
2. **Groq chính + Gemini dự phòng:**
   - `AI_PRIMARY_PROVIDER=groq`
   - `AI_FALLBACK_PROVIDER=gemini`
3. **Chỉ dùng một provider (Không fallback):**
   - `AI_PRIMARY_PROVIDER=gemini` (hoặc `groq`)
   - `AI_FALLBACK_PROVIDER=none`
4. **Chế độ Mock AI (Không tốn API key, cho test offline):**
   - Đặt `USE_REAL_AI=false`

### 3. Nguyên tắc Fallback & Bảo toàn tính cách Anna

- **Bảo toàn cá tính Anna:** Mọi provider đều nhận chung system instruction của nhân vật Anna từ `app/services/personality.py` và trả về JSON có cấu trúc `{"reply": "...", "emotion": "..."}`.
- **Chuẩn hóa cảm xúc:** Cả hai provider đều chuẩn hóa cảm xúc về 4 trạng thái tương thích Android (`neutral`, `happy`, `sad`, `surprised`).
- **Trường hợp cả hai provider cạn quota:** Nếu cả primary và fallback (hoặc provider duy nhất) đều cạn kiệt hạn ngạch (429/RESOURCE_EXHAUSTED), hệ thống chuyển sang câu xin lỗi thân thiện của Anna với cảm xúc `sad` và `sources: []`, mã HTTP 200, lưu lại database với tính lũy thỏa (idempotency).
- **Trường hợp lỗi xác thực (Auth error/thiếu key):** Nếu primary gặp lỗi xác thực nhưng fallback được cấu hình hợp lệ, hệ thống tự động chuyển tiếp sang fallback để đảm bảo phiên demo không bị gián đoạn. Nếu fallback tắt hoặc cũng lỗi, trả về 503 `LLM_UNAVAILABLE`.
- **RAG Embeddings:** Quá trình embedding tài liệu và vector search trong RAG **luôn chạy trên Gemini** độc lập với provider sinh phản hồi hội thoại.

### 4. Giới hạn thời gian (Timeout Budget) và số worker cho Demo

- **Vô hiệu hóa cơ chế tự động thử lại (Retry) của SDK:**
  - Client Groq được cấu hình `max_retries=0`.
  - Client Gemini sinh phản hồi và Gemini RAG embedding đều được cấu hình `HttpRetryOptions(attempts=1)` (chỉ 1 lần gọi duy nhất, không retry tự động).
  - Trình điều phối (Provider orchestrator) đảm bảo mỗi provider chỉ được gọi tối đa 1 lần trong chuỗi xử lý: RAG embedding (tối đa 1 lần) -> Primary generation (tối đa 1 lần) -> Fallback generation (tối đa 1 lần).
- **Tính toán ngân sách thời gian:**
  $$\text{RAG (9s)} + \text{Gemini (28s)} + \text{Groq (15s)} = 52\text{s} \le \text{AI\_TOTAL\_TIMEOUT\_MS (55s)}$$
  - Con số 52 giây là **tổng cấu hình timeout của các provider**, không phải là deadline đồng hồ thực (wall-clock deadline) toàn request, bởi vì overhead từ Python, SQLite, Chroma, kết nối mạng và lập lịch có thể cộng thêm thời gian.
  - `AI_TOTAL_TIMEOUT_MS` đóng vai trò là ngưỡng trần an toàn được kiểm tra xác thực khi khởi động server, không phải cơ chế huỷ runtime tự động.
  - **Khuyến nghị cho Android:** Phía client Android cần cấu hình read timeout tối thiểu **65 giây** khi tích hợp để tránh client huỷ kết nối sớm trước khi toàn bộ chuỗi fallback hoàn tất.
- **Chạy demo với đúng một worker (Bắt buộc):**
  ```powershell
  .\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1
  ```
  *Lưu ý:* Cơ chế khóa `request_id` xử lý idempotency được kiểm soát trong bộ nhớ tiến trình Uvicorn. Nhiều worker có thể dẫn đến việc cùng gọi provider cho một `request_id` trước khi SQLite chặn ghi trùng ở tầng cơ sở dữ liệu. Do đó, môi trường demo bắt buộc chạy với 1 worker.

Khi phát triển với chế độ tự động tải lại (reload):
```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## RAG: Sổ tay sinh viên

RAG dùng Chroma local để lưu các chunks/vector embedding và SQLite để lưu metadata tài liệu cùng nguồn đã dùng trong mỗi câu trả lời. Khi không có đoạn sổ tay nào đủ liên quan, chat tự động dùng Gemini bình thường.

Thêm vào `backend/.env`:

```env
RAG_ENABLED=true
RAG_ADMIN_TOKEN=tao_mot_chuoi_bi_mat_dai_va_ngau_nhien
GEMINI_EMBEDDING_MODEL=gemini-embedding-2
RAG_TOP_K=4
RAG_MIN_SCORE=0.70
```

Khởi động lại server, vào Swagger `http://localhost:8000/docs`, gọi `POST /api/v1/knowledge/documents` và:

- điền header `X-Admin-Token` bằng đúng `RAG_ADMIN_TOKEN`;
- chọn file PDF sổ tay có thể bôi đen/copy chữ (tối đa 15 MB);
- gửi request. API trả về số trang và số chunks đã import.

`GET /api/v1/knowledge/documents` cho phép kiểm tra danh sách tài liệu đã import, cũng yêu cầu `X-Admin-Token`. Endpoint upload không dùng `X-Client-Id` vì đây là thao tác quản trị. Chat vẫn dùng `X-Client-Id` như trước.

Mỗi phản hồi chat có thêm trường `sources`. Nếu RAG được dùng, mỗi nguồn chứa `filename`, `page_number`, `document_id`, và `score`; nếu câu hỏi ngoài phạm vi sổ tay thì `sources` là mảng rỗng và Gemini trả lời theo kiến thức chung.
