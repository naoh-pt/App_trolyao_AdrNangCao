# Anna — Trợ lý ảo Android 2D

Ứng dụng Kotlin/Jetpack Compose kết nối backend FastAPI. Bản `main` tổng hợp đến Stage 17: chat/giọng nói và nhân vật hoạt ảnh, thời tiết, bản đồ/lịch/hẹn giờ có xác nhận, trí nhớ cá nhân, cá nhân hóa, cập nhật tâm trạng và bổ sung thông tin tạo lịch qua nhiều lượt chat.

## Clone dự án

```powershell
git clone --branch main https://github.com/naoh-pt/App_trolyao_AdrNangCao.git
cd App_trolyao_AdrNangCao
```

Mã nguồn Android, backend, Gradle Wrapper và 141 frame nhân vật đã có trong Git. Máy mới cần Python 3.11+, Android Studio, Android SDK 35 và JDK 17 trở lên tương thích Gradle 8.9 (có thể dùng JDK 17 hoặc 21). Trong Android Studio, chọn Gradle JDK tương ứng; khi chạy bằng terminal, đặt `JAVA_HOME` tới JDK trên máy của bạn. Không cần dùng đường dẫn Java của người phát triển.

## Chạy backend trước

Ví dụ trên Windows PowerShell, từ thư mục gốc:

```powershell
cd backend
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Để thử kết nối và chat giả lập khi chưa có API key, sửa hai dòng trong `backend/.env`:

```dotenv
USE_REAL_AI=false
RAG_ENABLED=false
```

Chế độ này dùng phản hồi mock cho chat AI; các lệnh xác định vẫn có thể dùng, riêng thời tiết cần Internet. Để chat AI thật, đặt `USE_REAL_AI=true`, điền khóa và model của provider trong `.env`; chỉ bật RAG khi có khóa Gemini, token quản trị riêng và đã nhập tài liệu. Xem [hướng dẫn backend](backend/README.md) để cấu hình provider và nhập PDF.

Khởi động từ thư mục `backend`:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Kiểm tra `http://127.0.0.1:8000/api/v1/health`; Swagger ở `http://127.0.0.1:8000/docs`.

Backend đọc **`backend/.env`**, không phải file `.env` ở gốc. API key, SQLite, dữ liệu Chroma và cấu hình SDK cục bộ không được đưa lên Git. Máy clone sẽ có database mới khi backend khởi động; tài liệu RAG phải được nhập lại. Không chia sẻ file `.env` chứa khóa thật.

## Chạy Android

1. Android Studio → **Open** thư mục `android`, cài SDK 35 nếu được yêu cầu và chờ Gradle sync. Android Studio tạo `local.properties` theo SDK của máy mới.
2. Chạy bản **debug** trên emulator hoặc điện thoại Android 8.0/API 26 trở lên.
3. Trong app → **Cài đặt** → nhập URL backend → **Kiểm tra kết nối** → **Lưu**.

| Kết nối | URL trong ứng dụng |
| --- | --- |
| Android Emulator | `http://10.0.2.2:8000` |
| Điện thoại cùng Wi-Fi với máy chạy backend | `http://<IP-LAN-máy-chạy-backend>:8000` |
| Điện thoại qua USB, sau `adb reverse tcp:8000 tcp:8000` | `http://127.0.0.1:8000` |

Kết nối Wi-Fi cần cho phép cổng 8000 qua firewall. HTTP chỉ được bật cho bản debug; release dùng HTTPS. Xem thêm [hướng dẫn Android](android/README.md).

## Kiểm thử

Từ `backend`:

```powershell
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
```

Từ `android` (cần JDK và Android SDK đã cấu hình):

```powershell
.\gradlew.bat :app:testDebugUnitTest :app:assembleDebug
```

Kiểm thử backend dùng database tạm và chặn kết nối mạng ngoài. Kiểm thử tự động không thay thế kiểm tra thiết bị thật hoặc API AI/thời tiết trực tiếp. Checklist Stage 17 và các giới hạn được ghi ở [báo cáo Stage 17](review/stage17-natural-language-router.md); báo cáo đó ghi lại trạng thái trước lần tích hợp `main` này.
