# VirtualAssistant — Android (vai trò A)

Kotlin + Jetpack Compose + Navigation Compose + ViewModel/Repository + Room + DataStore + Retrofit/OkHttp.

## Chạy app
1. Android Studio (bản mới) → **Open** thư mục này → chờ Gradle sync (nếu Studio gợi ý nâng cấp AGP/Gradle thì đồng ý).
2. Bật backend trên laptop: `uvicorn ... --host 0.0.0.0 --port 8000`, cho phép cổng 8000 qua firewall.
3. Cắm điện thoại (USB debugging), Run bản **debug**.
4. Trong app: **Cài đặt** → nhập `http://<IP LAN laptop>:8000` → **Kiểm tra kết nối** → **Lưu**.
   - Điện thoại và laptop phải cùng Wi-Fi. Lấy IP laptop: `ipconfig` (Windows) / `ifconfig` / `ip a`.
   - Emulator: `http://10.0.2.2:8000`. Không dùng `localhost`.
5. HTTP (cleartext) chỉ được bật ở bản debug (`app/src/debug/AndroidManifest.xml`). Bản release phải dùng HTTPS.

## Ghép asset nhân vật (vai trò B)
Chép 6 file `character_idle.png`, `character_thinking.png`, `character_talking.png`,
`character_happy.png`, `character_sad.png`, `character_surprised.png` (1024×1024) vào
`app/src/main/res/drawable-nodpi/`. Chưa có file thì app hiện emoji tạm.
Quy tắc chọn ảnh nằm ở `characterAsset()` trong `ui/components/CharacterAvatar.kt`.

## Cấu trúc
- `data/remote`: DTO, `ChatApi` (hợp đồng API), `ApiClient`
- `data/local`: Room (conversations, messages), `SettingsStore` (DataStore: `client_id`, URL backend)
- `data/repo/ChatRepository`: server là nguồn chính, Room là cache offline
- `ui/{home,chat,history,settings}`: màn hình + ViewModel
