# Báo cáo thực hiện: Cài đặt nền tảng FastAPI (Milestone 1 - Thành viên C)

**Ngày thực hiện:** 02/10/2026  
**Thành viên đảm nhiệm:** Thành viên C (Backend & Lưu trữ)  
**Tài liệu kế hoạch tham chiếu:** `KE_HOACH_TRO_LY_AO_ANDROID-1.md` (giữ nguyên không sửa đổi)

---

## 1. Mục tiêu công việc

Hoàn thành mốc kỹ thuật đầu tiên cho backend:
- Thiết lập dự án Python trong thư mục `backend/` với Python 3.11+.
- Khởi tạo môi trường ảo tại `backend/.venv` và cài đặt các dependencies tối thiểu (FastAPI, Uvicorn).
- Triển khai endpoint `GET /api/v1/health` trả về HTTP 200 và chính xác `{"status":"ok"}`.
- Cấu hình server có thể chạy trên Windows với `python -m uvicorn` lắng nghe host `0.0.0.0` và cổng `8000`.
- Tạo file `.gitignore` ở thư mục gốc dự án chuẩn bị cho Git (bỏ qua `.venv/`, `__pycache__/`, `.env`, SQLite files, v.v.).
- Viết tài liệu `backend/README.md` hướng dẫn lệnh PowerShell chi tiết (bao gồm phương án xử lý khi PowerShell chặn kích hoạt script).
- Khởi động server thực tế và kiểm thử endpoint sức khỏe, báo cáo kết quả thật.

---

## 2. Danh sách tệp tin đã tạo

| Đường dẫn tệp | Mô tả chức năng |
| --- | --- |
| `.gitignore` | Cấu hình bỏ qua `.venv/`, `__pycache__/`, `.env`, SQLite files (`*.db`, `*.sqlite3`), và các file tạm của IDE/OS tại thư mục gốc. |
| `backend/requirements.txt` | Khai báo các thư viện phụ thuộc tối thiểu cho Milestone 1 (`fastapi`, `uvicorn[standard]`). Không thêm thư viện LLM hay DB ở mốc này. |
| `backend/app/__init__.py` | Đánh dấu thư mục `app` là package Python. |
| `backend/app/main.py` | Khởi tạo ứng dụng FastAPI, cấu hình CORS cơ bản cho dev, đăng ký router v1. |
| `backend/app/api/__init__.py` | Package API. |
| `backend/app/api/v1/__init__.py` | Package API phiên bản 1. |
| `backend/app/api/v1/health.py` | Endpoint `GET /health` (khi gộp vào app với prefix `/api/v1` sẽ là `/api/v1/health`), trả về `{"status":"ok"}`. |
| `backend/main.py` | Wrapper điểm vào cấp thư mục `backend/`, cho phép gọi cả `uvicorn app.main:app` và `uvicorn main:app`. |
| `backend/README.md` | Hướng dẫn chi tiết bằng lệnh Windows PowerShell cho cài đặt, kích hoạt môi trường, khởi chạy và kiểm thử. |
| `backend/reports/step1_setup.md` | Báo cáo chi tiết công việc của mốc Milestone 1 (file hiện tại). |

---

## 3. Các lệnh đã thực thi trong quá trình thiết lập

1. **Kiểm tra phiên bản Python 3.11:**
   ```powershell
   py -3.11 --version
   # Kết quả: Python 3.11.9
   ```

2. **Tạo môi trường ảo `.venv`:**
   ```powershell
   cd d:\nam5\semester_1\advance_android\troLyAo_ani\backend
   py -3.11 -m venv .venv
   ```

3. **Kiểm tra môi trường ảo:**
   ```powershell
   & "d:\nam5\semester_1\advance_android\troLyAo_ani\backend\.venv\Scripts\python.exe" --version
   # Kết quả: Python 3.11.9
   ```

4. **Cài đặt thư viện phụ thuộc vào `.venv`:**
   ```powershell
   & "d:\nam5\semester_1\advance_android\troLyAo_ani\backend\.venv\Scripts\python.exe" -m pip install -r requirements.txt
   # Đã cài đặt thành công: fastapi-0.142.2, uvicorn-0.54.0, starlette, pydantic, websockets, v.v.
   ```

5. **Kiểm tra tính tương thích khi import module ứng dụng:**
   ```powershell
   & "d:\nam5\semester_1\advance_android\troLyAo_ani\backend\.venv\Scripts\python.exe" -c "from app.main import app; print('App imported successfully:', app.title)"
   # Kết quả: App imported successfully: Tro Ly Ao Backend API
   ```

6. **Khởi chạy máy chủ thực tế (background process):**
   ```powershell
   & "d:\nam5\semester_1\advance_android\troLyAo_ani\backend\.venv\Scripts\python.exe" -m uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```

7. **Kiểm tra phản hồi thực tế từ endpoint `/api/v1/health` và `/docs`:**
   ```powershell
   curl.exe -i http://127.0.0.1:8000/api/v1/health
   Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/health" -Method Get
   curl.exe -i http://127.0.0.1:8000/docs
   curl.exe -s http://127.0.0.1:8000/openapi.json
   ```

---

## 4. Kết quả kiểm thử thực tế

Máy chủ FastAPI đã được kích hoạt thành công trên cổng `8000` và kiểm thử trực tiếp:

### Phản hồi từ `GET /api/v1/health`:
```http
HTTP/1.1 200 OK
date: Fri, 02 Oct 2026 14:55:04 GMT
server: uvicorn
content-length: 15
content-type: application/json
vary: Origin

{"status":"ok"}
```
- Mã phản hồi: **HTTP 200 OK**
- Nội dung trả về: **`{"status":"ok"}`** (đúng chính xác yêu cầu).

### Phản hồi từ tài liệu Swagger UI (`GET /docs`):
- Mã phản hồi: **HTTP 200 OK**
- Nội dung: Trang Swagger UI tích hợp sẵn OpenAPI schema 3.1.0 hiển thị endpoint `/api/v1/health`.

---

## 5. Hướng dẫn khởi chạy trên máy tính Windows

Bạn có thể chạy dự án trên laptop bằng các bước sau:

### Cách 1: Sử dụng môi trường ảo được kích hoạt (PowerShell)
```powershell
cd d:\nam5\semester_1\advance_android\troLyAo_ani\backend
.\.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Cách 2: Chạy trực tiếp qua file thực thi `.venv` (Không lo lỗi PowerShell ExecutionPolicy)
Nếu PowerShell chặn chạy file script kích hoạt (`Activate.ps1` bị lỗi UnauthorizedAccess), bạn chỉ cần gõ:
```powershell
cd d:\nam5\semester_1\advance_android\troLyAo_ani\backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Kiểm tra server:
Mở một cửa sổ PowerShell khác hoặc trình duyệt:
- Endpoint health: `http://localhost:8000/api/v1/health` (trả về `{"status":"ok"}`)
- Swagger Docs: `http://localhost:8000/docs`

---

## 6. Vấn đề tồn đọng & Lưu ý cho mốc tiếp theo

- **Vấn đề tồn đọng trong Milestone 1:** Không có (tất cả yêu cầu cho Milestone 1 đều đã hoàn thành và kiểm thử thành công).
- **Lưu ý khi demo thiết bị di động thật qua LAN:**
  - Vì server lắng nghe tại `0.0.0.0:8000`, thiết bị Android cần sử dụng địa chỉ IPv4 LAN của laptop (ví dụ: `http://192.168.1.x:8000/api/v1/health`).
  - Nếu Android không kết nối được qua Wi-Fi, cần kiểm tra Windows Defender Firewall để cho phép inbound traffic trên port 8000.
  - Trên Android Emulator, sử dụng địa chỉ `http://10.0.2.2:8000/api/v1/health`.
- **Kế hoạch Milestone 2:** Triển khai SQLite database, schema hội thoại (`conversations`, `messages`), CRUD endpoints, và mock AI service theo hợp đồng API trong kế hoạch dự án.
