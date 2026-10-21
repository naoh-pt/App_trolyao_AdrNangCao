"""Map-only punctuation regression; every route test forbids external generation/retrieval."""

import uuid

import pytest

import ai_service
import app.api.v1.conversations as routes
import app.services.rag_service as rag
from app.db.connection import get_connection
from app.main import app
from app.services.assistant_action_service import recognize_action
from app.services.providers.gemini_provider import GeminiProvider
from app.services.providers.groq_provider import GroqProvider
from app.services.providers.provider_service import ProviderService


COMMANDS = [
    ("Tìm trên bản đồ Hồ Gươm", "Hồ Gươm"),
    ("Tìm trên bản đồ Hồ Gươm.", "Hồ Gươm"),
    ("Tìm trên bản đồ Hồ Gươm!", "Hồ Gươm"),
    ("Tìm trên bản đồ Hồ Gươm?", "Hồ Gươm"),
    ("Tìm trên bản đồ Hồ Gươm,", "Hồ Gươm"),
    ("Tìm bản đồ Học viện Kỹ thuật Mật mã.", "Học viện Kỹ thuật Mật mã"),
    ("Tìm đường đến Đại học Bách khoa Hà Nội.", "Đại học Bách khoa Hà Nội"),
]


@pytest.mark.parametrize("message,expected", COMMANDS)
def test_requested_map_commands(message, expected):
    result = recognize_action(message)
    assert result is not None and result.action is not None
    assert result.action.type == "map_search"
    assert result.action.query == expected
    assert result.action.label == "Mở bản đồ"
    assert result.emotion == "happy"


@pytest.mark.parametrize("suffix", ["   ", ".   ", "?!", ",;:", ". ! ? ; : ,  ", "\t.\n!\t"])
def test_suffix_punctuation_and_whitespace(suffix):
    result = recognize_action(f"  Tìm trên bản đồ Hồ Gươm{suffix}")
    assert result is not None and result.action.query == "Hồ Gươm"


@pytest.mark.parametrize("message,expected", [
    ("Tìm Hồ Gươm trên bản đồ.!", "Hồ Gươm"),
    ("mở bản đồ tìm Hồ Gươm?", "Hồ Gươm"),
    ("chỉ đường tới Hồ Gươm;", "Hồ Gươm"),
    ("bản đồ đến Hồ Gươm:", "Hồ Gươm"),
    ("Tìm trên bản đồ Bảo tàng A:B, St. John's - Q.1!", "Bảo tàng A:B, St. John's - Q.1"),
    ("Tìm Bảo tàng A:B, C-D. trên bản đồ!", "Bảo tàng A:B, C-D"),
])
def test_existing_forms_and_internal_punctuation(message, expected):
    result = recognize_action(message)
    assert result is not None and result.action.query == expected


@pytest.mark.parametrize("message", ["Tìm trên bản đồ", "Tìm bản đồ   ", "Tìm trên bản đồ .?!,;:  ", "mở bản đồ ..."])
def test_empty_query_has_no_map_action(message):
    result = recognize_action(message)
    assert result is not None and result.action is None


@pytest.mark.parametrize("message", [
    "Bản đồ là gì?",
    "Bạn có thể giải thích cách đọc bản đồ không?",
    "Tôi muốn học về bản đồ.",
    'Giải thích câu "Tìm trên bản đồ Hồ Gươm."',
    "Học viện Kỹ thuật Mật mã có bản đồ không?",
    "Tại sao bản đồ có nhiều ký hiệu?",
])
def test_map_conversation_is_not_an_action(message):
    assert recognize_action(message) is None


@pytest.mark.parametrize("query", [
    "https://example.com", "geo:0,0", "file:/private", "content:private",
    "javascript:alert(1)", "intent:foo", "custom:foo", "com.google.android.apps.maps", "org.example.maps",
])
def test_raw_schemes_and_packages_are_not_map_actions(query):
    result = recognize_action(f"Tìm trên bản đồ {query}!")
    assert result is not None and result.action is None


def test_timer_and_calendar_recognition_are_unchanged():
    timer = recognize_action("Nhắc tôi học bài sau 5 phút")
    assert timer.action.type == "set_timer"
    assert timer.action.duration_seconds == 300
    assert timer.action.message == "Học bài"
    calendar = recognize_action("đặt lịch nộp bài lúc 8 giờ tối mai")
    assert calendar.action.type == "create_calendar_event"
    assert calendar.action.title == "Nộp bài"
    assert calendar.action.start_at.endswith("T20:00:00+07:00")
    assert calendar.action.end_at.endswith("T20:30:00+07:00")


@pytest.mark.parametrize("message,expected", COMMANDS)
@pytest.mark.parametrize("real_ai_enabled", [False, True])
def test_route_schema_persistence_replay_and_no_providers(
    client, temp_db_file, monkeypatch, message, expected, real_ai_enabled,
):
    def forbidden(*args, **kwargs):
        pytest.fail("Map command reached quick reply, RAG, embedding, mock AI or provider generation")

    monkeypatch.setattr(routes, "USE_REAL_AI", real_ai_enabled)
    monkeypatch.setattr(routes, "RAG_ENABLED", True)
    for obj, attribute in [
        (routes, "get_quick_reply"), (routes, "retrieve"), (routes, "prompt_context"),
        (rag, "_embed"), (ai_service, "generate_reply"), (ai_service, "get_provider_service"),
        (routes.mock_ai, "generate_reply"), (ProviderService, "generate_reply"),
        (GeminiProvider, "generate_reply"), (GroqProvider, "generate_reply"),
    ]:
        monkeypatch.setattr(obj, attribute, forbidden)

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
    payload = {"request_id": request_id, "message": message}

    response = client.post(url, headers=headers, json=payload)
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"user_message", "assistant_message", "sources", "action"}
    assert body["sources"] == []
    action = body["action"]
    assert action == {
        "type": "map_search", "label": "Mở bản đồ", "query": expected,
        "message": None, "duration_seconds": None, "title": None, "start_at": None, "end_at": None,
    }
    assert set(body["user_message"]) == {"id", "role", "text", "emotion", "created_at"}
    assert set(body["assistant_message"]) == {"id", "role", "text", "emotion", "created_at", "action"}
    assert body["assistant_message"]["action"] == action
    assert body["user_message"]["text"] == message
    assert body["user_message"]["role"] == "user"
    assert body["user_message"]["emotion"] is None
    assert body["assistant_message"]["role"] == "assistant"
    assert body["assistant_message"]["emotion"] == "happy"
    assert f'"{expected}"' in body["assistant_message"]["text"]
    for role in ("user_message", "assistant_message"):
        assert str(uuid.UUID(body[role]["id"])) == body[role]["id"]
        assert body[role]["created_at"]

    replay = client.post(url, headers=headers, json={**payload, "message": f"  {message}  "})
    assert replay.status_code == 200
    assert replay.json() == body
    assert not any("SELECT role, text, emotion FROM (" in sql for sql in statements)
    # The existing persistence contract stores complete messages/request linkage and reconstructs
    # structured actions on replay; there is no separate action column/table to add or migrate.
    with get_connection(temp_db_file) as db:
        rows = db.execute("SELECT id, role, text, emotion, created_at FROM messages WHERE conversation_id = ? ORDER BY rowid", (conv_id,)).fetchall()
        expected_messages = [{key: value for key, value in body[role].items() if key != "action"}
                             for role in ("user_message", "assistant_message")]
        assert [dict(row) for row in rows] == expected_messages
        records = db.execute("SELECT * FROM idempotency_records WHERE conversation_id = ?", (conv_id,)).fetchall()
        assert len(records) == 1
        assert records[0]["request_id"] == request_id
        assert records[0]["normalized_message"] == message
        assert records[0]["user_message_id"] == body["user_message"]["id"]
        assert records[0]["assistant_message_id"] == body["assistant_message"]["id"]
        assert db.execute("SELECT COUNT(*) FROM message_sources").fetchone()[0] == 0
