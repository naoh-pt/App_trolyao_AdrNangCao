"""Automated tests for Message sending, Mock AI, and Idempotency (Milestone 3)."""

import concurrent.futures
import sqlite3
import uuid
import pytest

from app.db.connection import get_connection
import app.services.mock_ai as mock_ai_module


def test_send_message_success(client):
    """POST /conversations/{id}/messages successfully returns user and assistant message pair."""
    client_id = str(uuid.uuid4())
    headers = {"X-Client-Id": client_id}

    # 1. Create a conversation
    conv = client.post("/api/v1/conversations", headers=headers).json()
    conv_id = conv["id"]

    # 2. Send message
    req_id = str(uuid.uuid4())
    res = client.post(
        f"/api/v1/conversations/{conv_id}/messages",
        headers=headers,
        json={"request_id": req_id, "message": "Xin chào bạn!"},
    )
    assert res.status_code == 200
    data = res.json()

    assert "user_message" in data
    assert "assistant_message" in data

    u_msg = data["user_message"]
    a_msg = data["assistant_message"]

    # Verify user message
    uuid.UUID(u_msg["id"])
    assert u_msg["role"] == "user"
    assert u_msg["text"] == "Xin chào bạn!"
    assert u_msg["emotion"] is None
    assert u_msg["created_at"].endswith("Z")

    # Verify assistant message
    uuid.UUID(a_msg["id"])
    assert a_msg["role"] == "assistant"
    assert len(a_msg["text"]) > 0
    assert a_msg["emotion"] in ["neutral", "happy", "sad", "surprised"]
    assert a_msg["created_at"].endswith("Z")


def test_message_ordering_and_tie_breaker(client):
    """Messages are retrieved oldest first, with user message strictly before assistant reply."""
    client_id = str(uuid.uuid4())
    headers = {"X-Client-Id": client_id}
    conv = client.post("/api/v1/conversations", headers=headers).json()
    conv_id = conv["id"]

    # Send 2 message pairs
    r1 = client.post(
        f"/api/v1/conversations/{conv_id}/messages",
        headers=headers,
        json={"request_id": str(uuid.uuid4()), "message": "Tin nhắn 1"},
    ).json()

    r2 = client.post(
        f"/api/v1/conversations/{conv_id}/messages",
        headers=headers,
        json={"request_id": str(uuid.uuid4()), "message": "Tin nhắn 2"},
    ).json()

    # Get all messages
    get_res = client.get(f"/api/v1/conversations/{conv_id}/messages", headers=headers)
    assert get_res.status_code == 200
    items = get_res.json()["items"]
    assert len(items) == 4

    assert items[0]["id"] == r1["user_message"]["id"]
    assert items[0]["role"] == "user"

    assert items[1]["id"] == r1["assistant_message"]["id"]
    assert items[1]["role"] == "assistant"

    assert items[2]["id"] == r2["user_message"]["id"]
    assert items[2]["role"] == "user"

    assert items[3]["id"] == r2["assistant_message"]["id"]
    assert items[3]["role"] == "assistant"


def test_last_10_context(client, monkeypatch):
    """Mock AI receives at most the last 10 messages from the conversation, ordered oldest to newest."""
    client_id = str(uuid.uuid4())
    headers = {"X-Client-Id": client_id}
    conv = client.post("/api/v1/conversations", headers=headers).json()
    conv_id = conv["id"]

    captured_contexts = []
    original_generate = mock_ai_module.generate_reply

    def spy_generate(context, message):
        captured_contexts.append(list(context))
        return original_generate(context, message)

    monkeypatch.setattr(mock_ai_module, "generate_reply", spy_generate)

    # Send 6 message pairs (12 messages total)
    for i in range(6):
        res = client.post(
            f"/api/v1/conversations/{conv_id}/messages",
            headers=headers,
            json={"request_id": str(uuid.uuid4()), "message": f"Câu hỏi {i+1}"},
        )
        assert res.status_code == 200

    # The 6th request had 10 messages already in the database (from the first 5 pairs)
    assert len(captured_contexts) == 6
    last_context = captured_contexts[-1]
    assert len(last_context) == 10

    # Verify context is ordered oldest to newest
    assert last_context[0]["role"] == "user"
    assert last_context[0]["text"] == "Câu hỏi 1"
    assert last_context[-1]["role"] == "assistant"


def test_repeated_request_id_idempotency(client, temp_db_file):
    """Retrying with the same request_id returns the identical message pair without inserting duplicates."""
    client_id = str(uuid.uuid4())
    headers = {"X-Client-Id": client_id}
    conv = client.post("/api/v1/conversations", headers=headers).json()
    conv_id = conv["id"]

    req_id = str(uuid.uuid4())

    # First call
    res1 = client.post(
        f"/api/v1/conversations/{conv_id}/messages",
        headers=headers,
        json={"request_id": req_id, "message": "Câu hỏi lặp lại"},
    )
    assert res1.status_code == 200
    data1 = res1.json()

    # Second call (with same text including whitespace that normalizes identically)
    res2 = client.post(
        f"/api/v1/conversations/{conv_id}/messages",
        headers=headers,
        json={"request_id": req_id, "message": "   Câu hỏi lặp lại   "},
    )
    assert res2.status_code == 200
    data2 = res2.json()

    # Verify identical data
    assert data1["user_message"]["id"] == data2["user_message"]["id"]
    assert data1["assistant_message"]["id"] == data2["assistant_message"]["id"]
    assert data1["user_message"]["created_at"] == data2["user_message"]["created_at"]
    assert data1["assistant_message"]["created_at"] == data2["assistant_message"]["created_at"]

    # Verify database has only 2 messages (1 user, 1 assistant)
    with get_connection(temp_db_file) as db:
        count = db.execute("SELECT COUNT(*) as cnt FROM messages WHERE conversation_id = ?", (conv_id,)).fetchone()["cnt"]
        assert count == 2


def test_same_request_id_different_text_conflict(client):
    """Reusing the same request_id with different text returns HTTP 409 Conflict."""
    client_id = str(uuid.uuid4())
    headers = {"X-Client-Id": client_id}
    conv = client.post("/api/v1/conversations", headers=headers).json()
    conv_id = conv["id"]

    req_id = str(uuid.uuid4())

    # First request
    res1 = client.post(
        f"/api/v1/conversations/{conv_id}/messages",
        headers=headers,
        json={"request_id": req_id, "message": "Nội dung ban đầu"},
    )
    assert res1.status_code == 200

    # Second request with same request_id but different text
    res2 = client.post(
        f"/api/v1/conversations/{conv_id}/messages",
        headers=headers,
        json={"request_id": req_id, "message": "Nội dung hoàn toàn khác"},
    )
    assert res2.status_code == 409
    err = res2.json()["error"]
    assert err["code"] == "REQUEST_ID_CONFLICT"


def test_near_simultaneous_retries(client, temp_db_file):
    """Near-simultaneous requests with same request_id commit only once and both return HTTP 200 with same IDs."""
    client_id = str(uuid.uuid4())
    headers = {"X-Client-Id": client_id}
    conv = client.post("/api/v1/conversations", headers=headers).json()
    conv_id = conv["id"]

    req_id = str(uuid.uuid4())

    def send_req():
        return client.post(
            f"/api/v1/conversations/{conv_id}/messages",
            headers=headers,
            json={"request_id": req_id, "message": "Đồng thời kiểm tra"},
        )

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        f1 = executor.submit(send_req)
        f2 = executor.submit(send_req)
        res1 = f1.result()
        res2 = f2.result()

    assert res1.status_code == 200
    assert res2.status_code == 200

    d1 = res1.json()
    d2 = res2.json()

    assert d1["user_message"]["id"] == d2["user_message"]["id"]
    assert d1["assistant_message"]["id"] == d2["assistant_message"]["id"]

    # Verify only 2 messages exist in database
    with get_connection(temp_db_file) as db:
        count = db.execute("SELECT COUNT(*) as cnt FROM messages WHERE conversation_id = ?", (conv_id,)).fetchone()["cnt"]
        assert count == 2


def test_another_clients_conversation(client):
    """Sending message to non-existent or another client's conversation returns HTTP 404 NOT_FOUND."""
    client_a = str(uuid.uuid4())
    client_b = str(uuid.uuid4())

    conv_a = client.post("/api/v1/conversations", headers={"X-Client-Id": client_a}).json()

    # Client B tries to send message to Client A's conversation
    res = client.post(
        f"/api/v1/conversations/{conv_a['id']}/messages",
        headers={"X-Client-Id": client_b},
        json={"request_id": str(uuid.uuid4()), "message": "Xin chào"},
    )
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "NOT_FOUND"

    # Non-existent conversation UUID
    res_fake = client.post(
        f"/api/v1/conversations/{uuid.uuid4()}/messages",
        headers={"X-Client-Id": client_a},
        json={"request_id": str(uuid.uuid4()), "message": "Xin chào"},
    )
    assert res_fake.status_code == 404
    assert res_fake.json()["error"]["code"] == "NOT_FOUND"


def test_invalid_inputs(client):
    """Validation rejects empty message, message > 2000 chars, missing/malformed request_id."""
    client_id = str(uuid.uuid4())
    headers = {"X-Client-Id": client_id}
    conv = client.post("/api/v1/conversations", headers=headers).json()
    conv_id = conv["id"]

    # 1. Missing request_id
    r1 = client.post(
        f"/api/v1/conversations/{conv_id}/messages",
        headers=headers,
        json={"message": "Xin chào"},
    )
    assert r1.status_code == 400
    assert r1.json()["error"]["code"] == "INVALID_REQUEST_ID"

    # 2. Malformed request_id
    r2 = client.post(
        f"/api/v1/conversations/{conv_id}/messages",
        headers=headers,
        json={"request_id": "not-a-valid-uuid", "message": "Xin chào"},
    )
    assert r2.status_code == 400
    assert r2.json()["error"]["code"] == "INVALID_REQUEST_ID"

    # 3. Empty message
    r3 = client.post(
        f"/api/v1/conversations/{conv_id}/messages",
        headers=headers,
        json={"request_id": str(uuid.uuid4()), "message": ""},
    )
    assert r3.status_code == 400
    assert r3.json()["error"]["code"] == "INVALID_MESSAGE"

    # 4. Whitespace-only message
    r4 = client.post(
        f"/api/v1/conversations/{conv_id}/messages",
        headers=headers,
        json={"request_id": str(uuid.uuid4()), "message": "   \n\t  "},
    )
    assert r4.status_code == 400
    assert r4.json()["error"]["code"] == "INVALID_MESSAGE"

    # 5. Message > 2000 chars
    r5 = client.post(
        f"/api/v1/conversations/{conv_id}/messages",
        headers=headers,
        json={"request_id": str(uuid.uuid4()), "message": "A" * 2001},
    )
    assert r5.status_code == 400
    assert r5.json()["error"]["code"] == "INVALID_MESSAGE"


def test_mock_failure_no_partial_save(client, temp_db_file):
    """Simulated AI failure or timeout returns 503/504 and saves NEITHER message to SQLite."""
    client_id = str(uuid.uuid4())
    headers = {"X-Client-Id": client_id}
    conv = client.post("/api/v1/conversations", headers=headers).json()
    conv_id = conv["id"]

    # 1. Simulate AI Failure (503)
    res_fail = client.post(
        f"/api/v1/conversations/{conv_id}/messages",
        headers=headers,
        json={"request_id": str(uuid.uuid4()), "message": "Kiểm tra lỗi __TEST_FAIL_AI__"},
    )
    assert res_fail.status_code == 503
    assert res_fail.json()["error"]["code"] == "LLM_UNAVAILABLE"

    # 2. Simulate AI Timeout (504)
    res_timeout = client.post(
        f"/api/v1/conversations/{conv_id}/messages",
        headers=headers,
        json={"request_id": str(uuid.uuid4()), "message": "Kiểm tra lỗi __TEST_TIMEOUT__"},
    )
    assert res_timeout.status_code == 504
    assert res_timeout.json()["error"]["code"] == "LLM_TIMEOUT"

    # Verify that NO messages and NO idempotency records were saved
    with get_connection(temp_db_file) as db:
        msg_count = db.execute("SELECT COUNT(*) as cnt FROM messages WHERE conversation_id = ?", (conv_id,)).fetchone()["cnt"]
        idemp_count = db.execute("SELECT COUNT(*) as cnt FROM idempotency_records WHERE conversation_id = ?", (conv_id,)).fetchone()["cnt"]
        assert msg_count == 0
        assert idemp_count == 0


def test_persistence_after_reopening_sqlite(client, temp_db_file):
    """Sent messages and idempotency records survive reopening SQLite."""
    client_id = str(uuid.uuid4())
    headers = {"X-Client-Id": client_id}
    conv = client.post("/api/v1/conversations", headers=headers).json()
    conv_id = conv["id"]

    req_id = str(uuid.uuid4())
    send_res = client.post(
        f"/api/v1/conversations/{conv_id}/messages",
        headers=headers,
        json={"request_id": req_id, "message": "Tin nhắn lưu trữ bền vững"},
    ).json()

    # Reopen connection directly from temp_db_file
    conn = get_connection(temp_db_file)
    msg_rows = conn.execute("SELECT id, text FROM messages WHERE conversation_id = ?", (conv_id,)).fetchall()
    idemp_row = conn.execute("SELECT request_id, normalized_message FROM idempotency_records WHERE request_id = ?", (req_id,)).fetchone()
    conn.close()

    assert len(msg_rows) == 2
    assert idemp_row is not None
    assert idemp_row["normalized_message"] == "Tin nhắn lưu trữ bền vững"


def test_deletion_cascade_messages_and_idempotency(client, temp_db_file):
    """Deleting conversation cascades and removes messages and idempotency records."""
    client_id = str(uuid.uuid4())
    headers = {"X-Client-Id": client_id}
    conv = client.post("/api/v1/conversations", headers=headers).json()
    conv_id = conv["id"]

    req_id = str(uuid.uuid4())
    client.post(
        f"/api/v1/conversations/{conv_id}/messages",
        headers=headers,
        json={"request_id": req_id, "message": "Sắp bị xóa"},
    )

    # Delete conversation
    del_res = client.delete(f"/api/v1/conversations/{conv_id}", headers=headers)
    assert del_res.status_code == 204

    # Verify cascaded deletion
    with get_connection(temp_db_file) as db:
        conv_cnt = db.execute("SELECT COUNT(*) as cnt FROM conversations WHERE id = ?", (conv_id,)).fetchone()["cnt"]
        msg_cnt = db.execute("SELECT COUNT(*) as cnt FROM messages WHERE conversation_id = ?", (conv_id,)).fetchone()["cnt"]
        idemp_cnt = db.execute("SELECT COUNT(*) as cnt FROM idempotency_records WHERE conversation_id = ?", (conv_id,)).fetchone()["cnt"]
        assert conv_cnt == 0
        assert msg_cnt == 0
        assert idemp_cnt == 0
