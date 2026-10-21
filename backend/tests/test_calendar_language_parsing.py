"""Deterministic calendar grammar, timezone and local-route regression tests."""

import uuid
from datetime import datetime, timedelta, timezone

import pytest

import ai_service
import app.api.v1.conversations as routes
import app.services.rag_service as rag
from app.db.connection import get_connection
from app.main import app
from app.services.assistant_action_service import (
    DEFAULT_CALENDAR_DURATION_MINUTES, VIETNAM_TZ, recognize_action,
)
from app.services.providers.gemini_provider import GeminiProvider
from app.services.providers.groq_provider import GroqProvider
from app.services.providers.provider_service import ProviderService


FIXED = datetime(2026, 10, 21, 11, tzinfo=VIETNAM_TZ)


@pytest.fixture
def now_vn():
    return FIXED


COMMANDS = [
    ("Tạo lịch học Android lúc 8 giờ tối ngày mai", "Học Android", "2026-10-22T20:00:00+07:00"),
    ("Tạo lịch học Android vào ngày mai lúc 8 giờ tối", "Học Android", "2026-10-22T20:00:00+07:00"),
    ("Tạo lịch học Android ngày mai lúc 20 giờ", "Học Android", "2026-10-22T20:00:00+07:00"),
    ("Tạo lịch học Android lúc 20:00 ngày mai", "Học Android", "2026-10-22T20:00:00+07:00"),
    ("Tạo lịch học Android lúc 8h30 tối ngày mai", "Học Android", "2026-10-22T20:30:00+07:00"),
    ("Thêm lịch họp nhóm ngày kia lúc 19 giờ", "Họp nhóm", "2026-10-23T19:00:00+07:00"),
    ("Tạo lịch ôn bài lúc 7 giờ sáng ngày kia", "Ôn bài", "2026-10-23T07:00:00+07:00"),
    ("Đặt lịch làm bài tập vào ngày kia lúc 20:30", "Làm bài tập", "2026-10-23T20:30:00+07:00"),
    ("Tạo lịch học vào hôm nay lúc 8 giờ tối", "Học", "2026-10-21T20:00:00+07:00"),
    ("Tạo lịch học lúc 8 giờ tối thứ 7 tuần này", "Học", "2026-10-24T20:00:00+07:00"),
    ("Tạo lịch học vào thứ 7 tuần này lúc 20 giờ", "Học", "2026-10-24T20:00:00+07:00"),
    ("Thêm lịch họp lúc 9 giờ sáng thứ 2 tuần sau", "Họp", "2026-10-26T09:00:00+07:00"),
    ("Tạo lịch ôn bài thứ hai tuần tới lúc 19:30", "Ôn bài", "2026-10-26T19:30:00+07:00"),
    ("Thêm lịch đi chơi lúc 8 giờ sáng chủ nhật tuần sau", "Đi chơi", "2026-11-01T08:00:00+07:00"),
    ("Tạo lịch học lúc 20 giờ thứ 7 tới", "Học", "2026-10-24T20:00:00+07:00"),
    ("Tạo lịch học vào 25/10 lúc 20 giờ", "Học", "2026-10-25T20:00:00+07:00"),
    ("Tạo lịch học lúc 20 giờ 25/10/2026", "Học", "2026-10-25T20:00:00+07:00"),
    ("Tạo lịch học ngày 25 tháng 10 lúc 20 giờ", "Học", "2026-10-25T20:00:00+07:00"),
    ("Tạo lịch học lúc 20 giờ ngày 25 tháng 10 năm 2026", "Học", "2026-10-25T20:00:00+07:00"),
]


def assert_event(result, title, expected_start):
    assert result is not None and result.action is not None
    action = result.action
    assert action.type == "create_calendar_event"
    assert action.label == "Mở lịch để xác nhận"
    assert action.title == title
    assert action.start_at == expected_start
    start = datetime.fromisoformat(action.start_at)
    end = datetime.fromisoformat(action.end_at)
    assert start.utcoffset() == end.utcoffset() == timedelta(hours=7)
    assert end > start
    assert end - start == timedelta(minutes=DEFAULT_CALENDAR_DURATION_MINUTES)
    assert DEFAULT_CALENDAR_DURATION_MINUTES == 30
    assert action.query is None and action.duration_seconds is None


@pytest.mark.parametrize("command,title,start", COMMANDS)
def test_supported_commands(command, title, start, now_vn):
    assert_event(recognize_action(command, now=now_vn), title, start)


@pytest.mark.parametrize("expression,day", [
    ("hôm nay", 21), ("ngày mai", 22), ("mai", 22), ("ngày kia", 23), ("ngày mốt", 23),
])
@pytest.mark.parametrize("date_first", [True, False])
def test_relative_dates_in_both_orders(expression, day, date_first, now_vn):
    tail = f"vào {expression} lúc 20 giờ" if date_first else f"lúc 20 giờ {expression}"
    assert_event(recognize_action(f"Tạo lịch học {tail}", now=now_vn), "Học", f"2026-10-{day}T20:00:00+07:00")


@pytest.mark.parametrize("expression,hour,minute", [
    ("8 giờ sáng", 8, 0), ("3 giờ chiều", 15, 0), ("8 giờ tối", 20, 0),
    ("12 giờ trưa", 12, 0), ("12 giờ đêm", 0, 0), ("20 giờ", 20, 0), ("20:30", 20, 30),
    ("8h sáng", 8, 0), ("8h30 tối", 20, 30), ("20h", 20, 0), ("20h30", 20, 30),
    ("8 giờ 30 tối", 20, 30), ("08:00", 8, 0), ("0 giờ", 0, 0), ("8 giờ buổi tối", 20, 0),
])
def test_time_formats(expression, hour, minute, now_vn):
    result = recognize_action(f"Tạo lịch học lúc {expression} ngày mai", now=now_vn)
    assert_event(result, "Học", f"2026-10-22T{hour:02}:{minute:02}:00+07:00")


WEEKDAYS = [("thứ 2", 0), ("thứ hai", 0), ("thứ 3", 1), ("thứ ba", 1),
            ("thứ 4", 2), ("thứ tư", 2), ("thứ 5", 3), ("thứ năm", 3),
            ("thứ 6", 4), ("thứ sáu", 4), ("thứ 7", 5), ("thứ bảy", 5), ("chủ nhật", 6)]


@pytest.mark.parametrize("weekday,number", WEEKDAYS)
@pytest.mark.parametrize("qualifier,week_offset", [("tuần này", 0), ("tuần sau", 7), ("tuần tới", 7)])
@pytest.mark.parametrize("date_first", [True, False])
def test_all_weekdays_qualifiers_and_word_orders(weekday, number, qualifier, week_offset, date_first, now_vn):
    tail = f"vào {weekday} {qualifier} lúc 20 giờ" if date_first else f"lúc 20 giờ {weekday} {qualifier}"
    result = recognize_action(f"Tạo lịch học {tail}", now=now_vn)
    if week_offset == 0 and number < now_vn.weekday():
        assert result.action is None and "đã qua" in result.reply
    else:
        monday = now_vn.date() - timedelta(days=now_vn.weekday())
        target = monday + timedelta(days=week_offset + number)
        assert_event(result, "Học", f"{target.isoformat()}T20:00:00+07:00")


@pytest.mark.parametrize("clock,expression,expected", [
    ("2026-01-31T11:00:00+07:00", "ngày mai", "2026-02-01"),
    ("2026-01-31T11:00:00+07:00", "ngày kia", "2026-02-02"),
    ("2026-12-30T11:00:00+07:00", "ngày kia", "2027-01-01"),
    ("2026-12-31T11:00:00+07:00", "mai", "2027-01-01"),
    ("2024-02-28T11:00:00+07:00", "ngày mai", "2024-02-29"),
    ("2024-02-28T11:00:00+07:00", "ngày kia", "2024-03-01"),
    ("2024-02-29T11:00:00+07:00", "ngày mai", "2024-03-01"),
    ("2026-12-30T11:00:00+07:00", "thứ hai tuần sau", "2027-01-04"),
    ("2026-10-25T11:00:00+07:00", "thứ 2 tuần sau", "2026-10-26"),
    ("2026-10-31T11:00:00+07:00", "chủ nhật tuần này", "2026-11-01"),
    ("2024-02-28T11:00:00+07:00", "thứ năm tuần này", "2024-02-29"),
    ("2026-10-26T11:00:00+07:00", "25/10", "2027-10-25"),
    ("2026-10-25T21:00:00+07:00", "25/10", "2027-10-25"),
    ("2025-01-01T11:00:00+07:00", "29/2", "2028-02-29"),
    ("2097-01-01T11:00:00+07:00", "29/2", "2104-02-29"),
])
def test_date_rollovers(clock, expression, expected):
    assert_event(recognize_action(f"Tạo lịch học {expression} lúc 20 giờ", now=datetime.fromisoformat(clock)),
                 "Học", expected + "T20:00:00+07:00")


@pytest.mark.parametrize("expression,hour,expected_date", [
    ("thứ 4 tuần này", 20, "2026-10-21"),
    ("thứ tư tới", 20, "2026-10-21"),
    ("thứ 4 tới", 8, "2026-10-28"),
    ("thứ hai tới", 20, "2026-10-26"),
])
def test_nearest_weekday_and_current_weekday_future(expression, hour, expected_date, now_vn):
    assert_event(recognize_action(f"Tạo lịch học lúc {hour:02}:00 {expression}", now=now_vn),
                 "Học", f"{expected_date}T{hour:02}:00:00+07:00")


@pytest.mark.parametrize("command,fragment", [
    ("Tạo lịch học hôm nay lúc 8 giờ sáng", "đã qua"),
    ("Tạo lịch học hôm nay lúc 11:00", "đã qua"),
    ("Tạo lịch học thứ tư tuần này lúc 8 giờ sáng", "đã qua"),
    ("Tạo lịch học thứ hai tuần này lúc 20 giờ", "đã qua"),
    ("Tạo lịch học thứ bảy lúc 20 giờ", "tuần này hay tuần sau"),
    ("Tạo lịch học cuối tuần này lúc 20 giờ", "thứ Bảy hay Chủ nhật"),
    ("Tạo lịch học cuối tuần sau lúc 20 giờ", "thứ Bảy hay Chủ nhật"),
    ("Tạo lịch học lúc 8 giờ ngày mai", "sáng hay tối"),
    ("Tạo lịch học lúc 8h ngày mai", "sáng hay tối"),
    ("Tạo lịch học lúc 8h30 ngày mai", "sáng hay tối"),
    ("Tạo lịch học lúc 20 giờ", "hôm nay hay ngày mai"),
    ("Tạo lịch học ngày mai buổi sáng", "mấy giờ"),
    ("Tạo lịch vào ngày mai lúc 20 giờ", "tên sự kiện"),
    ("Tạo lịch lúc 20 giờ ngày mai", "tên sự kiện"),
    ("Tạo lịch học 31/4/2027 lúc 20 giờ", "chưa hợp lệ"),
    ("Tạo lịch học 29/2/2027 lúc 20 giờ", "chưa hợp lệ"),
    ("Tạo lịch học 25/10/2025 lúc 20 giờ", "đã qua"),
    ("Tạo lịch học ngày mai hoặc ngày kia lúc 20 giờ", "một ngày"),
    ("Tạo lịch học ngày mai lúc 20 giờ hoặc 21 giờ", "một giờ"),
    ("Tạo lịch học ngày 25 tháng 10 năm 26 lúc 20 giờ", "một ngày"),
    ("Tạo lịch học ngày mai lúc 8 giờ sáng tối", "một buổi"),
])
def test_incomplete_ambiguous_or_past_commands_have_no_action(command, fragment, now_vn):
    result = recognize_action(command, now=now_vn)
    assert result is not None and result.action is None
    assert fragment in result.reply


@pytest.mark.parametrize("time", ["25 giờ", "24:00", "20:75", "8h99 tối", "-1 giờ sáng", "1.5 giờ chiều", "23 giờ sáng", "3 giờ trưa"])
def test_invalid_time_has_no_action(time, now_vn):
    result = recognize_action(f"Tạo lịch học lúc {time} ngày mai", now=now_vn)
    assert result is not None and result.action is None


@pytest.mark.parametrize("command", [
    "Lịch học là gì?", "Giải thích cách tạo lịch trên Android.", "Ngày kia nghĩa là gì?",
    "Học viện công bố lịch thi khi nào?", 'Viết câu có cụm từ “ngày mai lúc 8 giờ”.',
    "Thư viện mở cửa lúc 8 giờ sáng phải không?", "Thứ hai tuần sau nghĩa là gì?",
    "Giải thích câu Tạo lịch học lúc 20 giờ ngày mai.",
])
def test_conservative_non_matches(command, now_vn):
    assert recognize_action(command, now=now_vn) is None


def test_clock_conversion_uses_vietnam_date_and_rejects_naive_clock():
    utc = datetime(2026, 12, 31, 18, tzinfo=timezone.utc)  # Jan 1, 01:00 in Vietnam.
    assert_event(recognize_action("Tạo lịch học hôm nay lúc 20 giờ", now=utc), "Học", "2027-01-01T20:00:00+07:00")
    with pytest.raises(ValueError, match="timezone-aware"):
        recognize_action("Tạo lịch học hôm nay lúc 20 giờ", now=datetime(2026, 10, 21, 11))


def test_map_and_timer_are_preserved(now_vn):
    map_result = recognize_action("Tìm trên bản đồ Hồ Gươm.", now=now_vn)
    assert map_result.action.type == "map_search" and map_result.action.query == "Hồ Gươm"
    timer = recognize_action("Nhắc tôi học bài sau 5 phút", now=now_vn)
    assert timer.action.type == "set_timer" and timer.action.duration_seconds == 300
    assert timer.action.message == "Học bài"


@pytest.mark.parametrize("duration,seconds", [("5 phút", 300), ("2 giờ", 7200)])
def test_relative_timer_with_person_named_mai_is_not_calendar(duration, seconds, now_vn):
    result = recognize_action(f"Nhắc tôi gọi Mai sau {duration}", now=now_vn)
    assert result.action.type == "set_timer"
    assert result.action.message == "Gọi Mai"
    assert result.action.duration_seconds == seconds


@pytest.mark.parametrize("command,title,start", COMMANDS)
@pytest.mark.parametrize("real_ai", [False, True])
def test_route_schema_bypass_persistence_and_late_replay(client, temp_db_file, monkeypatch, command, title, start, real_ai):
    def forbidden(*args, **kwargs):
        pytest.fail("Local calendar reached quick replies, history/RAG/embedding, AI or providers")

    monkeypatch.setattr(routes, "USE_REAL_AI", real_ai)
    monkeypatch.setattr(routes, "RAG_ENABLED", True)
    for obj, attr in [
        (routes, "get_quick_reply"), (routes, "retrieve"), (routes, "prompt_context"), (rag, "_embed"),
        (ai_service, "generate_reply"), (ai_service, "get_provider_service"),
        (routes.mock_ai, "generate_reply"), (ProviderService, "generate_reply"),
        (GeminiProvider, "generate_reply"), (GroqProvider, "generate_reply"),
    ]:
        monkeypatch.setattr(obj, attr, forbidden)

    class Clock(datetime):
        current = FIXED

        @classmethod
        def now(cls, tz=None):
            return cls.current.astimezone(tz)

    monkeypatch.setattr(routes, "datetime", Clock)
    statements = []

    def traced_db():
        with get_connection(temp_db_file) as db:
            db.set_trace_callback(statements.append)
            yield db

    monkeypatch.setitem(app.dependency_overrides, routes.get_db, traced_db)
    headers = {"X-Client-Id": str(uuid.uuid4())}
    conversation = client.post("/api/v1/conversations", headers=headers)
    assert conversation.status_code == 200
    conv_id = conversation.json()["id"]
    request_id = str(uuid.uuid4())
    url = f"/api/v1/conversations/{conv_id}/messages"
    response = client.post(url, headers=headers, json={"request_id": request_id, "message": command})
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"user_message", "assistant_message", "sources", "action"}
    assert body["sources"] == []
    action = body["action"]
    assert action == {
        "type": "create_calendar_event", "label": "Mở lịch để xác nhận", "title": title,
        "start_at": start, "end_at": (datetime.fromisoformat(start) + timedelta(minutes=30)).isoformat(),
        "message": None, "duration_seconds": None, "query": None,
    }
    assert body["assistant_message"]["action"] == action
    assert set(body["user_message"]) == {"id", "role", "text", "emotion", "created_at"}
    assert set(body["assistant_message"]) == {"id", "role", "text", "emotion", "created_at", "action"}
    assert body["user_message"]["text"] == command
    assert body["assistant_message"]["emotion"] == "happy"
    for role in ("user_message", "assistant_message"):
        assert str(uuid.UUID(body[role]["id"])) == body[role]["id"]
        assert datetime.fromisoformat(body[role]["created_at"].replace("Z", "+00:00")) == FIXED

    # A week later the event may already be past; replay must retain the original action exactly.
    Clock.current += timedelta(days=14)
    replay = client.post(url, headers=headers, json={"request_id": request_id, "message": f"  {command}  "})
    assert replay.status_code == 200 and replay.json() == body
    assert not any("SELECT role, text, emotion FROM (" in sql for sql in statements)
    with get_connection(temp_db_file) as db:
        rows = db.execute("SELECT id, role, text, emotion, created_at FROM messages WHERE conversation_id = ? ORDER BY rowid", (conv_id,)).fetchall()
        expected_rows = [{k: v for k, v in body[role].items() if k != "action"}
                         for role in ("user_message", "assistant_message")]
        assert [dict(row) for row in rows] == expected_rows
        records = db.execute("SELECT * FROM idempotency_records WHERE conversation_id = ?", (conv_id,)).fetchall()
        assert len(records) == 1 and records[0]["request_id"] == request_id
        assert records[0]["normalized_message"] == command
        assert records[0]["user_message_id"] == body["user_message"]["id"]
        assert records[0]["assistant_message_id"] == body["assistant_message"]["id"]
        assert db.execute("SELECT COUNT(*) FROM message_sources").fetchone()[0] == 0


@pytest.mark.parametrize("command", [
    "Tạo lịch học ngày mai lúc 25 giờ", "Tạo lịch học ngày mai lúc 20:75",
    "Tạo lịch học ngày mai lúc 8 giờ", "Tạo lịch vào ngày mai lúc 20 giờ",
    "Tạo lịch học thứ bảy lúc 20 giờ", "Tạo lịch học cuối tuần sau lúc 20 giờ",
    "Tạo lịch học ngày 31 tháng 4 năm 2027 lúc 20 giờ",
])
def test_incomplete_calendar_route_has_no_action_button_and_bypasses_ai(client, monkeypatch, command):
    def forbidden(*args, **kwargs):
        pytest.fail("Calendar clarification reached generation or RAG")

    monkeypatch.setattr(routes, "USE_REAL_AI", True)
    monkeypatch.setattr(routes, "RAG_ENABLED", True)
    for obj, attr in [
        (routes, "get_quick_reply"), (routes, "retrieve"), (routes, "prompt_context"), (rag, "_embed"),
        (ai_service, "generate_reply"), (ai_service, "get_provider_service"),
        (routes.mock_ai, "generate_reply"), (ProviderService, "generate_reply"),
        (GeminiProvider, "generate_reply"), (GroqProvider, "generate_reply"),
    ]:
        monkeypatch.setattr(obj, attr, forbidden)
    headers = {"X-Client-Id": str(uuid.uuid4())}
    conversation = client.post("/api/v1/conversations", headers=headers).json()["id"]
    response = client.post(f"/api/v1/conversations/{conversation}/messages", headers=headers,
                           json={"request_id": str(uuid.uuid4()), "message": command})
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"user_message", "assistant_message", "sources"}
    assert "action" not in body["assistant_message"]
    assert body["sources"] == []
    assert body["assistant_message"]["text"]
