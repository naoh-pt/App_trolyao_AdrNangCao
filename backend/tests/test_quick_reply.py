"""Unit and route tests for deterministic local quick replies."""

import uuid
import pytest

import ai_service
import app.api.v1.conversations as routes
from app.db.connection import get_connection
from app.services.quick_reply_service import (
    QUICK_REPLIES,
    get_quick_reply,
    normalize_for_quick_reply,
)


# ============================================================================
# 8.2 Quick-reply unit tests
# ============================================================================

@pytest.mark.parametrize(
    "greeting_input",
    [
        "chào",
        "xin chào",
        "chào bạn",
        "chào Anna",
        "xin chào Anna",
        "xin chào bạn",
        "hello",
        "hi",
        "hello Anna",
        "hi Anna",
        "hi bạn",
        "chào nhé",
        "chào bạn nhé",
    ],
)
def test_greeting_intent_matches(greeting_input):
    result = get_quick_reply(greeting_input)
    assert result is not None
    reply_text, emotion = result
    assert emotion == "happy"
    assert reply_text == QUICK_REPLIES["greeting"][0]


@pytest.mark.parametrize(
    "thanks_input",
    [
        "cảm ơn",
        "cám ơn",
        "cảm ơn Anna",
        "cám ơn Anna",
        "cảm ơn bạn",
        "cảm ơn bạn nhé",
        "cảm ơn nhiều",
        "cảm ơn bạn nhiều",
        "thank you",
        "thanks",
        "thank you Anna",
        "thanks Anna",
    ],
)
def test_thanks_intent_matches(thanks_input):
    result = get_quick_reply(thanks_input)
    assert result is not None
    reply_text, emotion = result
    assert emotion == "happy"
    assert reply_text == QUICK_REPLIES["thanks"][0]


@pytest.mark.parametrize(
    "goodbye_input",
    [
        "tạm biệt",
        "tạm biệt bạn",
        "tạm biệt Anna",
        "bye",
        "bye bye",
        "bye Anna",
        "goodbye",
        "goodbye Anna",
        "hẹn gặp lại",
    ],
)
def test_goodbye_intent_matches(goodbye_input):
    result = get_quick_reply(goodbye_input)
    assert result is not None
    reply_text, emotion = result
    assert emotion == "happy"
    assert reply_text == QUICK_REPLIES["goodbye"][0]


@pytest.mark.parametrize(
    "identity_input",
    [
        "bạn là ai",
        "bạn là ai thế",
        "bạn là ai vậy",
        "cậu là ai",
        "bạn tên gì",
        "bạn tên là gì",
        "tên của bạn là gì",
        "tên bạn là gì",
        "Anna là ai",
        "ai đây",
    ],
)
def test_identity_intent_matches(identity_input):
    result = get_quick_reply(identity_input)
    assert result is not None
    reply_text, emotion = result
    assert emotion == "happy"
    assert reply_text == QUICK_REPLIES["identity"][0]


@pytest.mark.parametrize(
    "capabilities_input",
    [
        "bạn làm được gì",
        "bạn có thể làm gì",
        "bạn có thể giúp gì",
        "bạn có thể giúp gì cho mình",
        "bạn giúp được gì",
        "Anna giúp được gì",
        "bạn biết làm gì",
        "cậu làm được gì",
    ],
)
def test_capabilities_intent_matches(capabilities_input):
    result = get_quick_reply(capabilities_input)
    assert result is not None
    reply_text, emotion = result
    assert emotion in {"happy", "neutral"}
    assert reply_text == QUICK_REPLIES["capabilities"][0]


@pytest.mark.parametrize(
    "cased_input,expected_intent",
    [
        ("XIN CHÀO", "greeting"),
        ("CHÀO ANNA", "greeting"),
        ("HELLO", "greeting"),
        ("CẢM ƠN", "thanks"),
        ("THANK YOU", "thanks"),
        ("TẠM BIỆT", "goodbye"),
        ("BẠN LÀ AI", "identity"),
        ("BẠN LÀM ĐƯỢC GÌ", "capabilities"),
    ],
)
def test_case_normalization(cased_input, expected_intent):
    result = get_quick_reply(cased_input)
    assert result is not None
    assert result[0] == QUICK_REPLIES[expected_intent][0]


@pytest.mark.parametrize(
    "whitespace_input,expected_intent",
    [
        ("   chào   anna   ", "greeting"),
        ("\n\t  xin   chào   \n", "greeting"),
        ("  cảm ơn    bạn  ", "thanks"),
        ("   tạm   biệt   ", "goodbye"),
        ("  bạn   là   ai  ", "identity"),
    ],
)
def test_surrounding_and_repeated_whitespace(whitespace_input, expected_intent):
    result = get_quick_reply(whitespace_input)
    assert result is not None
    assert result[0] == QUICK_REPLIES[expected_intent][0]


@pytest.mark.parametrize(
    "punct_input,expected_intent",
    [
        ("chào bạn!", "greeting"),
        ("chào Anna???", "greeting"),
        ("hello...", "greeting"),
        ("Hi ~", "greeting"),
        ("cảm ơn bạn nhé!", "thanks"),
        ("bạn là ai???", "identity"),
        ("bạn làm được gì?!", "capabilities"),
        ("tạm biệt.", "goodbye"),
    ],
)
def test_ending_punctuation_stripping(punct_input, expected_intent):
    result = get_quick_reply(punct_input)
    assert result is not None
    assert result[0] == QUICK_REPLIES[expected_intent][0]


@pytest.mark.parametrize(
    "longer_greeting_sentence",
    [
        "chào Anna cho mình hỏi phòng đào tạo ở đâu",
        "chào bạn, hôm nay có lịch thi không",
        "xin chào, mình muốn tìm hiểu về học phí",
        "lời chào mừng năm học mới của học viện",
        "chào cờ sáng thứ hai lúc mấy giờ",
    ],
)
def test_longer_sentence_containing_greeting_does_not_falsely_match(longer_greeting_sentence):
    """Conservative matching must never match sentences that simply contain greeting words."""
    assert get_quick_reply(longer_greeting_sentence) is None


@pytest.mark.parametrize(
    "school_question",
    [
        "Quy chế đào tạo của Học viện Kỹ thuật Mật mã như thế nào?",
        "Học phí kỳ 1 của KMA là bao nhiêu?",
        "Điều kiện xét học bổng khuyến khích học tập tại trường?",
        "Học viện có những chuyên ngành nào?",
        "Lịch thi học kỳ 2 năm học này?",
    ],
)
def test_school_questions_do_not_match(school_question):
    """School and regulation questions must never be hijacked by quick replies."""
    assert get_quick_reply(school_question) is None


@pytest.mark.parametrize(
    "academic_question",
    [
        "Môn giải tích 1 học những nội dung gì?",
        "Thuật toán mã hóa AES hoạt động như thế nào?",
        "Toán rời rạc gồm các phần nào?",
        "Giải thích khái niệm hàm băm SHA-256",
        "Lập trình hướng đối tượng trong Java",
    ],
)
def test_academic_questions_do_not_match(academic_question):
    """Academic questions must never match quick replies."""
    assert get_quick_reply(academic_question) is None


@pytest.mark.parametrize(
    "unknown_input",
    [
        "Thời tiết hôm nay thế nào?",
        "1 + 1 bằng mấy?",
        "Bạn thích ăn gì?",
        "xyz abc 123",
        "...",
    ],
)
def test_unknown_inputs_return_none(unknown_input):
    """Unmatched inputs return None to proceed to RAG and LLM."""
    assert get_quick_reply(unknown_input) is None


# ============================================================================
# 8.3 Quick-reply route tests
# ============================================================================

def _create_chat(client):
    headers = {"X-Client-Id": str(uuid.uuid4())}
    res = client.post("/api/v1/conversations", headers=headers)
    assert res.status_code == 200
    return headers, res.json()["id"]


def test_quick_reply_route_success(client, temp_db_file, monkeypatch):
    """Quick reply returns HTTP 200, valid schema, persists messages, and skips RAG & Gemini."""
    rag_called = []
    ai_called = []

    monkeypatch.setattr(routes, "retrieve", lambda q: rag_called.append(q) or [])
    monkeypatch.setattr(ai_service, "generate_reply", lambda *args: ai_called.append(args) or ("AI reply", "neutral"))

    headers, conv_id = _create_chat(client)
    req_id = str(uuid.uuid4())
    res = client.post(
        f"/api/v1/conversations/{conv_id}/messages",
        headers=headers,
        json={"request_id": req_id, "message": "Chào Anna!"},
    )

    assert res.status_code == 200
    data = res.json()

    # Schema checks
    assert set(data.keys()) == {"user_message", "assistant_message", "sources"}
    assert data["sources"] == []
    assert len(rag_called) == 0
    assert len(ai_called) == 0

    u_msg = data["user_message"]
    a_msg = data["assistant_message"]

    assert u_msg["role"] == "user"
    assert u_msg["text"] == "Chào Anna!"
    assert u_msg["emotion"] is None

    assert a_msg["role"] == "assistant"
    assert a_msg["text"] == QUICK_REPLIES["greeting"][0]
    assert a_msg["emotion"] == "happy"

    # SQLite persistence check
    with get_connection(temp_db_file) as db:
        msg_count = db.execute("SELECT COUNT(*) FROM messages WHERE conversation_id = ?", (conv_id,)).fetchone()[0]
        assert msg_count == 2
        idemp_row = db.execute("SELECT * FROM idempotency_records WHERE request_id = ?", (req_id,)).fetchone()
        assert idemp_row is not None
        assert idemp_row["normalized_message"] == "Chào Anna!"


def test_quick_reply_replay_idempotency(client, temp_db_file, monkeypatch):
    """Replaying same request_id returns committed response without duplicate inserts."""
    headers, conv_id = _create_chat(client)
    req_id = str(uuid.uuid4())

    res1 = client.post(
        f"/api/v1/conversations/{conv_id}/messages",
        headers=headers,
        json={"request_id": req_id, "message": "Cảm ơn Anna"},
    )
    assert res1.status_code == 200
    data1 = res1.json()

    # Replay with same request_id
    res2 = client.post(
        f"/api/v1/conversations/{conv_id}/messages",
        headers=headers,
        json={"request_id": req_id, "message": "   Cảm ơn Anna   "},
    )
    assert res2.status_code == 200
    data2 = res2.json()

    assert data1 == data2
    with get_connection(temp_db_file) as db:
        msg_count = db.execute("SELECT COUNT(*) FROM messages WHERE conversation_id = ?", (conv_id,)).fetchone()[0]
        assert msg_count == 2
