"""Unit and route tests for assistant action recognition and route integration."""

import uuid
from datetime import datetime, timedelta
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.assistant_action_service import (
    VIETNAM_TZ,
    recognize_action,
)

client = TestClient(app)


# =============================================================================
# 1. Timer Unit Tests
# =============================================================================

def test_timer_minutes_recognition():
    res = recognize_action("nhắc tôi học bài sau 5 phút")
    assert res is not None
    assert res.emotion == "happy"
    assert res.action is not None
    assert res.action.type == "set_timer"
    assert res.action.duration_seconds == 300
    assert res.action.message == "Học bài"
    assert "5 phút" in res.action.label


def test_timer_minutes_with_nua():
    res = recognize_action("nhắc mình uống nước sau 10 phút nữa")
    assert res is not None
    assert res.action is not None
    assert res.action.type == "set_timer"
    assert res.action.duration_seconds == 600
    assert res.action.message == "Uống nước"


def test_timer_hours_recognition():
    res = recognize_action("nhắc tôi kiểm tra bài sau 2 giờ")
    assert res is not None
    assert res.action is not None
    assert res.action.type == "set_timer"
    assert res.action.duration_seconds == 7200
    assert res.action.message == "Kiểm tra bài"


def test_timer_hen_gio_form():
    res = recognize_action("hẹn giờ 30 phút để nghỉ")
    assert res is not None
    assert res.action is not None
    assert res.action.type == "set_timer"
    assert res.action.duration_seconds == 1800
    assert res.action.message == "Nghỉ"


def test_timer_missing_duration_asks_clarification():
    res = recognize_action("nhắc tôi học bài")
    assert res is not None
    assert res.action is None
    assert "sau bao lâu nữa" in res.reply


def test_timer_zero_or_negative_duration():
    res = recognize_action("hẹn giờ 0 phút")
    assert res is not None
    assert res.action is None
    assert "từ 1 phút trở lên" in res.reply


def test_timer_exceeds_max_24h():
    res = recognize_action("hẹn giờ 25 giờ")
    assert res is not None
    assert res.action is None
    assert "tối đa là 24 giờ" in res.reply


# =============================================================================
# 2. Calendar Unit Tests
# =============================================================================

def test_calendar_tomorrow_evening():
    res = recognize_action("đặt lịch nộp bài lúc 8 giờ tối mai")
    assert res is not None
    assert res.action is not None
    assert res.action.type == "create_calendar_event"
    assert res.action.title == "Nộp bài"
    assert res.action.start_at is not None
    assert res.action.end_at is not None
    # 8 giờ tối -> 20:00
    assert "T20:00:00+07:00" in res.action.start_at
    assert "T20:30:00+07:00" in res.action.end_at


def test_calendar_tomorrow_colon_time():
    res = recognize_action("nhắc tôi họp nhóm lúc 19:30 ngày mai")
    assert res is not None
    assert res.action is not None
    assert res.action.type == "create_calendar_event"
    assert res.action.title == "Họp nhóm"
    assert "T19:30:00+07:00" in res.action.start_at
    assert "T20:00:00+07:00" in res.action.end_at


def test_calendar_ambiguous_day_asks_clarification():
    res = recognize_action("đặt lịch học Android lúc 20:00")
    assert res is not None
    assert res.action is None
    assert "hôm nay hay ngày mai" in res.reply


def test_calendar_ambiguous_hour_asks_clarification():
    res = recognize_action("đặt lịch nộp bài lúc 8 giờ ngày mai")
    assert res is not None
    assert res.action is None
    assert "sáng hay tối" in res.reply


# =============================================================================
# 3. Map Search Unit Tests
# =============================================================================

def test_map_search_kma():
    res = recognize_action("tìm Học viện Kỹ thuật Mật mã trên bản đồ")
    assert res is not None
    assert res.action is not None
    assert res.action.type == "map_search"
    assert res.action.query == "Học viện Kỹ thuật Mật mã"
    assert res.action.label == "Mở bản đồ"


def test_map_search_ho_guom():
    res = recognize_action("mở bản đồ tìm Hồ Gươm")
    assert res is not None
    assert res.action is not None
    assert res.action.type == "map_search"
    assert res.action.query == "Hồ Gươm"


def test_map_search_chi_duong():
    res = recognize_action("chỉ đường đến Bảo tàng Hà Nội")
    assert res is not None
    assert res.action is not None
    assert res.action.type == "map_search"
    assert res.action.query == "Bảo tàng Hà Nội"


def test_map_search_missing_place_asks_clarification():
    res = recognize_action("mở bản đồ")
    assert res is not None
    assert res.action is None
    assert "địa điểm nào trên bản đồ" in res.reply


def test_map_search_rejects_raw_url():
    res = recognize_action("chỉ đường đến https://maps.google.com/xyz")
    assert res is not None
    assert res.action is None
    assert "bằng chữ thay vì đường dẫn" in res.reply


# =============================================================================
# 4. Non-Action / Regular Questions Fallthrough
# =============================================================================

@pytest.mark.parametrize(
    "normal_query",
    [
        "Học viện Kỹ thuật Mật mã ở đâu?",
        "Lịch thi học kỳ xem ở đâu?",
        "Cho mình biết thông tin tuyển sinh",
        "Xin chào Anna",
        "Cảm ơn bạn nhiều nhé",
        "Giải thích thuật toán RSA",
    ],
)
def test_normal_queries_bypass_action_recognition(normal_query):
    assert recognize_action(normal_query) is None


# =============================================================================
# 5. Route Integration Tests
# =============================================================================

def test_route_timer_returns_action_and_persists():
    client_id = str(uuid.uuid4())
    headers = {"X-Client-Id": client_id}

    # Create conversation
    create_resp = client.post("/api/v1/conversations", headers=headers, json={"title": "Test Actions"})
    assert create_resp.status_code == 200
    conv_id = create_resp.json()["id"]

    # Send timer message
    req_id = str(uuid.uuid4())
    msg_resp = client.post(
        f"/api/v1/conversations/{conv_id}/messages",
        headers=headers,
        json={"request_id": req_id, "message": "nhắc tôi học bài sau 5 phút"},
    )
    assert msg_resp.status_code == 200
    data = msg_resp.json()

    assert data["action"] is not None
    assert data["action"]["type"] == "set_timer"
    assert data["action"]["duration_seconds"] == 300
    assert data["action"]["message"] == "Học bài"
    assert data["sources"] == []
    assert data["assistant_message"]["emotion"] == "happy"

    # Verify idempotency replay returns same action
    replay_resp = client.post(
        f"/api/v1/conversations/{conv_id}/messages",
        headers=headers,
        json={"request_id": req_id, "message": "nhắc tôi học bài sau 5 phút"},
    )
    assert replay_resp.status_code == 200
    replay_data = replay_resp.json()
    assert replay_data["action"] is not None
    assert replay_data["action"]["type"] == "set_timer"
    assert replay_data["assistant_message"]["id"] == data["assistant_message"]["id"]


def test_route_map_search_returns_action():
    client_id = str(uuid.uuid4())
    headers = {"X-Client-Id": client_id}

    create_resp = client.post("/api/v1/conversations", headers=headers)
    assert create_resp.status_code == 200
    conv_id = create_resp.json()["id"]

    req_id = str(uuid.uuid4())
    msg_resp = client.post(
        f"/api/v1/conversations/{conv_id}/messages",
        headers=headers,
        json={"request_id": req_id, "message": "tìm Học viện Kỹ thuật Mật mã trên bản đồ"},
    )
    assert msg_resp.status_code == 200
    data = msg_resp.json()
    assert data["action"] is not None
    assert data["action"]["type"] == "map_search"
    assert data["action"]["query"] == "Học viện Kỹ thuật Mật mã"
