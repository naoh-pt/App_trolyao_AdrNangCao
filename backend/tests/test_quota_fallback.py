"""Tests for structured quota classification and Anna's friendly quota fallback."""

import uuid
from unittest.mock import MagicMock, patch

import pytest
from google.genai.errors import ClientError, ServerError

import ai_service
import app.api.v1.conversations as routes
from app.db.connection import get_connection
from app.exceptions import (
    LLMQuotaExhaustedException,
    LLMTimeoutException,
    LLMUnavailableException,
    is_quota_exhausted_exception,
)
from app.services.personality import (
    ANNA_QUOTA_FALLBACK_EMOTION,
    ANNA_QUOTA_FALLBACK_TEXT,
)
from app.services.rag_service import RetrievedChunk


# ============================================================================
# 8.5 Structured Quota Classification Tests (Offline Fake Exceptions)
# ============================================================================

def test_custom_quota_exception_recognized():
    assert is_quota_exhausted_exception(LLMQuotaExhaustedException()) is True


def test_status_code_429_recognized():
    class Fake429Exception(Exception):
        status_code = 429

    assert is_quota_exhausted_exception(Fake429Exception()) is True


def test_code_429_recognized():
    class FakeCode429(Exception):
        code = 429

    assert is_quota_exhausted_exception(FakeCode429()) is True


def test_http_status_429_recognized():
    class FakeHttpStatus429(Exception):
        http_status = 429

    assert is_quota_exhausted_exception(FakeHttpStatus429()) is True


def test_resource_exhausted_status_recognized():
    class FakeResourceExhausted(Exception):
        status = "RESOURCE_EXHAUSTED"

    assert is_quota_exhausted_exception(FakeResourceExhausted()) is True


def test_resource_exhausted_reason_recognized():
    class FakeReasonExhausted(Exception):
        reason = "resource_exhausted"

    assert is_quota_exhausted_exception(FakeReasonExhausted()) is True


def test_attached_response_with_429_recognized():
    class FakeResponseException(Exception):
        def __init__(self):
            resp = MagicMock()
            resp.status_code = 429
            self.response = resp

    assert is_quota_exhausted_exception(FakeResponseException()) is True


def test_genai_client_error_429_recognized():
    err = ClientError(429, {"error": {"code": 429, "status": "RESOURCE_EXHAUSTED", "message": "Quota exceeded"}})
    assert is_quota_exhausted_exception(err) is True


def test_genai_client_error_403_not_quota():
    err = ClientError(403, {"error": {"code": 403, "status": "PERMISSION_DENIED", "message": "Bad API key"}})
    assert is_quota_exhausted_exception(err) is False


def test_genai_server_error_503_not_quota():
    err = ServerError(503, {"error": {"code": 503, "status": "UNAVAILABLE", "message": "Service unavailable"}})
    assert is_quota_exhausted_exception(err) is False


def test_timeout_not_treated_as_quota():
    assert is_quota_exhausted_exception(TimeoutError("request timed out")) is False
    assert is_quota_exhausted_exception(LLMTimeoutException()) is False


def test_generic_503_not_treated_as_quota():
    assert is_quota_exhausted_exception(LLMUnavailableException()) is False


def test_arbitrary_exception_with_quota_text_not_treated_as_quota():
    """Conservative check: word 'quota' in a message string without structured code must NOT match."""
    err = Exception("Random error containing the word quota in plain text")
    assert is_quota_exhausted_exception(err) is False


def test_unknown_exception_not_treated_as_quota():
    assert is_quota_exhausted_exception(RuntimeError("disk I/O error")) is False


# ============================================================================
# ai_service Exception Handling Unit Tests
# ============================================================================

def test_ai_service_raises_quota_exception_on_429():
    with patch("ai_service.client") as mock_client:
        err = ClientError(429, {"error": {"code": 429, "status": "RESOURCE_EXHAUSTED"}})
        mock_client.models.generate_content.side_effect = err

        with pytest.raises(LLMQuotaExhaustedException):
            ai_service.generate_reply([], "Câu hỏi kiểm tra")


def test_ai_service_raises_unavailable_on_auth_error():
    with patch("ai_service.client") as mock_client:
        err = ClientError(403, {"error": {"code": 403, "status": "PERMISSION_DENIED"}})
        mock_client.models.generate_content.side_effect = err

        with pytest.raises(LLMUnavailableException):
            ai_service.generate_reply([], "Câu hỏi kiểm tra")


def test_ai_service_raises_timeout_on_timeout():
    with patch("ai_service.client") as mock_client:
        mock_client.models.generate_content.side_effect = TimeoutError("Deadline exceeded")

        with pytest.raises(LLMTimeoutException):
            ai_service.generate_reply([], "Câu hỏi kiểm tra")


# ============================================================================
# Route Tests for Quota Fallback and Error Containment
# ============================================================================

def _chat(client):
    headers = {"X-Client-Id": str(uuid.uuid4())}
    res = client.post("/api/v1/conversations", headers=headers)
    assert res.status_code == 200
    return headers, res.json()["id"]


def test_real_ai_quota_fallback_returns_happy_contract_with_sad_emotion(
    client, temp_db_file, monkeypatch
):
    """When real AI fails with quota exhaustion:
    1. Returns HTTP 200 with normal Android response schema.
    2. Uses Anna's friendly quota fallback text.
    3. Emotion is 'sad'.
    4. Sources list is empty (even if RAG was run).
    5. User and assistant messages are saved to SQLite.
    6. Replay with same request_id does not call AI again.
    """
    monkeypatch.setattr(routes, "USE_REAL_AI", True)
    monkeypatch.setattr(routes, "RAG_ENABLED", True)

    source = RetrievedChunk("doc-1:0", "doc-1", "So_tay.pdf", 1, "Quy định", 0.85)
    monkeypatch.setattr(routes, "retrieve", lambda q: [source])

    calls = {"ai": 0}

    def failing_ai(context, message, rag_context):
        calls["ai"] += 1
        raise LLMQuotaExhaustedException()

    monkeypatch.setattr(ai_service, "generate_reply", failing_ai)

    headers, conv_id = _chat(client)
    req_id = str(uuid.uuid4())

    res = client.post(
        f"/api/v1/conversations/{conv_id}/messages",
        headers=headers,
        json={"request_id": req_id, "message": "Điều kiện làm khóa luận tốt nghiệp?"},
    )

    assert res.status_code == 200
    data = res.json()

    # Schema verification
    assert set(data.keys()) == {"user_message", "assistant_message", "sources"}
    assert data["sources"] == []

    u_msg = data["user_message"]
    a_msg = data["assistant_message"]

    assert u_msg["text"] == "Điều kiện làm khóa luận tốt nghiệp?"
    assert u_msg["role"] == "user"
    assert u_msg["emotion"] is None

    assert a_msg["role"] == "assistant"
    assert a_msg["text"] == ANNA_QUOTA_FALLBACK_TEXT
    assert a_msg["emotion"] == ANNA_QUOTA_FALLBACK_EMOTION  # "sad"

    # SQLite persistence verification
    with get_connection(temp_db_file) as db:
        rows = db.execute("SELECT role, text, emotion FROM messages WHERE conversation_id = ?", (conv_id,)).fetchall()
        assert len(rows) == 2
        assert rows[0]["role"] == "user"
        assert rows[1]["role"] == "assistant"
        assert rows[1]["text"] == ANNA_QUOTA_FALLBACK_TEXT
        assert rows[1]["emotion"] == "sad"

        # message_sources must be 0 because quota fallback answer did not use RAG
        src_count = db.execute("SELECT COUNT(*) FROM message_sources").fetchone()[0]
        assert src_count == 0

    # Idempotency replay check
    res_replay = client.post(
        f"/api/v1/conversations/{conv_id}/messages",
        headers=headers,
        json={"request_id": req_id, "message": "Điều kiện làm khóa luận tốt nghiệp?"},
    )
    assert res_replay.status_code == 200
    assert res_replay.json() == data
    assert calls["ai"] == 1  # AI was not called a second time


def test_mock_ai_quota_fallback_via_monkeypatch(client, temp_db_file, monkeypatch):
    """When mock AI raises a quota exception, Anna friendly fallback is returned."""
    def quota_fail(context, message):
        raise LLMQuotaExhaustedException("AI quota exhausted")

    monkeypatch.setattr(routes.mock_ai, "generate_reply", quota_fail)

    headers, conv_id = _chat(client)
    req_id = str(uuid.uuid4())

    res = client.post(
        f"/api/v1/conversations/{conv_id}/messages",
        headers=headers,
        json={"request_id": req_id, "message": "Câu hỏi trong lúc hết quota"},
    )

    assert res.status_code == 200
    data = res.json()
    assert data["assistant_message"]["text"] == ANNA_QUOTA_FALLBACK_TEXT
    assert data["assistant_message"]["emotion"] == "sad"
    assert data["sources"] == []

    with get_connection(temp_db_file) as db:
        cnt = db.execute("SELECT COUNT(*) FROM messages WHERE conversation_id = ?", (conv_id,)).fetchone()[0]
        assert cnt == 2


def test_literal_test_quota_string_is_not_treated_as_special_trigger(client, temp_db_file):
    """Regression check: literal '__TEST_QUOTA__' is normal text and never triggers quota fallback."""
    headers, conv_id = _chat(client)
    req_id = str(uuid.uuid4())

    res = client.post(
        f"/api/v1/conversations/{conv_id}/messages",
        headers=headers,
        json={"request_id": req_id, "message": "__TEST_QUOTA__"},
    )

    assert res.status_code == 200
    data = res.json()
    # It must NOT trigger quota fallback
    assert data["assistant_message"]["text"] != ANNA_QUOTA_FALLBACK_TEXT
    assert data["assistant_message"]["emotion"] != "sad"
    assert data["assistant_message"]["emotion"] == "neutral"
    assert "__TEST_QUOTA__" in data["assistant_message"]["text"]



def test_real_ai_auth_error_is_not_quota_and_saves_no_messages(client, temp_db_file, monkeypatch):
    """Authentication or configuration error returns 503 LLM_UNAVAILABLE without saving messages."""
    monkeypatch.setattr(routes, "USE_REAL_AI", True)
    monkeypatch.setattr(routes, "RAG_ENABLED", False)

    def auth_error(*args, **kwargs):
        raise LLMUnavailableException("API Key không hợp lệ")

    monkeypatch.setattr(ai_service, "generate_reply", auth_error)

    headers, conv_id = _chat(client)
    res = client.post(
        f"/api/v1/conversations/{conv_id}/messages",
        headers=headers,
        json={"request_id": str(uuid.uuid4()), "message": "Hỏi câu bình thường"},
    )

    assert res.status_code == 503
    err = res.json()["error"]
    assert err["code"] == "LLM_UNAVAILABLE"
    # Ensure raw SDK trace or sensitive text is not exposed
    assert "Traceback" not in err["message"]

    with get_connection(temp_db_file) as db:
        cnt = db.execute("SELECT COUNT(*) FROM messages WHERE conversation_id = ?", (conv_id,)).fetchone()[0]
        assert cnt == 0


def test_real_ai_timeout_is_not_quota_and_saves_no_messages(client, temp_db_file, monkeypatch):
    """Timeout error returns 504 LLM_TIMEOUT without saving messages."""
    monkeypatch.setattr(routes, "USE_REAL_AI", True)
    monkeypatch.setattr(routes, "RAG_ENABLED", False)

    def timeout_error(*args, **kwargs):
        raise LLMTimeoutException()

    monkeypatch.setattr(ai_service, "generate_reply", timeout_error)

    headers, conv_id = _chat(client)
    res = client.post(
        f"/api/v1/conversations/{conv_id}/messages",
        headers=headers,
        json={"request_id": str(uuid.uuid4()), "message": "Hỏi câu bình thường"},
    )

    assert res.status_code == 504
    err = res.json()["error"]
    assert err["code"] == "LLM_TIMEOUT"

    with get_connection(temp_db_file) as db:
        cnt = db.execute("SELECT COUNT(*) FROM messages WHERE conversation_id = ?", (conv_id,)).fetchone()[0]
        assert cnt == 0


def test_generic_503_is_not_converted_to_quota(client, temp_db_file, monkeypatch):
    """Generic 503 unavailable exception remains 503 and is NOT treated as quota exhaustion."""
    monkeypatch.setattr(routes, "USE_REAL_AI", True)
    monkeypatch.setattr(routes, "RAG_ENABLED", False)

    def generic_503(*args, **kwargs):
        raise LLMUnavailableException("Máy chủ AI tạm thời bận")

    monkeypatch.setattr(ai_service, "generate_reply", generic_503)

    headers, conv_id = _chat(client)
    res = client.post(
        f"/api/v1/conversations/{conv_id}/messages",
        headers=headers,
        json={"request_id": str(uuid.uuid4()), "message": "Hỏi câu bình thường"},
    )

    assert res.status_code == 503
    assert res.json()["error"]["code"] == "LLM_UNAVAILABLE"

    with get_connection(temp_db_file) as db:
        cnt = db.execute("SELECT COUNT(*) FROM messages WHERE conversation_id = ?", (conv_id,)).fetchone()[0]
        assert cnt == 0
