"""Real-mode route wiring with fake retrieval and generation, never a provider call."""

import uuid

import pytest

import ai_service
import app.api.v1.conversations as routes
from app.db.connection import get_connection
from app.exceptions import LLMTimeoutException, LLMUnavailableException, RAGUnavailableException
from app.services.rag_service import RetrievedChunk


def _conversation(client):
    headers = {"X-Client-Id": str(uuid.uuid4())}
    response = client.post("/api/v1/conversations", headers=headers)
    assert response.status_code == 200
    return headers, response.json()["id"]


def _send(client, headers, conversation_id, request_id=None):
    return client.post(
        f"/api/v1/conversations/{conversation_id}/messages",
        headers=headers,
        json={"request_id": request_id or str(uuid.uuid4()), "message": "Điều kiện học bổng?"},
    )


@pytest.fixture
def real_mode(monkeypatch):
    monkeypatch.setattr(routes, "USE_REAL_AI", True)
    monkeypatch.setattr(routes, "RAG_ENABLED", True)


def test_rag_success_adds_context_and_preserves_android_schema(client, temp_db_file, monkeypatch, real_mode):
    source = RetrievedChunk("doc-1:0", "doc-1", "Sổ tay.pdf", 2, "Điều kiện học bổng", 0.9)
    with get_connection(temp_db_file) as db:
        db.execute(
            "INSERT INTO knowledge_documents (id, filename, sha256, page_count, chunk_count, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            ("doc-1", "Sổ tay.pdf", "test-sha", 1, 1, "2026-01-01T00:00:00Z"),
        )
    monkeypatch.setattr(routes, "retrieve", lambda question: [source])
    seen = []

    def generate(context, message, rag_context):
        seen.append((context, message, rag_context))
        return "  Học bổng theo sổ tay.  ", "happy"

    monkeypatch.setattr(ai_service, "generate_reply", generate)
    headers, conversation_id = _conversation(client)
    response = _send(client, headers, conversation_id)
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"user_message", "assistant_message", "sources"}
    assert set(body["assistant_message"]) == {"id", "role", "text", "emotion", "created_at"}
    assert body["assistant_message"]["text"] == "Học bổng theo sổ tay."
    assert body["assistant_message"]["emotion"] == "happy"
    assert body["user_message"]["emotion"] is None
    assert body["sources"] == [{"document_id": "doc-1", "filename": "Sổ tay.pdf", "page_number": 2, "score": 0.9}]
    assert seen[0][1] == "Điều kiện học bổng?"
    assert "Sổ tay.pdf, trang 2" in seen[0][2]
    assert "Điều kiện học bổng" in seen[0][2]
    with get_connection(temp_db_file) as db:
        assert db.execute("SELECT COUNT(*) FROM message_sources").fetchone()[0] == 1


def test_empty_rag_uses_normal_generation_and_additive_empty_sources(client, monkeypatch, real_mode):
    monkeypatch.setattr(routes, "retrieve", lambda question: [])
    seen = []
    monkeypatch.setattr(ai_service, "generate_reply", lambda context, message, rag_context: seen.append(rag_context) or ("Bình thường", "neutral"))
    headers, conversation_id = _conversation(client)
    response = _send(client, headers, conversation_id)
    assert response.status_code == 200
    assert response.json()["sources"] == []
    assert seen == [None]


def test_controlled_rag_failure_falls_back_without_http_500(client, monkeypatch, real_mode, caplog):
    def fail(question):
        raise RAGUnavailableException(category="collection_query")

    monkeypatch.setattr(routes, "retrieve", fail)
    seen = []
    monkeypatch.setattr(ai_service, "generate_reply", lambda context, message, rag_context: seen.append(rag_context) or ("Trả lời thường", "neutral"))
    headers, conversation_id = _conversation(client)
    response = _send(client, headers, conversation_id)
    assert response.status_code == 200
    assert response.json()["assistant_message"]["text"] == "Trả lời thường"
    assert response.json()["sources"] == []
    assert seen == [None]
    assert "collection_query" in caplog.text
    assert "Traceback" not in caplog.text


@pytest.mark.parametrize("failure,expected", [(LLMUnavailableException(), 503), (LLMTimeoutException(), 504)])
def test_generation_failure_keeps_controlled_error_and_no_messages(client, temp_db_file, monkeypatch, real_mode, failure, expected):
    monkeypatch.setattr(routes, "retrieve", lambda question: [])
    monkeypatch.setattr(ai_service, "generate_reply", lambda *args: (_ for _ in ()).throw(failure))
    headers, conversation_id = _conversation(client)
    response = _send(client, headers, conversation_id)
    assert response.status_code == expected
    assert response.json()["error"]["code"] in {"LLM_UNAVAILABLE", "LLM_TIMEOUT"}
    with get_connection(temp_db_file) as db:
        assert db.execute("SELECT COUNT(*) FROM messages WHERE conversation_id = ?", (conversation_id,)).fetchone()[0] == 0


def test_rag_disabled_never_retrieves(client, monkeypatch, real_mode):
    monkeypatch.setattr(routes, "RAG_ENABLED", False)
    monkeypatch.setattr(routes, "retrieve", lambda question: pytest.fail("retrieval was called"))
    monkeypatch.setattr(ai_service, "generate_reply", lambda context, message, rag_context: ("Không RAG", "neutral") if rag_context is None else pytest.fail("unexpected RAG context"))
    headers, conversation_id = _conversation(client)
    response = _send(client, headers, conversation_id)
    assert response.status_code == 200
    assert response.json()["sources"] == []


def test_invalid_emotion_becomes_neutral(client, monkeypatch, real_mode):
    monkeypatch.setattr(routes, "retrieve", lambda question: [])
    monkeypatch.setattr(ai_service, "generate_reply", lambda context, message, rag_context: ("Trả lời", "ANGRY"))
    headers, conversation_id = _conversation(client)
    response = _send(client, headers, conversation_id)
    assert response.status_code == 200
    assert response.json()["assistant_message"]["emotion"] == "neutral"


def test_retry_same_request_id_does_not_call_provider_again(client, temp_db_file, monkeypatch, real_mode):
    calls = {"rag": 0, "ai": 0}

    def retrieve(question):
        calls["rag"] += 1
        return []

    def generate(context, message, rag_context):
        calls["ai"] += 1
        return "Một câu trả lời", "neutral"

    monkeypatch.setattr(routes, "retrieve", retrieve)
    monkeypatch.setattr(ai_service, "generate_reply", generate)
    headers, conversation_id = _conversation(client)
    request_id = str(uuid.uuid4())
    first = _send(client, headers, conversation_id, request_id)
    second = _send(client, headers, conversation_id, request_id)
    assert first.status_code == second.status_code == 200
    assert first.json() == second.json()
    assert calls == {"rag": 1, "ai": 1}
    with get_connection(temp_db_file) as db:
        assert db.execute("SELECT COUNT(*) FROM messages WHERE conversation_id = ?", (conversation_id,)).fetchone()[0] == 2


def test_missing_gemini_key_in_real_mode_is_controlled(client, monkeypatch, real_mode):
    monkeypatch.setattr(routes, "RAG_ENABLED", False)
    monkeypatch.setattr(ai_service, "client", None)
    headers, conversation_id = _conversation(client)
    response = _send(client, headers, conversation_id)
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "LLM_UNAVAILABLE"
