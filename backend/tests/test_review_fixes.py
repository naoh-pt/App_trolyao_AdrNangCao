"""Regression checks for the independent backend review findings."""

import concurrent.futures
import sqlite3
import threading
import time
import uuid

import pytest

import app.api.v1.conversations as conversation_routes
import app.services.mock_ai as mock_ai
import app.services.request_guard as request_guard
from app.db.connection import get_connection


def _chat(client):
    headers = {"X-Client-Id": str(uuid.uuid4())}
    conv = client.post("/api/v1/conversations", headers=headers)
    assert conv.status_code == 200
    return headers, conv.json()["id"]


def _send(client, headers, conv_id, message="hello", request_id=None):
    return client.post(
        f"/api/v1/conversations/{conv_id}/messages",
        headers=headers,
        json={"request_id": request_id or str(uuid.uuid4()), "message": message},
    )


@pytest.mark.parametrize("result", [("", "neutral"), (" \t ", "happy"), (None, "neutral"), (42, "neutral"), None])
def test_invalid_ai_reply_is_retryable_and_never_saved(client, temp_db_file, monkeypatch, result):
    headers, conv_id = _chat(client)
    monkeypatch.setattr(mock_ai, "generate_reply", lambda context, message: result)
    response = _send(client, headers, conv_id)
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "LLM_UNAVAILABLE"
    db = get_connection(temp_db_file)
    try:
        assert db.execute("SELECT COUNT(*) FROM messages").fetchone()[0] == 0
        assert db.execute("SELECT COUNT(*) FROM idempotency_records").fetchone()[0] == 0
    finally:
        db.close()


@pytest.mark.parametrize("emotion", [None, 42, "unknown", "HAPPY"])
def test_invalid_emotion_is_neutral_in_response_and_database(client, temp_db_file, monkeypatch, emotion):
    headers, conv_id = _chat(client)
    monkeypatch.setattr(mock_ai, "generate_reply", lambda context, message: ("  answer  ", emotion))
    response = _send(client, headers, conv_id)
    assert response.status_code == 200
    assert response.json()["assistant_message"]["emotion"] == "neutral"
    assert response.json()["assistant_message"]["text"] == "answer"
    db = get_connection(temp_db_file)
    try:
        row = db.execute("SELECT emotion, text FROM messages WHERE role = 'assistant'").fetchone()
        assert (row["emotion"], row["text"]) == ("neutral", "answer")
    finally:
        db.close()


def test_overlapping_same_id_invokes_ai_once(client, temp_db_file, monkeypatch):
    headers, conv_id = _chat(client)
    req_id = str(uuid.uuid4())
    entered_ai = threading.Event()
    release_ai = threading.Event()
    calls = []

    def slow_ai(context, message):
        calls.append(1)
        entered_ai.set()
        assert release_ai.wait(5)
        return "answer", "happy"

    monkeypatch.setattr(mock_ai, "generate_reply", slow_ai)
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(_send, client, headers, conv_id, "same", req_id)
        assert entered_ai.wait(5)
        second = pool.submit(_send, client, headers, conv_id, "same", req_id)
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            with request_guard._registry_lock:
                entry = request_guard._entries.get(req_id)
                if entry is not None and entry.users == 2:
                    break
            time.sleep(0.01)
        else:
            release_ai.set()
            pytest.fail("second request did not overlap the first")
        release_ai.set()
        responses = [first.result(timeout=5), second.result(timeout=5)]

    assert [r.status_code for r in responses] == [200, 200]
    assert responses[0].json() == responses[1].json()
    assert len(calls) == 1
    db = get_connection(temp_db_file)
    try:
        assert db.execute("SELECT COUNT(*) FROM messages").fetchone()[0] == 2
    finally:
        db.close()
    with request_guard._registry_lock:
        assert req_id not in request_guard._entries


def test_request_wait_is_bounded(client, monkeypatch):
    headers, conv_id = _chat(client)
    req_id = str(uuid.uuid4())
    entered_ai = threading.Event()
    release_ai = threading.Event()
    monkeypatch.setattr(request_guard, "WAIT_SECONDS", 0.1)

    def slow_ai(context, message):
        entered_ai.set()
        assert release_ai.wait(5)
        return "answer", "neutral"

    monkeypatch.setattr(mock_ai, "generate_reply", slow_ai)
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        first = pool.submit(_send, client, headers, conv_id, "same", req_id)
        assert entered_ai.wait(5)
        waiting = _send(client, headers, conv_id, "same", req_id)
        release_ai.set()
        assert first.result(timeout=5).status_code == 200
    assert waiting.status_code == 503
    assert waiting.json()["error"]["code"] == "REQUEST_IN_PROGRESS"
    assert _send(client, headers, conv_id, "same", req_id).status_code == 200
    with request_guard._registry_lock:
        assert req_id not in request_guard._entries


def test_deletion_during_ai_returns_404_without_orphans(client, temp_db_file, monkeypatch):
    headers, conv_id = _chat(client)

    def delete_during_ai(context, message):
        db = get_connection(temp_db_file)
        try:
            with db:
                db.execute("DELETE FROM conversations WHERE id = ?", (conv_id,))
        finally:
            db.close()
        return "answer", "neutral"

    monkeypatch.setattr(mock_ai, "generate_reply", delete_during_ai)
    response = _send(client, headers, conv_id)
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"
    db = get_connection(temp_db_file)
    try:
        assert db.execute("SELECT COUNT(*) FROM messages").fetchone()[0] == 0
        assert db.execute("SELECT COUNT(*) FROM idempotency_records").fetchone()[0] == 0
    finally:
        db.close()


def test_conversation_recency_within_second_and_legacy_timestamp(client, monkeypatch):
    times = iter([
        "2030-01-01T00:00:00Z",
        "2030-01-01T00:00:00.100000Z",
        "2030-01-01T00:00:00.200000Z",
    ])
    monkeypatch.setattr(conversation_routes, "utc_now_iso", lambda: next(times))
    headers, older = _chat(client)
    newer = client.post("/api/v1/conversations", headers=headers).json()["id"]
    assert _send(client, headers, older).status_code == 200
    items = client.get("/api/v1/conversations", headers=headers).json()["items"]
    assert [item["id"] for item in items] == [older, newer]
    assert items[0]["updated_at"] == "2030-01-01T00:00:00.200000Z"


def test_sqlite_write_lock_returns_retryable_error_then_succeeds(client, temp_db_file):
    headers = {"X-Client-Id": str(uuid.uuid4())}
    blocker = get_connection(temp_db_file)
    try:
        blocker.execute("BEGIN IMMEDIATE")
        response = client.post("/api/v1/conversations", headers=headers)
        assert response.status_code == 503
        assert response.json()["error"]["code"] == "DATABASE_BUSY"
        assert response.headers["Retry-After"] == "1"
    finally:
        blocker.rollback()
        blocker.close()
    assert client.post("/api/v1/conversations", headers=headers).status_code == 200


def test_send_busy_rolls_back_and_same_id_can_retry(client, temp_db_file, monkeypatch):
    headers, conv_id = _chat(client)
    req_id = str(uuid.uuid4())
    calls = []

    def fake_ai(context, message):
        calls.append(1)
        return "answer", "neutral"

    monkeypatch.setattr(mock_ai, "generate_reply", fake_ai)
    blocker = get_connection(temp_db_file)
    try:
        blocker.execute("BEGIN IMMEDIATE")
        busy = _send(client, headers, conv_id, "retry me", req_id)
        assert busy.status_code == 503
        assert busy.json()["error"]["code"] == "DATABASE_BUSY"
    finally:
        blocker.rollback()
        blocker.close()
    sent = _send(client, headers, conv_id, "retry me", req_id)
    repeated = _send(client, headers, conv_id, "retry me", req_id)
    assert sent.status_code == repeated.status_code == 200
    assert sent.json() == repeated.json()
    assert len(calls) == 2  # The failed write had no committed result to reuse.
    db = get_connection(temp_db_file)
    try:
        assert db.execute("SELECT COUNT(*) FROM messages").fetchone()[0] == 2
    finally:
        db.close()


def test_legacy_and_precise_message_order_is_stable(client, temp_db_file, monkeypatch):
    headers, conv_id = _chat(client)
    legacy_id = str(uuid.uuid4())
    db = get_connection(temp_db_file)
    try:
        with db:
            db.execute(
                "INSERT INTO messages (id, conversation_id, role, text, emotion, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (legacy_id, conv_id, "user", "legacy", None, "2030-01-01T00:00:00Z"),
            )
    finally:
        db.close()
    monkeypatch.setattr(conversation_routes, "utc_now_iso", lambda: "2030-01-01T00:00:00.123456Z")
    contexts = []

    def fake_ai(context, message):
        contexts.append(context)
        return "answer", "neutral"

    monkeypatch.setattr(mock_ai, "generate_reply", fake_ai)
    assert _send(client, headers, conv_id).status_code == 200
    assert contexts[0][0]["text"] == "legacy"
    items = client.get(f"/api/v1/conversations/{conv_id}/messages", headers=headers).json()["items"]
    assert [item["role"] for item in items] == ["user", "user", "assistant"]
    assert items[0]["id"] == legacy_id
