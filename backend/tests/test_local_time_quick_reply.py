"""Fixed-clock local time tests; route checks never invoke external services."""

import uuid
from datetime import datetime, timedelta, timezone

import pytest

import ai_service
import app.api.v1.conversations as routes
import app.services.rag_service as rag
from app.db.connection import get_connection
from app.services.providers.gemini_provider import GeminiProvider
from app.services.providers.groq_provider import GroqProvider
from app.services.providers.provider_service import ProviderService
from app.services.quick_reply_service import VIETNAM_TZ, get_quick_reply


FIXED = datetime(2026, 10, 12, 19, 34, tzinfo=VIETNAM_TZ)
QUESTIONS = [
    ("Mấy giờ rồi?", "Bây giờ là 19 giờ 34 phút nhé!"),
    ("Hôm nay là ngày bao nhiêu?", "Hôm nay là ngày 12/10/2026 nhé!"),
    ("Hôm nay là thứ mấy?", "Hôm nay là thứ Hai, ngày 12/10/2026 nhé!"),
    ("Bây giờ là buổi gì?", "Bây giờ là buổi tối nhé!"),
]


@pytest.mark.parametrize("message,expected", QUESTIONS)
def test_fixed_clock_formats(message, expected):
    assert get_quick_reply(message, now=FIXED) == (expected, "happy")


@pytest.mark.parametrize("message,fragment", [
    ("Bây giờ là mấy giờ?", "19 giờ 34 phút"),
    ("Hiện tại là mấy giờ", "19 giờ 34 phút"),
    ("Anna ơi, mấy giờ rồi?", "19 giờ 34 phút"),
    ("Cho mình hỏi bây giờ là mấy giờ", "19 giờ 34 phút"),
    ("  ANNA  ƠI, \n MẤY   GIỜ RỒI?!  ", "19 giờ 34 phút"),
    ("Anna oi, may gio roi?", "19 giờ 34 phút"),
    ("cho minh hoi bay gio la may gio", "19 giờ 34 phút"),
    ("Hôm nay ngày mấy?", "12/10/2026"),
    ("Ngày hôm nay là ngày bao nhiêu", "12/10/2026"),
    ("Anna ơi, hôm nay ngày bao nhiêu?", "12/10/2026"),
    ("hom nay ngay may", "12/10/2026"),
    ("Hôm nay thứ mấy", "thứ Hai"),
    ("Anna ơi, hôm nay là thứ mấy?", "thứ Hai"),
    ("HOM NAY LA THU MAY...", "thứ Hai"),
    ("Hiện tại đang là buổi sáng hay tối?", "buổi tối"),
    ("bay gio la buoi gi?", "buổi tối"),
])
def test_variants(message, fragment):
    assert fragment in get_quick_reply(message, now=FIXED)[0]


@pytest.mark.parametrize("offset,weekday", enumerate([
    "thứ Hai", "thứ Ba", "thứ Tư", "thứ Năm", "thứ Sáu", "thứ Bảy", "Chủ nhật",
]))
def test_all_weekdays(offset, weekday):
    day = FIXED + timedelta(days=offset)
    assert get_quick_reply("Hôm nay thứ mấy?", now=day) == (
        f"Hôm nay là {weekday}, ngày {day:%d/%m/%Y} nhé!", "happy",
    )


@pytest.mark.parametrize("hour,minute,period", [
    (0, 0, "ban đêm"), (4, 59, "ban đêm"), (5, 0, "buổi sáng"),
    (10, 59, "buổi sáng"), (11, 0, "buổi trưa"), (12, 59, "buổi trưa"),
    (13, 0, "buổi chiều"), (17, 59, "buổi chiều"), (18, 0, "buổi tối"),
    (22, 59, "buổi tối"), (23, 0, "ban đêm"), (23, 59, "ban đêm"),
])
def test_day_period_boundaries(hour, minute, period):
    assert get_quick_reply("Bây giờ là buổi gì?", now=FIXED.replace(hour=hour, minute=minute)) == (
        f"Bây giờ là {period} nhé!", "happy",
    )


def test_utc_conversion_crosses_date_and_weekday():
    utc = datetime(2026, 10, 11, 17, 4, tzinfo=timezone.utc)
    assert get_quick_reply("Mấy giờ rồi?", now=utc)[0] == "Bây giờ là 00 giờ 04 phút nhé!"
    assert get_quick_reply("Hôm nay thứ mấy?", now=utc)[0] == "Hôm nay là thứ Hai, ngày 12/10/2026 nhé!"


def test_naive_clock_rejected_without_machine_timezone_assumption():
    with pytest.raises(ValueError, match="timezone-aware"):
        get_quick_reply("Mấy giờ rồi?", now=datetime(2026, 10, 12))


@pytest.mark.parametrize("message", [
    'Giải thích câu "mấy giờ rồi" bằng tiếng Anh',
    "Viết đoạn hội thoại có câu mấy giờ rồi",
    "Tại sao con người chia một ngày thành 24 giờ?",
    "Học phí hiện tại là bao nhiêu?", "Thư viện mở cửa lúc mấy giờ?",
    "Mấy giờ ngày mai tôi nên học bài?", "Nhắc tôi học bài sau 5 phút",
    "Đặt lịch học lúc 8 giờ tối", "Tạo lịch vào ngày mai",
    "Tìm đường đến trường lúc 7 giờ", "hẹn giờ 5 phút",
    "mở bản đồ tìm Hồ Gươm", "Còn bao lâu đến 8 giờ tối?",
    "Mấy giờ rồi và học phí bao nhiêu?", "Hôm nay ngày mấy, có lịch thi không?",
    'Dịch "hôm nay là thứ mấy"', "Ngày mai là thứ mấy?",
    "Anna ơi, mấy giờ rồi, nhắc tôi học bài", "bay gio la may gio de dat lich",
])
def test_conservative_nonmatches(message):
    assert get_quick_reply(message, now=FIXED) is None


@pytest.mark.parametrize("message,expected", QUESTIONS)
def test_route_schema_persistence_replay_and_no_ai(client, temp_db_file, monkeypatch, message, expected):
    def forbidden(*args, **kwargs):
        pytest.fail("Local reply reached history, RAG, embedding, or AI")

    monkeypatch.setattr(routes, "USE_REAL_AI", True)
    monkeypatch.setattr(routes, "RAG_ENABLED", True)
    for obj, attr in [
        (routes, "retrieve"), (routes, "prompt_context"), (rag, "_embed"),
        (ai_service, "generate_reply"), (ai_service, "get_provider_service"),
        (routes.mock_ai, "generate_reply"), (ProviderService, "generate_reply"),
        (GeminiProvider, "generate_reply"), (GroqProvider, "generate_reply"),
    ]:
        monkeypatch.setattr(obj, attr, forbidden)

    calls = []

    def fixed_reply(text):
        calls.append(text)
        return get_quick_reply(text, now=FIXED)

    monkeypatch.setattr(routes, "get_quick_reply", fixed_reply)
    headers = {"X-Client-Id": str(uuid.uuid4())}
    conv = client.post("/api/v1/conversations", headers=headers).json()["id"]
    request_id = str(uuid.uuid4())
    payload = {"request_id": request_id, "message": message}
    statements = []
    original_connection = routes.get_db

    # Observe route SQL using the fixture's same isolated database.
    def traced_db():
        with get_connection(temp_db_file) as db:
            db.set_trace_callback(statements.append)
            yield db

    from app.main import app
    monkeypatch.setitem(app.dependency_overrides, original_connection, traced_db)
    url = f"/api/v1/conversations/{conv}/messages"
    first = client.post(url, headers=headers, json=payload)
    assert first.status_code == 200
    body = first.json()
    assert set(body) == {"user_message", "assistant_message", "sources"}
    assert body["sources"] == []
    for role in ("user", "assistant"):
        msg = body[f"{role}_message"]
        assert set(msg) == {"id", "role", "text", "emotion", "created_at"}
        assert msg["role"] == role
        assert str(uuid.UUID(msg["id"])) == msg["id"]
        assert msg["created_at"]
    assert body["user_message"]["text"] == message
    assert body["user_message"]["emotion"] is None
    assert body["assistant_message"]["text"] == expected
    assert body["assistant_message"]["emotion"] == "happy"
    assert not any("SELECT role, text, emotion FROM (" in sql for sql in statements)

    # A retry must use the saved answer even if time has moved forward.
    monkeypatch.setattr(routes, "get_quick_reply", forbidden)
    replay = client.post(url, headers=headers, json={**payload, "message": f"  {message}  "})
    assert replay.status_code == 200
    assert replay.json() == body
    assert calls == [message]
    with get_connection(temp_db_file) as db:
        rows = db.execute("SELECT id, role, text, emotion, created_at FROM messages WHERE conversation_id = ? ORDER BY rowid", (conv,)).fetchall()
        assert [dict(row) for row in rows] == [body["user_message"], body["assistant_message"]]
        record = db.execute("SELECT * FROM idempotency_records WHERE request_id = ?", (request_id,)).fetchone()
        assert record["normalized_message"] == message
        assert record["user_message_id"] == body["user_message"]["id"]
        assert record["assistant_message_id"] == body["assistant_message"]["id"]
        assert db.execute("SELECT COUNT(*) FROM message_sources").fetchone()[0] == 0
