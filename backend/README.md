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
cd backend
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

Chạy toàn bộ bộ kiểm thử với cơ sở dữ liệu tạm thời (được cô lập hoàn toàn, không ảnh hưởng đến database phát triển):

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

## Chế độ đồng hành và cá nhân hóa (Stage 16)

Khởi động backend như cũ: bảng `companion_preferences` được thêm bằng `CREATE TABLE IF NOT EXISTS`, không sửa trí nhớ/lịch sử cũ, không cần API key hoặc dependency mới. Không chỉnh file `.env` hiện tại.

Hai API dùng header `X-Client-Id` hiện có:

- `GET /api/v1/companion-preferences`: giá trị đã lưu hoặc mặc định, không tạo bản ghi khi chỉ đọc.
- `PUT /api/v1/companion-preferences`: thay thế nguyên bộ lựa chọn của client trong một transaction. Enum/tên không hợp lệ trả HTTP 400 theo kiểu lỗi chung của dự án. Không gọi AI/RAG.

```json
{
  "preferred_name": "Hoàn",
  "address_style": "anna_ban",
  "humor_level": "medium",
  "response_length": "medium",
  "support_style": "balanced",
  "mood_check_in_enabled": true
}
```

Tên mặc định trống, tối đa 30 ký tự, một dòng, không ký tự điều khiển/chỉ dẫn. Cách xưng hô: `anna_ban`, `minh_ban`, `chi_em`, `em_anh`, `em_chi`; không suy đoán giới tính. Hài hước: `low/medium/high`. Độ dài: `short/medium/detailed`. Hỗ trợ: `balanced/listen_first/advice_first/solve_together`. Tên chỉ dùng tự nhiên, vừa phải; lựa chọn này không ghi đè trí nhớ Stage 15.

Prompt Gemini/Groq dùng chung thứ tự: an toàn → tính cách Anna → chính sách đồng hành → lựa chọn được kiểm tra → trí nhớ không đáng tin cậy → RAG → lịch sử/tin hiện tại. Yêu cầu lắng nghe/góp ý/cùng giải quyết trong tin hiện tại ưu tiên hơn lựa chọn hỗ trợ mặc định. Nội dung nghiêm túc luôn tắt hài hước. Anna là AI hỗ trợ, không phải người hay người thay thế bạn bè/chuyên gia; không chẩn đoán, tạo phụ thuộc hay thao túng bằng trí nhớ. Nguy hiểm tức thời được phản hồi bình tĩnh, khuyến khích liên hệ người tin cậy ở gần và hỗ trợ chuyên môn/khẩn cấp phù hợp, không tra cứu hotline qua web. Weather, action, quick reply và lệnh trí nhớ giữ câu trả lời xác định, không bị cá nhân hóa hoặc gửi qua AI.

Android: Cài đặt → **Cá nhân hóa Anna**, chỉnh và nhấn **Lưu thay đổi**. Rời khi chưa lưu có xác nhận; lưu lỗi giữ bản chỉnh sửa. Mood card chỉ xét sau khi vào chat đã tồn tại, Stage 15 trả kết quả không có lời nhắc, tải được cài đặt bật mood, và thiết bị chưa đánh dấu ngày đó cho client này. Marker ngày được dành nguyên tử ngay trước khi hiện để tránh hai chat hiện trùng; xoay máy/tái tổ hợp/đổi chat không tạo thẻ mới cùng ngày. Ngày tính theo lịch địa phương trên thiết bị; chỉ kiểm tra lúc vào chat, không polling. Lỗi/đổi chat đúng lúc có thể tiêu thụ marker mà chưa thấy thẻ; thử lại ở lần vào ngày sau, không có thông báo nền.

Thẻ tâm trạng và ba lựa chọn hỗ trợ nằm trong danh sách chat, không thay kích thước nhân vật. Chọn là thao tác gửi rõ ràng, qua luồng gửi/request-id/TTS/typewriter hiện có và giữ nguyên bản nháp đang gõ. Không chọn thì không gửi/đọc/đổi animation. Không lưu mood history hay nhãn tâm lý; chỉ các tin nhắn người dùng chủ động gửi mới nằm trong lịch sử chat thông thường. Bộ nhận biết hỗ trợ dùng quy tắc Unicode bảo thủ, có thể bỏ sót; không là công cụ chẩn đoán. Cá nhân hóa câu trả lời thật cần provider AI hoạt động; toàn bộ kiểm thử tự động dùng fake.

Kiểm thử offline: `.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider tests/test_companion.py`.

## Trí nhớ cá nhân và lời nhắc trong ứng dụng (Stage 15)

Khởi động backend như cũ. `init_db()` thêm bảng `personal_memories` và chỉ mục bằng `CREATE TABLE/INDEX IF NOT EXISTS`, giữ nguyên bảng/lịch sử trò chuyện hiện có. Không cần dependency, API key, cấu hình `.env` hay migration phá dữ liệu. Kiểm thử nâng cấp chỉ chạy với database tạm.

Chỉ lưu khi người dùng ra lệnh rõ ràng:

```text
Anna hãy nhớ: mình tên là Hoàn.
Anna hãy nhớ: mình thích học Android.
Hãy nhớ rằng mình đang học năm cuối.
Anna nhớ gì về mình?
Bạn đang nhớ gì về mình?
Anna hãy quên việc mình thích học Android.
Hãy quên thông tin mình tên là Hoàn.
Anna hãy nhớ: mình thi Android vào thứ Sáu tuần sau. Nhắc mình khi mở ứng dụng từ hôm nay.
```

Câu kể thông thường không tự được lưu. Mỗi thông tin tối đa 300 ký tự; tối đa 30 thông tin đang hoạt động cho mỗi `X-Client-Id`; chuẩn hóa Unicode/hoa thường để chặn trùng. Bộ lọc xác định từ chối thông tin có dấu hiệu mật khẩu, OTP, API/private key, token, số thẻ đầy đủ; đây là bảo vệ theo mẫu, không bảo đảm phát hiện mọi bí mật. Tin nhắn chat vẫn được lưu theo hợp đồng hiện tại, vì vậy không nhập bí mật vào cuộc trò chuyện.

Ngày sự kiện và ngày bắt đầu nhắc dùng bộ phân tích Calendar hiện có theo UTC+07:00: hôm nay, ngày mai, ngày kia, thứ cụ thể tuần này/tuần sau/tuần tới. Ngày mơ hồ hoặc đã qua cần làm rõ. Lời nhắc chỉ phát một lần khi mở/chọn một cuộc trò chuyện đã tồn tại, không chạy nền, không polling, không thông báo Android và không tự mở Calendar. Lời nhắc xuất hiện như tin nhắn lịch sử bình thường, không ép TTS/typewriter/animation. Không có cuộc trò chuyện được chọn thì không gọi check-in hay tạo chat vì check-in.

API mới dùng cùng header `X-Client-Id` và kiểu lỗi của dự án:

- `GET /api/v1/memories`: `{items: [...]}` gồm thông tin đang hoạt động và đã lưu trữ, có cờ `active`; không lộ trường chuẩn hóa/client ID nội bộ.
- `DELETE /api/v1/memories/{id}`: HTTP 204, chỉ xóa bản ghi thuộc chủ sở hữu; không xóa lịch sử chat.
- `POST /api/v1/conversations/{id}/check-in`: HTTP 200 `{message: null}` hoặc `{message: MessageResponse}`. Một transaction ghi tin nhắn và `reminded_at`; không gọi công cụ ngoài hoặc AI. Không tạo chat tự động.

Android: Cài đặt → **Trí nhớ của Anna** để xem, xóa từng mục hoặc xóa tất cả sau xác nhận (xóa từng ID trong danh sách, gồm mục đã lưu trữ). Nếu mạng lỗi giữa chừng, danh sách được tải lại và hiển thị lỗi thân thiện; thao tác này không phải bulk transaction. Sự kiện hết hạn được lưu trữ/exclude khỏi context và check-in, không bị xóa ngầm. Không tự kích hoạt lại bản ghi đã nhắc/quá hạn; muốn tạo sự kiện mới cùng nội dung thì người dùng phải xóa bản cũ rồi lưu lại rõ ràng.

Khi chat thường dùng Gemini/Groq, tối đa 10 mục đang hoạt động, tối đa 1500 ký tự JSON đã escape được đưa vào khối dữ liệu người dùng không đáng tin cậy, tách khỏi RAG. Không làm theo chỉ dẫn nằm trong trí nhớ. Thông tin này có thể được gửi tới provider đang cấu hình khi người dùng gửi câu hỏi AI thông thường; các lệnh local, Weather, action và check-in không gọi AI. Không log nội dung trí nhớ. Cơ chế sở hữu vẫn là UUID client của dự án, không phải hệ thống đăng nhập mới.

Nhắc lặp lại, nhắc khi ứng dụng đóng và thông báo hệ thống nằm ngoài phạm vi; dùng Calendar/timer hiện có. Vào lại cùng màn hình sau xoay máy/tái tổ hợp không tạo lần check-in logic mới; vào một navigation entry mới thì kiểm tra lại. Không có yêu cầu định kỳ hay tự thử lại nền.

Kiểm thử offline: `.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider tests/test_memory.py`.

## Thời tiết trực tiếp: Open-Meteo (Stage 14B)

Backend dùng công cụ xác định, không dùng Gemini/Groq/RAG để lấy hoặc diễn đạt dữ liệu thời tiết. Không cần API key hay GPS. Laptop chạy backend cần Internet ra ngoài tới hai host HTTPS cố định: `geocoding-api.open-meteo.com` và `api.open-meteo.com`. Không có URL cấu hình tùy ý, không theo redirect, không retry. Khởi động lại backend sau khi đổi cấu hình.

Các câu mẫu:

- `Thời tiết Hà Nội hiện tại thế nào?`
- `Thời tiết Hà Nội hôm nay thế nào?`
- `Ngày mai Hà Nội có mưa không?`
- `Nhiệt độ ở Bắc Ninh hôm nay bao nhiêu?`
- `Hôm nay mình có nên mang áo mưa ở Hà Nội không?`

Hỗ trợ `hiện tại`, `hôm nay`, `ngày mai`, `ngày kia`. Thiếu địa điểm thì Anna hỏi lại, không chọn vị trí IP hoặc mặc định Hà Nội. Với địa điểm nước ngoài nên ghi rõ quốc gia sau dấu phẩy, ví dụ `Thời tiết Paris, France ngày mai thế nào?`. Chỉ dùng tên được gõ trong câu, không lấy vị trí điện thoại. Lỗi mạng hoặc thiếu dữ liệu trả lời thân thiện, không nhờ AI đoán thời tiết. Mỗi kết quả thành công có `Nguồn dữ liệu: Open-Meteo.`; `sources` vẫn là mảng rỗng vì schema nguồn hiện tại dành cho tài liệu RAG.

Các giá trị mặc định (có trong `.env.example`, không cần sửa file `.env` hiện tại để bật tính năng):

```env
WEATHER_ENABLED=true
WEATHER_CONNECT_TIMEOUT_MS=3000
WEATHER_READ_TIMEOUT_MS=6000
WEATHER_CACHE_TTL_SECONDS=600
WEATHER_GEOCODING_CACHE_TTL_SECONDS=86400
```

Timeout độc lập với ngân sách AI: connect tối đa 3 giây, read/write/pool tối đa 6 giây mỗi request HTTP; một câu hỏi chưa cache cần tối đa hai request tuần tự. Không có retry. Đây là timeout I/O của HTTPX, không phải deadline tuyệt đối cho toàn bộ câu hỏi. Cache trong RAM: địa điểm 24 giờ, dự báo 10 phút, tối đa 256 mục mỗi cache, mất khi khởi động lại. Giá trị số không hợp lệ/không dương/vượt giới hạn dùng mặc định an toàn; giới hạn cấu hình: connect 3000 ms, read 6000 ms, dự báo 3600 giây, địa điểm 86400 giây. Dùng `WEATHER_ENABLED=false` để tạm tắt; câu hỏi thời tiết vẫn không được gửi sang AI.

Ngày dự báo được tính trong timezone Open-Meteo trả về; dữ liệu hiện tại quá 2 giờ bị từ chối. Dự báo có thể thay đổi, cache có thể chậm tối đa 10 phút, lời khuyên mang áo mưa không bảo đảm chắc chắn có/không mưa. Công cụ này dành cho demo một worker, không phải dịch vụ cảnh báo thời tiết khẩn cấp.

Kiểm thử offline:

```powershell
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider tests/test_weather.py
```

Tài liệu gốc: [Forecast API](https://open-meteo.com/en/docs), [Geocoding API](https://open-meteo.com/en/docs/geocoding-api). Kiểm thử tự động dùng HTTP MockTransport, không gọi mạng thật.

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
