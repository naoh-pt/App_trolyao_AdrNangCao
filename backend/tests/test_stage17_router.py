"""Offline Stage 17 contracts: surface rules, trusted proposals and atomic slots."""
import json
import sqlite3
import unicodedata
import uuid
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace

import pytest
from app.api.v1 import conversations as routes
from app.db.connection import get_connection, init_db
from app.services.assistant_action_service import recognize_action, VIETNAM_TZ
from app.services.intent_normalization import normalize_intent
from app.services.intent_proposal import GeneratedReply, validate_proposal, proposal_command
from app.services.pending_calendar import plan_calendar, apply_calendar
from app.services.memory_service import parse_memory_command
from app.services.weather.intent import parse_weather_intent
from app.services.quick_reply_service import get_quick_reply

NOW = datetime(2026, 10, 21, 11, tzinfo=VIETNAM_TZ)


@pytest.fixture(autouse=True)
def clock(monkeypatch):
    class Clock(datetime):
        current = NOW
        @classmethod
        def now(cls, tz=None):
            return cls.current.astimezone(tz)
    monkeypatch.setattr(routes, "datetime", Clock)
    return Clock


def setup(client, owner=None):
    headers = {"X-Client-Id": owner or str(uuid.uuid4())}
    conv = client.post("/api/v1/conversations", headers=headers).json()["id"]
    return headers, conv


def send(client, headers, conv, text, rid=None):
    return client.post(f"/api/v1/conversations/{conv}/messages", headers=headers,
                       json={"message": text, "request_id": rid or str(uuid.uuid4())})


def forbidden(*args, **kwargs):
    pytest.fail("Deterministic path reached provider/RAG/Weather")


def forbid(monkeypatch):
    for obj, key in [(routes, "retrieve"), (routes, "get_weather_reply"),
                     (routes.ai_service, "generate_reply"), (routes.mock_ai, "generate_reply")]:
        monkeypatch.setattr(obj, key, forbidden)


@pytest.mark.parametrize("suffix", ["nhé?", "nha!", "với.", "giúp mình", "giúp tôi", "được không?", "giúp mình với!"])
def test_surface_wrappers_unicode_and_preserved_case(suffix):
    text = f"  Anna ơi,  Tìm trên bản đồ Hồ Gươm {suffix}  "
    normalized = normalize_intent(unicodedata.normalize("NFD", text))
    assert normalized == "Tìm trên bản đồ Hồ Gươm"
    assert recognize_action(normalized).action.query == "Hồ Gươm"


@pytest.mark.parametrize("command,kind", [
    ("Anna ơi, mấy giờ rồi nhé?", "time"),
    ("Này Anna, MẤY GIỜ RỒI nha!", "time"),
    ("Anna ơi, nhớ giúp mình là mình thích học Android nhé.", "memory"),
    ("Anna hãy nhớ: mình thi Android vào thứ Sáu tuần sau. Nhắc mình khi mở ứng dụng từ hôm nay nhé.", "memory"),
    ("Mở bản đồ tìm Hồ Gươm giúp mình với.", "map_search"),
    ("Anna dẫn mình đến Học viện Kỹ thuật Mật mã nhé.", "map_search"),
    ("Làm ơn tạo lịch học Android lúc 8 giờ tối ngày mai giúp mình.", "create_calendar_event"),
    ("Nhắc mình học bài sau 5 phút nhé.", "set_timer"),
    ("Ngày mai Hà Nội có mưa không vậy?", "weather"),
    ("Xin chào Anna, cho mình hỏi ngày mai Hà Nội có mưa không?", "weather"),
])
def test_natural_variants(command, kind):
    text = normalize_intent(command)
    if kind == "memory":
        assert parse_memory_command(text).operation == "save"
        assert "Android" in parse_memory_command(text).content
    elif kind == "weather":
        assert parse_weather_intent(text).location == "hà nội"
    elif kind == "time":
        assert get_quick_reply(text)
    else:
        assert recognize_action(text, now=NOW).action.type == kind


NEGATIVE = ["Giải thích bản đồ tư duy cho mình.", "Lịch sử Việt Nam có những giai đoạn nào?",
            "Thời tiết là gì trong khoa học?", "Đồng hồ cơ hoạt động thế nào?",
            "Giải thích áp lực khí quyển cho mình.", "Viết ví dụ về câu “ngày mai”.", "Ngày mai"]


@pytest.mark.parametrize("text", NEGATIVE)
def test_non_actions(text):
    text = normalize_intent(text)
    assert recognize_action(text, now=NOW) is None
    assert parse_weather_intent(text) is None
    assert parse_memory_command(text) is None
    assert proposal_command(proposal(), text) is None


def proposal(intent="map_search", slots=None, confidence=.92):
    return {"intent": intent, "confidence": confidence, "slots": {"query": "Hồ Gươm"} if slots is None else slots}


@pytest.mark.parametrize("value", [None, [], {}, "json", {"intent": "map_search"},
    proposal(confidence=.799), proposal(confidence=1.1), proposal(confidence=float("nan")),
    proposal(confidence=float("inf")), proposal(confidence=10**1000), proposal(confidence=True), proposal(intent="save_memory"),
    proposal(intent=[]), proposal(slots={"package": "com.google.maps"}), proposal(slots={"query": ["x"]}),
    proposal(slots={"query": {"nested": "x"}}), proposal(slots={"query": "x" * 201}),
    proposal(slots={"query": "https://example.com"}), proposal(slots={"query": "javascript:alert(1)"}),
    proposal(slots={"query": "com.google.android.apps.maps"}), proposal(slots={"query": "DROP TABLE messages"}),
    proposal(slots={"query": "cmd /c run"}), proposal(slots={"query": "a\nb"}),
    {**proposal(), "extra": "ignored?"}])
def test_reject_untrusted_proposals(value):
    assert validate_proposal(value) is None


def test_threshold_tuple_compatibility_and_slot_copy():
    value = proposal(confidence=.8)
    result = GeneratedReply("reply", "happy", value)
    assert result == ("reply", "happy") and len(result) == 2
    assert result.intent_proposal == value
    value["slots"]["query"] = "changed"
    assert result.intent_proposal["slots"]["query"] == "Hồ Gươm"
    assert proposal_command(result.intent_proposal, "Tìm một chỗ trên bản đồ") == "Tìm trên bản đồ Hồ Gươm"


@pytest.mark.parametrize("intent,slots", [
    ("create_calendar_event", {"title": "Học Android", "date_text": "ngày mai", "time_text": "8 giờ tối"}),
    ("map_search", {"query": "Hồ Gươm"}), ("set_timer", {"title": "Học", "duration_text": "5 phút"}),
])
def test_trusted_reparse(intent, slots):
    command = proposal_command(proposal(intent, slots), "Tôi muốn một lịch hoặc bản đồ hay hẹn giờ")
    assert recognize_action(command, now=NOW).action.type == intent


@pytest.mark.parametrize("slots", [
    {"title": "Học", "date_text": "ngày mai", "time_text": "25 giờ"},
    {"title": "Học", "date_text": "31/2/2027", "time_text": "20:30"},
])
def test_proposal_calendar_invalid_cannot_return_action(slots):
    command = proposal_command(proposal("create_calendar_event", slots), "Tôi muốn một lịch")
    assert recognize_action(command, now=NOW).action is None


@pytest.mark.parametrize("first,followups", [
    ("Tạo lịch học Android lúc 8 giờ tối", ["Ngày mai"]),
    ("Tạo lịch học Android vào ngày mai", ["8 giờ tối"]),
    ("Tạo cho mình một lịch", ["Học Android", "Ngày mai", "8 giờ tối"]),
    ("Tạo lịch lúc 8 giờ tối ngày mai", ["Học Android"]),
    ("Tạo lịch học Android", ["Tối mai lúc 8 giờ"]),
    ("Tạo lịch học Android", ["Học Android lúc 8 giờ tối ngày mai"]),
    ("Tạo lịch học Android lúc 8 giờ tối", ["Ngày kia"]),
    ("Tạo lịch học Android lúc 8 giờ tối", ["Thứ Bảy tuần này"]),
    ("Tạo lịch học Android lúc 8 giờ tối", ["Thứ Hai tuần sau"]),
    ("Tạo lịch học Android lúc 8 giờ tối", ["Ngày 25 tháng 10"]),
    ("Tạo lịch học Android vào ngày mai", ["7 giờ 30 sáng"]),
])
def test_pending_completion_and_replay(client, temp_db_file, monkeypatch, first, followups):
    forbid(monkeypatch)
    headers, conv = setup(client)
    start = send(client, headers, conv, first).json()
    assert "action" not in start and start["sources"] == []
    for index, text in enumerate(followups):
        rid = str(uuid.uuid4())
        response = send(client, headers, conv, text, rid)
        assert response.status_code == 200
        body = response.json()
        assert send(client, headers, conv, text, rid).json() == body
        if index < len(followups) - 1:
            assert "action" not in body
    action = body["action"]
    assert action["type"] == "create_calendar_event" and action["title"] == "Học Android"
    assert datetime.fromisoformat(action["end_at"]) - datetime.fromisoformat(action["start_at"]) == timedelta(minutes=30)
    with get_connection(temp_db_file) as db:
        assert db.execute("SELECT count(*) FROM pending_actions").fetchone()[0] == 0
        assert db.execute("SELECT count(*) FROM messages").fetchone()[0] == 2 * (1 + len(followups))
    assert body["assistant_message"]["action"] == action


@pytest.mark.parametrize("text", ["Thôi", "Bỏ qua", "Hủy", "Hủy tạo lịch", "Không cần nữa"])
def test_cancel_only_existing_state(client, temp_db_file, monkeypatch, text):
    forbid(monkeypatch)
    headers, conv = setup(client)
    send(client, headers, conv, "Tạo lịch học Android")
    rid = str(uuid.uuid4())
    result = send(client, headers, conv, text, rid).json()
    assert result["assistant_message"]["text"] == "Được rồi, Anna đã hủy thao tác tạo lịch."
    assert send(client, headers, conv, text, rid).json() == result
    with get_connection(temp_db_file) as db:
        assert not db.execute("SELECT 1 FROM pending_actions").fetchone()


def test_no_false_cancel_no_pending_and_ordinary_chat_one_call(client, monkeypatch):
    calls = []
    monkeypatch.setattr(routes.mock_ai, "generate_reply", lambda *args: calls.append(args) or ("Normal", "neutral"))
    headers, conv = setup(client)
    for text in ["Thôi", "Ngày mai", "Mình đang học Android."] + NEGATIVE:
        assert send(client, headers, conv, text).json()["assistant_message"]["text"] == "Normal"
    assert len(calls) == 3 + len(NEGATIVE)


def test_pending_isolation_expiry_unrelated_and_replacement(client, temp_db_file, monkeypatch, clock):
    headers, first = setup(client)
    _, second = setup(client, headers["X-Client-Id"])
    send(client, headers, first, "Tạo lịch học Android lúc 8 giờ tối")
    monkeypatch.setattr(routes.mock_ai, "generate_reply", lambda *a: ("Normal", "neutral"))
    assert "action" not in send(client, headers, second, "Ngày mai").json()
    stranger, _ = setup(client)
    assert send(client, stranger, first, "Ngày mai").status_code == 404
    for text in ["Mình buồn", "25 giờ", "20:75", "Giải thích API cho mình"]:
        result = send(client, headers, first, text).json()
        assert "action" not in result and "ngày nào" in result["assistant_message"]["text"]
    complete = send(client, headers, first, "Tạo lịch họp ngày kia lúc 20 giờ").json()
    assert complete["action"]["title"] == "Họp"
    send(client, headers, first, "Tạo lịch học Android lúc 8 giờ tối")
    clock.current += timedelta(minutes=11)
    assert send(client, headers, first, "Ngày mai").json()["assistant_message"]["text"] == "Normal"
    with get_connection(temp_db_file) as db:
        assert not db.execute("SELECT 1 FROM pending_actions").fetchone()


def test_pending_rollback_schema_and_concurrent_replay(client, temp_db_file, monkeypatch):
    forbid(monkeypatch)
    headers, conv = setup(client)
    send(client, headers, conv, "Tạo lịch học Android lúc 8 giờ tối")
    init_db(temp_db_file)  # Existing messages and pending survive repeat initialization.
    with get_connection(temp_db_file) as db:
        db.execute("CREATE TRIGGER fail_asst BEFORE INSERT ON messages WHEN NEW.role='assistant' BEGIN SELECT RAISE(ABORT, 'test'); END")
    with pytest.raises(sqlite3.IntegrityError):
        send(client, headers, conv, "Ngày mai")
    with get_connection(temp_db_file) as db:
        assert db.execute("SELECT count(*) FROM pending_actions").fetchone()[0] == 1
        assert db.execute("SELECT count(*) FROM messages").fetchone()[0] == 2
        db.execute("DROP TRIGGER fail_asst")
    rid = str(uuid.uuid4())
    with ThreadPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(lambda _: send(client, headers, conv, "Ngày mai", rid).json(), range(3)))
    assert all(result == results[0] for result in results)
    with get_connection(temp_db_file) as db:
        assert db.execute("SELECT count(*) FROM messages").fetchone()[0] == 4


def test_deterministic_memory_weather_and_timer_paths(client, temp_db_file, monkeypatch):
    forbid(monkeypatch)
    headers, conv = setup(client)
    memory = "Anna ơi, nhớ giúp mình là mình thích học Android nhé."
    assert send(client, headers, conv, memory).status_code == 200
    event = "Anna hãy nhớ: mình thi Android vào thứ Sáu tuần sau. Nhắc mình khi mở ứng dụng từ hôm nay nhé."
    assert send(client, headers, conv, event).status_code == 200
    with get_connection(temp_db_file) as db:
        rows = db.execute("SELECT content,remind_on FROM personal_memories ORDER BY rowid").fetchall()
        assert len(rows) == 2 and rows[0]["content"] == "bạn thích học Android"
        assert rows[1]["remind_on"] is not None
    assert send(client, headers, conv, "Nhắc mình học bài sau 5 phút nhé.").json()["action"]["duration_seconds"] == 300
    assert send(client, headers, conv, "Anna ơi, mấy giờ rồi nhé?").status_code == 200
    assert send(client, headers, conv, "Mở bản đồ tìm Hồ Gươm giúp mình với.").json()["action"]["query"] == "Hồ Gươm"
    weather_calls = []
    monkeypatch.setattr(routes, "get_weather_reply", lambda *a, **kw: weather_calls.append(a[0]) or ("Nguồn dữ liệu: Open-Meteo.", "neutral"))
    send(client, headers, conv, "Xin chào Anna, cho mình hỏi ngày mai Hà Nội có mưa không?")
    assert len(weather_calls) == 1


@pytest.mark.parametrize("intent,slots,original", [
    ("map_search", {"query": "Hồ Gươm"}, "Mình cần xem vị trí trên bản đồ"),
    ("create_calendar_event", {"title": "Học", "date_text": "ngày mai", "time_text": "20:30"}, "Mình cần một lịch để học"),
    ("weather_query", {"location": "Hà Nội", "date_text": "ngày mai"}, "Mình cần dự báo thời tiết ngày tới"),
    ("local_time_query", {"query": "mấy giờ rồi"}, "Cho mình biết mấy giờ ở đây"),
])
def test_same_generation_route_and_snapshot(client, monkeypatch, intent, slots, original):
    calls = []
    monkeypatch.setattr(routes, "USE_REAL_AI", True)
    monkeypatch.setattr(routes, "RAG_ENABLED", False)
    monkeypatch.setattr(routes.ai_service, "generate_reply", lambda *a: calls.append(a) or GeneratedReply("Normal", "neutral", proposal(intent, slots)))
    weather_calls = []
    monkeypatch.setattr(routes, "get_weather_reply", lambda *a, **kw: weather_calls.append(a) or ("Weather Open-Meteo", "happy"))
    headers, conv = setup(client)
    rid = str(uuid.uuid4())
    response = send(client, headers, conv, original, rid)
    assert response.status_code == 200
    result = response.json()
    if intent in {"map_search", "create_calendar_event"}:
        assert result["action"]["type"] == intent
    assert send(client, headers, conv, original, rid).json() == result
    assert len(calls) == 1 and len(weather_calls) == (1 if intent == "weather_query" else 0)


def test_both_providers_optional_proposal_and_fallback():
    from tests.test_provider_contracts import FakeGeminiClient, FakeGroqClient
    from app.services.providers.gemini_provider import GeminiProvider
    from app.services.providers.groq_provider import GroqProvider
    from app.services.providers.provider_service import ProviderService
    payload = json.dumps({"reply": "Normal", "emotion": "HAPPY", "intent_proposal": proposal()})
    gemini = GeminiProvider(api_key="test", client=FakeGeminiClient(response_text=payload))
    groq = GroqProvider(api_key="test", client=FakeGroqClient(content=payload))
    for provider in [gemini, groq]:
        result = provider.generate_reply([], "Mình cần bản đồ")
        assert result == ("Normal", "happy") and result.intent_proposal == proposal()
    failed = SimpleNamespace(name="fake", generate_reply=lambda *args: (_ for _ in ()).throw(TimeoutError()))
    assert ProviderService(failed, groq).generate_reply([], "Mình cần bản đồ").intent_proposal == proposal()


@pytest.mark.parametrize("first,question", [
    ("Tạo lịch học Android lúc 8 giờ tối", "Bạn muốn tạo lịch vào ngày nào?"),
    ("Tạo lịch học Android vào ngày mai", "Bạn muốn tạo lịch lúc mấy giờ?"),
    ("Tạo lịch lúc 20 giờ ngày mai", "Bạn muốn đặt tiêu đề lịch là gì?"),
    ("Tạo cho mình một lịch", "Bạn muốn tạo lịch gì, vào ngày nào và lúc mấy giờ?"),
])
def test_exact_missing_slot_question(client, monkeypatch, first, question):
    forbid(monkeypatch)
    headers, conv = setup(client)
    result = send(client, headers, conv, first).json()
    assert result["assistant_message"]["text"] == question
    assert "action" not in result


def test_invalid_date_keeps_pending_slots_and_provider_failure_cannot_consume(client, temp_db_file, monkeypatch):
    forbid(monkeypatch)
    headers, conv = setup(client)
    send(client, headers, conv, "Tạo lịch học Android lúc 20 giờ")
    with get_connection(temp_db_file) as db:
        before = dict(db.execute("SELECT * FROM pending_actions").fetchone())
    for text in ["Ngày 31 tháng 2 năm 2027", "Thứ Hai", "Giải thích API"]:
        assert "action" not in send(client, headers, conv, text).json()
        with get_connection(temp_db_file) as db:
            assert dict(db.execute("SELECT * FROM pending_actions").fetchone()) == before
    assert send(client, headers, conv, "Ngày mai").json()["action"]["type"] == "create_calendar_event"


def test_snapshot_retains_completed_followup_after_clock_change(client, monkeypatch, clock):
    forbid(monkeypatch)
    headers, conv = setup(client)
    send(client, headers, conv, "Tạo lịch học Android lúc 20 giờ")
    rid = str(uuid.uuid4())
    result = send(client, headers, conv, "Ngày mai", rid).json()
    clock.current += timedelta(days=100)
    assert send(client, headers, conv, "Ngày mai", rid).json() == result


def test_different_request_ids_cannot_complete_same_pending_twice(client, monkeypatch):
    headers, conv = setup(client)
    send(client, headers, conv, "Tạo lịch học Android lúc 20 giờ")
    monkeypatch.setattr(routes.mock_ai, "generate_reply", lambda *a: ("Normal", "neutral"))
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: send(client, headers, conv, "Ngày mai").json(), range(2)))
    assert sum("action" in result for result in results) == 1


@pytest.mark.parametrize("value", [None, proposal(confidence=.2), proposal(intent="save_memory"),
    proposal(slots={"query": "javascript:alert(1)"})])
def test_invalid_optional_proposal_preserves_normal_reply(client, monkeypatch, value):
    calls = []
    monkeypatch.setattr(routes.mock_ai, "generate_reply", lambda *a: calls.append(a) or GeneratedReply("Normal reply", "happy", value))
    headers, conv = setup(client)
    result = send(client, headers, conv, "Mình cần xem vị trí trên bản đồ").json()
    assert result["assistant_message"]["text"] == "Normal reply"
    assert "action" not in result and len(calls) == 1
