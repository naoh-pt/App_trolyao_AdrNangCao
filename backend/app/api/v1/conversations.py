"""API endpoints for conversations and messages."""

import sqlite3
import uuid
import logging
from typing import Optional
from fastapi import APIRouter, Depends, Response, status

from app.api.dependencies import get_client_id, validate_conversation_id
from app.db.connection import get_db
from app.exceptions import (
    ConversationNotFoundException,
    InvalidMessageException,
    InvalidRequestIdException,
    InvalidAIReplyException,
    RequestIdConflictException,
)
from app.schemas.conversation import (
    AssistantActionResponse,
    ConversationCreate,
    ConversationListResponse,
    ConversationResponse,
    MessageListResponse,
    MessageResponse,
    SendMessageRequest,
    SendMessageResponse,
)
from app.schemas.knowledge import SourceResponse
import ai_service
from app.config import RAG_ENABLED, USE_REAL_AI
import app.services.mock_ai as mock_ai
from app.services.rag_service import prompt_context, retrieve
from app.exceptions import RAGUnavailableException, is_quota_exhausted_exception
from app.services.request_guard import own_request
from app.services.quick_reply_service import get_quick_reply
from app.services.assistant_action_service import recognize_action
from app.services.personality import ANNA_QUOTA_FALLBACK_TEXT, ANNA_QUOTA_FALLBACK_EMOTION
from app.utils.time import utc_now_iso

router = APIRouter(tags=["Conversations"])
VALID_EMOTIONS = {"neutral", "happy", "sad", "surprised"}


@router.post(
    "/conversations",
    response_model=ConversationResponse,
    status_code=status.HTTP_200_OK,
    summary="Tạo cuộc trò chuyện mới",
)
def create_conversation(
    payload: Optional[ConversationCreate] = None,
    client_id: str = Depends(get_client_id),
    db: sqlite3.Connection = Depends(get_db),
) -> ConversationResponse:
    """Tạo một cuộc trò chuyện mới với ID UUID do server sinh và tiêu đề mặc định."""
    conv_id = str(uuid.uuid4())
    now = utc_now_iso()

    title = "Cuộc trò chuyện mới"
    if payload and payload.title and payload.title.strip():
        title = payload.title.strip()

    with db:
        db.execute(
            """
            INSERT INTO conversations (id, client_id, title, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (conv_id, client_id, title, now, now),
        )

    return ConversationResponse(
        id=conv_id,
        title=title,
        created_at=now,
        updated_at=now,
    )


@router.get(
    "/conversations",
    response_model=ConversationListResponse,
    summary="Danh sách cuộc trò chuyện của client",
)
def list_conversations(
    client_id: str = Depends(get_client_id),
    db: sqlite3.Connection = Depends(get_db),
) -> ConversationListResponse:
    """Trả về danh sách cuộc trò chuyện thuộc client hiện tại, sắp xếp theo updated_at giảm dần."""
    cursor = db.execute(
        """
        SELECT id, title, created_at, updated_at
        FROM conversations
        WHERE client_id = ?
        ORDER BY CASE
            WHEN length(updated_at) = 20 THEN substr(updated_at, 1, 19) || '.000000Z'
            ELSE updated_at
        END DESC, rowid DESC
        """,
        (client_id,),
    )
    rows = cursor.fetchall()
    items = [
        ConversationResponse(
            id=row["id"],
            title=row["title"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
        for row in rows
    ]
    return ConversationListResponse(items=items)


@router.get(
    "/conversations/{id}/messages",
    response_model=MessageListResponse,
    summary="Xem danh sách tin nhắn trong cuộc trò chuyện",
)
def get_conversation_messages(
    id: str,
    client_id: str = Depends(get_client_id),
    db: sqlite3.Connection = Depends(get_db),
) -> MessageListResponse:
    """Lấy danh sách tin nhắn của cuộc trò chuyện, sắp xếp theo thời gian cũ nhất trước.

    Sử dụng tie-breaker rowid ASC để đảm bảo tin nhắn user luôn đứng trước assistant nếu cùng timestamp.
    Trả về 404 nếu cuộc trò chuyện không tồn tại hoặc thuộc client khác.
    """
    conv_id = validate_conversation_id(id)

    # Kiểm tra cuộc trò chuyện tồn tại và thuộc về client này
    row = db.execute(
        "SELECT id FROM conversations WHERE id = ? AND client_id = ?",
        (conv_id, client_id),
    ).fetchone()

    if not row:
        raise ConversationNotFoundException("Cuộc trò chuyện không tồn tại")

    cursor = db.execute(
        """
        SELECT id, role, text, emotion, created_at
        FROM messages
        WHERE conversation_id = ?
        ORDER BY CASE
            WHEN length(created_at) = 20 THEN substr(created_at, 1, 19) || '.000000Z'
            ELSE created_at
        END ASC, rowid ASC
        """,
        (conv_id,),
    )
    rows = cursor.fetchall()
    items = [
        MessageResponse(
            id=r["id"],
            role=r["role"],
            text=r["text"],
            emotion=r["emotion"],
            created_at=r["created_at"],
        )
        for r in rows
    ]
    return MessageListResponse(items=items)


@router.delete(
    "/conversations/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Xóa cuộc trò chuyện và tin nhắn liên quan",
)
def delete_conversation(
    id: str,
    client_id: str = Depends(get_client_id),
    db: sqlite3.Connection = Depends(get_db),
) -> Response:
    """Xóa cuộc trò chuyện, tin nhắn và bản ghi idempotency liên quan theo quy tắc cascade.

    Trả về 404 nếu cuộc trò chuyện không tồn tại hoặc thuộc client khác.
    """
    conv_id = validate_conversation_id(id)

    row = db.execute(
        "SELECT id FROM conversations WHERE id = ? AND client_id = ?",
        (conv_id, client_id),
    ).fetchone()

    if not row:
        raise ConversationNotFoundException("Cuộc trò chuyện không tồn tại")

    with db:
        db.execute(
            "DELETE FROM conversations WHERE id = ? AND client_id = ?",
            (conv_id, client_id),
        )

    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _sources_for_message(db: sqlite3.Connection, assistant_message_id: str) -> list[SourceResponse]:
    rows = db.execute(
        """SELECT document_id, filename, page_number, score FROM message_sources
           WHERE assistant_message_id = ? ORDER BY score DESC""",
        (assistant_message_id,),
    ).fetchall()
    return [SourceResponse(**dict(row)) for row in rows]


def _saved_response(db: sqlite3.Connection, req_id: str, client_id: str, conv_id: str, message: str):
    """Return a committed pair, or None when this request ID is unused."""
    row = db.execute(
        """SELECT client_id, conversation_id, normalized_message, user_message_id, assistant_message_id
           FROM idempotency_records WHERE request_id = ?""",
        (req_id,),
    ).fetchone()
    if row is None:
        return None
    if row["client_id"] != client_id or row["conversation_id"] != conv_id:
        raise RequestIdConflictException("Request ID belongs to another conversation or client")
    if row["normalized_message"] != message:
        raise RequestIdConflictException("Request ID was used with different message text")
    user = db.execute(
        "SELECT id, role, text, emotion, created_at FROM messages WHERE id = ?",
        (row["user_message_id"],),
    ).fetchone()
    assistant = db.execute(
        "SELECT id, role, text, emotion, created_at FROM messages WHERE id = ?",
        (row["assistant_message_id"],),
    ).fetchone()
    if user is None or assistant is None:
        raise RuntimeError("Idempotency record refers to missing messages")

    action_dto = None
    action_match = recognize_action(message)
    if action_match is not None and action_match.action is not None:
        action_dto = AssistantActionResponse(**action_match.action.to_dict())

    asst_dict = dict(assistant)
    asst_dict["action"] = action_dto

    return SendMessageResponse(
        user_message=MessageResponse(**dict(user)),
        assistant_message=MessageResponse(**asst_dict),
        sources=_sources_for_message(db, assistant["id"]),
        action=action_dto,
    )


@router.post(
    "/conversations/{id}/messages",
    response_model=SendMessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Send a message and receive an AI reply",
)
def send_message(
    id: str,
    payload: Optional[SendMessageRequest] = None,
    client_id: str = Depends(get_client_id),
    db: sqlite3.Connection = Depends(get_db),
) -> SendMessageResponse:
    """Send a message using process-local request ownership and an atomic SQLite write."""
    conv_id = validate_conversation_id(id)
    if payload is None or not payload.request_id or not payload.request_id.strip():
        raise InvalidRequestIdException("request_id is required")
    try:
        req_id = str(uuid.UUID(payload.request_id.strip()))
    except (ValueError, TypeError, AttributeError):
        raise InvalidRequestIdException("request_id must be a valid UUID")

    if payload.message is None or not isinstance(payload.message, str):
        raise InvalidMessageException("Message text is invalid")
    normalized_msg = payload.message.strip()
    if not normalized_msg:
        raise InvalidMessageException("Message text cannot be empty")
    if len(normalized_msg) > 2000:
        raise InvalidMessageException("Message text cannot exceed 2000 characters")

    # A retry waits for the owner, then checks the committed result before calling AI.
    with own_request(req_id):
        conv_row = db.execute(
            "SELECT id FROM conversations WHERE id = ? AND client_id = ?",
            (conv_id, client_id),
        ).fetchone()
        if conv_row is None:
            raise ConversationNotFoundException()

        saved = _saved_response(db, req_id, client_id, conv_id, normalized_msg)
        if saved is not None:
            return saved

        # Check deterministic assistant actions first (timer, calendar, map)
        action_match = recognize_action(normalized_msg)
        proposed_action = None
        if action_match is not None:
            reply_text, reply_emotion = action_match.reply, action_match.emotion
            if action_match.action is not None:
                proposed_action = AssistantActionResponse(**action_match.action.to_dict())
            retrieved = []
        else:
            # Check deterministic quick replies second (skips context, RAG, and AI)
            quick_reply = get_quick_reply(normalized_msg)
            if quick_reply is not None:
                reply_text, reply_emotion = quick_reply
                retrieved = []
            else:
                rows = db.execute(
                    """SELECT role, text, emotion FROM (
                           SELECT role, text, emotion, created_at, rowid
                           FROM messages WHERE conversation_id = ?
                           ORDER BY CASE
                               WHEN length(created_at) = 20 THEN substr(created_at, 1, 19) || '.000000Z'
                               ELSE created_at
                           END DESC, rowid DESC LIMIT 10
                       ) ORDER BY CASE
                           WHEN length(created_at) = 20 THEN substr(created_at, 1, 19) || '.000000Z'
                           ELSE created_at
                       END ASC, rowid ASC""",
                    (conv_id,),
                ).fetchall()
                context = [
                    {"role": row["role"], "text": row["text"], "emotion": row["emotion"]}
                    for row in rows
                ]
                retrieved = []
                try:
                    if USE_REAL_AI:
                        if RAG_ENABLED:
                            try:
                                retrieved = retrieve(normalized_msg)
                            except RAGUnavailableException as exc:
                                logging.warning("RAG unavailable (%s); continuing with normal Gemini reply", exc.category)
                        result = ai_service.generate_reply(context, normalized_msg, prompt_context(retrieved))
                    else:
                        result = mock_ai.generate_reply(context, normalized_msg)
                except Exception as exc:
                    if is_quota_exhausted_exception(exc):
                        logging.warning("AI provider quota exhausted; using friendly Anna fallback")
                        result = (ANNA_QUOTA_FALLBACK_TEXT, ANNA_QUOTA_FALLBACK_EMOTION)
                        retrieved = []
                    else:
                        raise

                if not isinstance(result, (tuple, list)) or len(result) != 2:
                    raise InvalidAIReplyException()
                reply_text, reply_emotion = result
        if not isinstance(reply_text, str) or not reply_text.strip():
            raise InvalidAIReplyException()
        reply_text = reply_text.strip()
        if not isinstance(reply_emotion, str) or reply_emotion not in VALID_EMOTIONS:
            reply_emotion = "neutral"

        user_msg_id = str(uuid.uuid4())
        asst_msg_id = str(uuid.uuid4())
        now_ts = utc_now_iso()
        try:
            with db:
                # BEGIN IMMEDIATE prevents deletion between the ownership recheck and inserts.
                db.execute("BEGIN IMMEDIATE")
                if db.execute(
                    "SELECT 1 FROM conversations WHERE id = ? AND client_id = ?",
                    (conv_id, client_id),
                ).fetchone() is None:
                    raise ConversationNotFoundException()
                db.execute(
                    """INSERT INTO messages (id, conversation_id, role, text, emotion, created_at)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (user_msg_id, conv_id, "user", normalized_msg, None, now_ts),
                )
                db.execute(
                    """INSERT INTO messages (id, conversation_id, role, text, emotion, created_at)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (asst_msg_id, conv_id, "assistant", reply_text, reply_emotion, now_ts),
                )
                db.execute(
                    """INSERT INTO idempotency_records
                       (request_id, client_id, conversation_id, normalized_message,
                        user_message_id, assistant_message_id, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (req_id, client_id, conv_id, normalized_msg, user_msg_id, asst_msg_id, now_ts),
                )
                for source in retrieved:
                    db.execute(
                        """INSERT INTO message_sources
                           (assistant_message_id, document_id, chunk_id, filename, page_number, score)
                           VALUES (?, ?, ?, ?, ?, ?)""",
                        (
                            asst_msg_id,
                            source.document_id,
                            source.chunk_id,
                            source.filename,
                            source.page_number,
                            source.score,
                        ),
                    )
                db.execute(
                    "UPDATE conversations SET updated_at = ? WHERE id = ? AND client_id = ?",
                    (now_ts, conv_id, client_id),
                )
        except sqlite3.IntegrityError as exc:
            # The constraint is the final guard if another process handles the same key.
            if getattr(exc, "sqlite_errorname", "") == "SQLITE_CONSTRAINT_FOREIGNKEY":
                if db.execute(
                    "SELECT 1 FROM conversations WHERE id = ? AND client_id = ?",
                    (conv_id, client_id),
                ).fetchone() is None:
                    raise ConversationNotFoundException() from exc
                raise
            saved = _saved_response(db, req_id, client_id, conv_id, normalized_msg)
            if saved is not None:
                return saved
            raise

        return SendMessageResponse(
            user_message=MessageResponse(
                id=user_msg_id, role="user", text=normalized_msg, emotion=None, created_at=now_ts
            ),
            assistant_message=MessageResponse(
                id=asst_msg_id, role="assistant", text=reply_text,
                emotion=reply_emotion, action=proposed_action, created_at=now_ts
            ),
            sources=[
                SourceResponse(
                    document_id=item.document_id,
                    filename=item.filename,
                    page_number=item.page_number,
                    score=item.score,
                )
                for item in retrieved
            ],
            action=proposed_action,
        )
