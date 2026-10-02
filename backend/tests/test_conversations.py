"""Automated tests for Conversation management and SQLite persistence."""

import uuid
import pytest
from app.db.connection import get_connection


def test_health_check_preserved(client):
    """GET /api/v1/health must return HTTP 200 with exactly {"status":"ok"}."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_create_conversation_default_title(client):
    """POST /conversations creates a conversation with default title and valid UTC ISO timestamps."""
    client_id = str(uuid.uuid4())
    response = client.post(
        "/api/v1/conversations",
        headers={"X-Client-Id": client_id},
    )
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    # Verify ID is a valid UUID
    uuid.UUID(data["id"])
    assert data["title"] == "Cuộc trò chuyện mới"
    assert data["created_at"].endswith("Z")
    assert data["updated_at"].endswith("Z")


def test_create_conversation_custom_title(client):
    """POST /conversations accepts an optional custom title."""
    client_id = str(uuid.uuid4())
    response = client.post(
        "/api/v1/conversations",
        headers={"X-Client-Id": client_id},
        json={"title": "Hội thoại thử nghiệm"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Hội thoại thử nghiệm"


def test_missing_and_malformed_client_id(client):
    """Missing or non-UUID X-Client-Id header returns HTTP 400 with structured error."""
    # Missing header
    res_missing = client.post("/api/v1/conversations")
    assert res_missing.status_code == 400
    assert res_missing.json()["error"]["code"] == "INVALID_CLIENT_ID"

    # Malformed UUID header
    res_malformed = client.post(
        "/api/v1/conversations",
        headers={"X-Client-Id": "not-a-valid-uuid"},
    )
    assert res_malformed.status_code == 400
    assert res_malformed.json()["error"]["code"] == "INVALID_CLIENT_ID"


def test_malformed_conversation_id(client):
    """Malformed conversation ID returns HTTP 400 with code INVALID_ID."""
    client_id = str(uuid.uuid4())
    headers = {"X-Client-Id": client_id}

    res_get = client.get("/api/v1/conversations/not-a-valid-uuid/messages", headers=headers)
    assert res_get.status_code == 400
    assert res_get.json()["error"]["code"] == "INVALID_ID"

    res_del = client.delete("/api/v1/conversations/invalid-id-here", headers=headers)
    assert res_del.status_code == 400
    assert res_del.json()["error"]["code"] == "INVALID_ID"


def test_list_conversations_ordered(client):
    """GET /conversations returns conversations ordered by updated_at descending."""
    client_id = str(uuid.uuid4())
    headers = {"X-Client-Id": client_id}

    # Create two conversations
    c1 = client.post("/api/v1/conversations", headers=headers, json={"title": "Chat 1"}).json()
    c2 = client.post("/api/v1/conversations", headers=headers, json={"title": "Chat 2"}).json()

    res = client.get("/api/v1/conversations", headers=headers)
    assert res.status_code == 200
    items = res.json()["items"]
    assert len(items) == 2
    # c2 was created after c1, so it should be first
    assert items[0]["id"] == c2["id"]
    assert items[1]["id"] == c1["id"]


def test_client_isolation(client):
    """Conversations created by Client A must not be visible or accessible to Client B."""
    client_a = str(uuid.uuid4())
    client_b = str(uuid.uuid4())

    conv_a = client.post(
        "/api/v1/conversations",
        headers={"X-Client-Id": client_a},
        json={"title": "Chat of A"},
    ).json()

    conv_b = client.post(
        "/api/v1/conversations",
        headers={"X-Client-Id": client_b},
        json={"title": "Chat of B"},
    ).json()

    # List conversations for A
    list_a = client.get("/api/v1/conversations", headers={"X-Client-Id": client_a}).json()["items"]
    assert len(list_a) == 1
    assert list_a[0]["id"] == conv_a["id"]

    # List conversations for B
    list_b = client.get("/api/v1/conversations", headers={"X-Client-Id": client_b}).json()["items"]
    assert len(list_b) == 1
    assert list_b[0]["id"] == conv_b["id"]

    # Client B tries to access Client A's conversation -> 404 NOT_FOUND
    res_b_access_a = client.get(
        f"/api/v1/conversations/{conv_a['id']}/messages",
        headers={"X-Client-Id": client_b},
    )
    assert res_b_access_a.status_code == 404
    assert res_b_access_a.json()["error"]["code"] == "NOT_FOUND"

    # Client B tries to delete Client A's conversation -> 404 NOT_FOUND
    res_b_del_a = client.delete(
        f"/api/v1/conversations/{conv_a['id']}",
        headers={"X-Client-Id": client_b},
    )
    assert res_b_del_a.status_code == 404
    assert res_b_del_a.json()["error"]["code"] == "NOT_FOUND"

    # Verify A's conversation still exists
    list_a_after = client.get("/api/v1/conversations", headers={"X-Client-Id": client_a}).json()["items"]
    assert len(list_a_after) == 1


def test_empty_messages_list(client):
    """GET /conversations/{id}/messages returns {"items":[]} for a new conversation."""
    client_id = str(uuid.uuid4())
    headers = {"X-Client-Id": client_id}

    conv = client.post("/api/v1/conversations", headers=headers).json()
    res = client.get(f"/api/v1/conversations/{conv['id']}/messages", headers=headers)
    assert res.status_code == 200
    assert res.json() == {"items": []}


def test_messages_ordered_oldest_first(client, temp_db_file):
    """GET /conversations/{id}/messages returns messages ordered oldest first."""
    client_id = str(uuid.uuid4())
    headers = {"X-Client-Id": client_id}
    conv = client.post("/api/v1/conversations", headers=headers).json()
    conv_id = conv["id"]

    # Insert messages directly into DB to test response formatting and ordering
    msg1_id = str(uuid.uuid4())
    msg2_id = str(uuid.uuid4())
    with get_connection(temp_db_file) as db:
        with db:
            db.execute(
                """
                INSERT INTO messages (id, conversation_id, role, text, emotion, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (msg1_id, conv_id, "user", "Xin chào", None, "2026-10-02T10:00:00Z"),
            )
            db.execute(
                """
                INSERT INTO messages (id, conversation_id, role, text, emotion, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (msg2_id, conv_id, "assistant", "Chào bạn!", "happy", "2026-10-02T10:00:02Z"),
            )

    res = client.get(f"/api/v1/conversations/{conv_id}/messages", headers=headers)
    assert res.status_code == 200
    items = res.json()["items"]
    assert len(items) == 2
    assert items[0]["id"] == msg1_id
    assert items[0]["role"] == "user"
    assert items[0]["text"] == "Xin chào"
    assert items[0]["emotion"] is None
    assert items[0]["created_at"] == "2026-10-02T10:00:00Z"

    assert items[1]["id"] == msg2_id
    assert items[1]["role"] == "assistant"
    assert items[1]["text"] == "Chào bạn!"
    assert items[1]["emotion"] == "happy"
    assert items[1]["created_at"] == "2026-10-02T10:00:02Z"


def test_delete_conversation_and_cascade(client, temp_db_file):
    """DELETE /conversations/{id} deletes conversation and cascades to messages with HTTP 204."""
    client_id = str(uuid.uuid4())
    headers = {"X-Client-Id": client_id}

    conv = client.post("/api/v1/conversations", headers=headers).json()
    conv_id = conv["id"]

    # Insert a message
    msg_id = str(uuid.uuid4())
    with get_connection(temp_db_file) as db:
        with db:
            db.execute(
                """
                INSERT INTO messages (id, conversation_id, role, text, emotion, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (msg_id, conv_id, "user", "Test message", None, "2026-10-02T10:00:00Z"),
            )

    # Delete conversation
    del_res = client.delete(f"/api/v1/conversations/{conv_id}", headers=headers)
    assert del_res.status_code == 204

    # Subsequent GET returns 404
    get_res = client.get(f"/api/v1/conversations/{conv_id}/messages", headers=headers)
    assert get_res.status_code == 404
    assert get_res.json()["error"]["code"] == "NOT_FOUND"

    # Verify messages are deleted from database (CASCADE)
    with get_connection(temp_db_file) as db:
        row = db.execute("SELECT COUNT(*) as cnt FROM messages WHERE conversation_id = ?", (conv_id,)).fetchone()
        assert row["cnt"] == 0


def test_404_behavior_nonexistent_uuid(client):
    """Accessing non-existent UUID returns HTTP 404 with code NOT_FOUND."""
    client_id = str(uuid.uuid4())
    non_existent_conv = str(uuid.uuid4())
    headers = {"X-Client-Id": client_id}

    res_get = client.get(f"/api/v1/conversations/{non_existent_conv}/messages", headers=headers)
    assert res_get.status_code == 404
    assert res_get.json()["error"]["code"] == "NOT_FOUND"

    res_del = client.delete(f"/api/v1/conversations/{non_existent_conv}", headers=headers)
    assert res_del.status_code == 404
    assert res_del.json()["error"]["code"] == "NOT_FOUND"


def test_persistence_after_reopening_database(temp_db_file):
    """Database records survive closing and reopening SQLite connection."""
    client_id = str(uuid.uuid4())
    conv_id = str(uuid.uuid4())
    now = "2026-10-02T10:00:00Z"

    # Step 1: Open connection, insert data, and close connection
    conn1 = get_connection(temp_db_file)
    with conn1:
        conn1.execute(
            """
            INSERT INTO conversations (id, client_id, title, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (conv_id, client_id, "Cuộc trò chuyện bền vững", now, now),
        )
    conn1.close()

    # Step 2: Open a fresh connection and verify data is still present
    conn2 = get_connection(temp_db_file)
    row = conn2.execute(
        "SELECT id, title, created_at, updated_at FROM conversations WHERE id = ? AND client_id = ?",
        (conv_id, client_id),
    ).fetchone()
    conn2.close()

    assert row is not None
    assert row["id"] == conv_id
    assert row["title"] == "Cuộc trò chuyện bền vững"
    assert row["created_at"] == now
    assert row["updated_at"] == now
