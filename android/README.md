# VirtualAssistant — Android (vai trò A)

Kotlin + Jetpack Compose + Navigation Compose + ViewModel/Repository + Room + DataStore + Retrofit/OkHttp.

## Chạy app
1. Trong thư mục `backend`, tạo môi trường ảo bằng `py -3.11 -m venv .venv`, cài thư viện bằng `.\.venv\Scripts\python.exe -m pip install -r requirements.txt`, rồi sao chép `.env.example` thành `.env`. Điền khóa API riêng chỉ khi dùng AI thật; xem [hướng dẫn backend](../backend/README.md).
2. Bật backend trên laptop: chạy `.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload` từ thư mục `backend`. Cho phép cổng 8000 qua firewall nếu kết nối qua Wi-Fi.
3. Android Studio → **Open** thư mục `android` → chờ Gradle sync.
4. Cắm điện thoại (USB debugging), Run bản **debug**.
5. Trong app: **Cài đặt** → nhập URL backend → **Kiểm tra kết nối** → **Lưu**.
   - Điện thoại và laptop phải cùng Wi-Fi. Lấy IP laptop: `ipconfig` (Windows) / `ifconfig` / `ip a`.
   - Qua Wi-Fi, dùng `http://<IP LAN laptop>:8000`.
   - Qua USB, chạy `adb reverse tcp:8000 tcp:8000` rồi dùng `http://127.0.0.1:8000` trên điện thoại.
   - Emulator: `http://10.0.2.2:8000`. Không dùng `localhost`.
6. HTTP (cleartext) chỉ được bật ở bản debug (`app/src/debug/AndroidManifest.xml`). Bản release phải dùng HTTPS.

## Asset nhân vật
Các frame hoạt ảnh `.webp` đã được theo dõi trong `app/src/main/res/drawable-nodpi/`; không cần sao chép ảnh thủ công sau khi clone.

## Cấu trúc
- `data/remote`: DTO, `ChatApi` (hợp đồng API), `ApiClient`
- `data/local`: Room (conversations, messages), `SettingsStore` (DataStore: `client_id`, URL backend)
- `data/repo/ChatRepository`: server là nguồn chính, Room là cache offline
- `ui/{home,chat,history,settings}`: màn hình + ViewModel
