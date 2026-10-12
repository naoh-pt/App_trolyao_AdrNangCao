# Group 1 Manual End-to-End Test Checklist

This document provides step-by-step instructions for performing manual end-to-end integration testing between the `VirtualAssistant` Android application and the FastAPI backend service.

---

## Pre-requisites & Setup

1. **Backend Host**: Laptop running FastAPI server bound to `0.0.0.0:8000`.
2. **Device**: Physical Android device or Android Emulator.
3. **Network**: Android device and Laptop connected to the same local Wi-Fi / LAN network.

---

## Test Cases

### Test 1: Start Backend Server
- **Preparation**: Ensure Python environment with FastAPI dependencies is active.
- **Action**: Run backend command: `uvicorn app.main:app --host 0.0.0.0 --port 8000`
- **Expected Result**: Backend starts successfully and prints `Uvicorn running on http://0.0.0.0:8000`.
- **Status**: [ ] Pass / [ ] Fail

---

### Test 2: Network Connectivity Setup
- **Preparation**: Ensure laptop and Android phone/emulator are on the same Wi-Fi network.
- **Action**: Note the laptop's LAN IP address (e.g. `192.168.1.10` via `ipconfig` or `ifconfig`). Ping laptop IP from device or verify route.
- **Expected Result**: Network packets route successfully between device and laptop.
- **Status**: [ ] Pass / [ ] Fail

---

### Test 3: Configure Backend URL in App Settings
- **Preparation**: Launch the `VirtualAssistant` Android app.
- **Action**: Navigate to **Cài đặt ⚙️** (Settings). Enter `192.168.1.10:8000` or `http://192.168.1.10:8000/api/v1/` into the Backend URL field and tap **Lưu** (Save).
- **Expected Result**: The app normalizes the URL to `http://192.168.1.10:8000/` and displays confirmation "Đã lưu địa chỉ backend thành công".
- **Status**: [ ] Pass / [ ] Fail

---

### Test 4: Verify Backend Health Check (/health)
- **Preparation**: Backend is running on port 8000; URL is saved in Settings.
- **Action**: In **Cài đặt ⚙️**, tap **Kiểm tra kết nối** (Test Connection).
- **Expected Result**: App calls `GET /api/v1/health` and displays green status text "Kết nối thành công! Server hoạt động bình thường."
- **Status**: [ ] Pass / [ ] Fail

---

### Test 5: Create a Conversation
- **Preparation**: Return to Home screen or Chat screen.
- **Action**: Tap **Bắt đầu trò chuyện** or the **+** (New Chat) icon.
- **Expected Result**: App sends `POST /api/v1/conversations` with `X-Client-Id` header. A new conversation is created on the server and cached in Room.
- **Status**: [ ] Pass / [ ] Fail

---

### Test 6: Send a Message
- **Preparation**: Active conversation open in Chat screen.
- **Action**: Type "Xin chào trợ lý" in text input and tap the **Send** button.
- **Expected Result**: 
  1. Input field clears, message appears as user bubble.
  2. Character avatar switches to `THINKING` state.
  3. Assistant responds with reply; avatar transitions to `TALKING` with appropriate emotion avatar.
- **Status**: [ ] Pass / [ ] Fail

---

### Test 7: Verify User and Assistant Message Ordering
- **Preparation**: User and Assistant messages sent/received.
- **Action**: Observe message list in the Chat screen.
- **Expected Result**: User message appears before Assistant reply, even if both messages share the exact same timestamp from backend (`createdAt`).
- **Status**: [ ] Pass / [ ] Fail

---

### Test 8: Return to Conversation History
- **Preparation**: Complete chat in active conversation.
- **Action**: Tap top bar **Quay lại** (Back) or **Lịch sử** (History) button.
- **Expected Result**: History screen displays the newly created conversation with updated title and last modified timestamp.
- **Status**: [ ] Pass / [ ] Fail

---

### Test 9: Reopen Existing Conversation
- **Preparation**: On Conversation History screen.
- **Action**: Tap on the conversation item in the list.
- **Expected Result**: Chat screen opens, loading and displaying all cached messages belonging to that conversation from Room database.
- **Status**: [ ] Pass / [ ] Fail

---

### Test 10: Delete a Conversation
- **Preparation**: On Conversation History screen with at least one conversation item.
- **Action**: Tap the delete icon next to a conversation item.
- **Expected Result**: App sends `DELETE /api/v1/conversations/{id}`. Upon success, conversation and its messages are deleted from Room database and removed from History UI.
- **Status**: [ ] Pass / [ ] Fail

---

### Test 11: Restart App and Verify Persistence
- **Preparation**: Ensure at least one active conversation exists.
- **Action**: Force stop / close `VirtualAssistant` app and relaunch it.
- **Expected Result**: Saved backend URL and Client ID persist in DataStore. Previously saved conversations and messages remain available from Room cache.
- **Status**: [ ] Pass / [ ] Fail

---

### Test 12: Backend Offline Error Handling
- **Preparation**: App is open in Chat screen.
- **Action**: Stop the FastAPI backend process on laptop. Attempt to send a message or tap Refresh.
- **Expected Result**: 
  1. App does NOT crash.
  2. Clear Vietnamese error message displayed: "Không thể kết nối tới server (Connection refused). Kiểm tra xem backend đã chạy chưa."
  3. Offline banner appears; previously cached chat history remains visible.
- **Status**: [ ] Pass / [ ] Fail

---

### Test 13: Backend Recovery and Online Status
- **Preparation**: Backend is stopped; app is showing offline banner.
- **Action**: Restart the FastAPI backend server on laptop. Tap **Thử lại** (Retry) on the offline banner.
- **Expected Result**: App reconnects successfully, offline banner disappears, and full sending capability is restored.
- **Status**: [ ] Pass / [ ] Fail

---

### Test 14: Rapid Tap Send Button (Duplicate Prevention)
- **Preparation**: Type "Test duplicate tap" in the text input.
- **Action**: Rapidly tap the **Send** button 5 times in quick succession.
- **Expected Result**: 
  1. Send action is immediately disabled upon first tap.
  2. Only 1 network request with 1 unique `request_id` is transmitted to the backend.
  3. No duplicate user or bot messages are created.
- **Status**: [ ] Pass / [ ] Fail

---

### Test 15: Empty Server List Synchronization
- **Preparation**: Clear database/data on backend server or delete all conversations via server DB.
- **Action**: Tap **Refresh** in History screen or pull to refresh.
- **Expected Result**: App detects empty list `[]` from backend, triggers safe full clean-up (`deleteAll()`), and removes stale local conversations from Room.
- **Status**: [ ] Pass / [ ] Fail
