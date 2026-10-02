"""API endpoints for conversations and messages."""

import sqlite3
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Response, status

from app.api.dependencies import get_client_id, validate_conversation_id
from app.db.connection import get_db
from app.exceptions import (
    ConversationNotFoundException,
    InvalidMessageException,
    InvalidRequestIdException,
    RequestIdConflictException,
)
from app.schemas.conversation import (
    ConversationCreate,
    ConversationListResponse,
    ConversationResponse,
    MessageListResponse,
    MessageResponse,
    SendMessageRequest,
    SendMessageResponse,
)
import app.services.mock_ai as mock_ai
from app.utils.time import utc_now_iso

router = APIRouter(tags=["Conversations"])


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
        ORDER BY updated_at DESC, rowid DESC
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
        ORDER BY created_at ASC, rowid ASC
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


@router.post(
    "/conversations/{id}/messages",
    response_model=SendMessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Gửi tin nhắn và nhận câu trả lời từ AI",
)
def send_message(
    id: str,
    payload: Optional[SendMessageRequest] = None,
    client_id: str = Depends(get_client_id),
    db: sqlite3.Connection = Depends(get_db),
) -> SendMessageResponse:
    """Gửi tin nhắn vào cuộc trò chuyện và nhận phản hồi từ Mock AI.

    Đảm bảo tính lũy thỏa (idempotency), cập nhật updated_at của cuộc trò chuyện,
    và lưu trữ nguyên tử trong một transaction SQLite.
    """
    conv_id = validate_conversation_id(id)

    # 1. Kiểm tra tính hợp lệ của request_id
    if payload is None or not payload.request_id or not payload.request_id.strip():
        raise InvalidRequestIdException("request_id là bắt buộc")
    try:
        req_uuid = uuid.UUID(payload.request_id.strip())
        req_id = str(req_uuid)
    except (ValueError, TypeError, AttributeError):
        raise InvalidRequestIdException("request_id phải là định dạng UUID hợp lệ")

    # 2. Kiểm tra tính hợp lệ của nội dung tin nhắn
    if payload.message is None or not isinstance(payload.message, str):
        raise InvalidMessageException("Nội dung tin nhắn không hợp lệ")

    normalized_msg = payload.message.strip()
    if len(normalized_msg) == 0:
        raise InvalidMessageException("Nội dung tin nhắn không được để trống")
    if len(normalized_msg) > 2000:
        raise InvalidMessageException("Nội dung tin nhắn không được vượt quá 2000 ký tự")

    # 3. Kiểm tra cuộc trò chuyện có tồn tại và thuộc về client hiện tại
    conv_row = db.execute(
        "SELECT id FROM conversations WHERE id = ? AND client_id = ?",
        (conv_id, client_id),
    ).fetchone()
    if not conv_row:
        raise ConversationNotFoundException("Cuộc trò chuyện không tồn tại")

    # 4. Kiểm tra Idempotency trước khi gọi AI (Fast path)
    idemp_row = db.execute(
        """
        SELECT client_id, conversation_id, normalized_message, user_message_id, assistant_message_id
        FROM idempotency_records
        WHERE request_id = ?
        """,
        (req_id,),
    ).fetchone()

    if idemp_row:
        # Kiểm tra phạm vi client và cuộc trò chuyện
        if idemp_row["client_id"] != client_id or idemp_row["conversation_id"] != conv_id:
            raise RequestIdConflictException("Request ID đã được sử dụng cho một hội thoại hoặc client khác")

        # Kiểm tra nội dung tin nhắn có trùng khớp hay không
        if idemp_row["normalized_message"] != normalized_msg:
            raise RequestIdConflictException("Request ID đã được sử dụng với nội dung tin nhắn khác")

        # Đọc cặp tin nhắn đã lưu trước đó và trả về nguyên trạng
        u_row = db.execute(
            "SELECT id, role, text, emotion, created_at FROM messages WHERE id = ?",
            (idemp_row["user_message_id"],),
        ).fetchone()
        a_row = db.execute(
            "SELECT id, role, text, emotion, created_at FROM messages WHERE id = ?",
            (idemp_row["assistant_message_id"],),
        ).fetchone()

        if u_row and a_row:
            return SendMessageResponse(
                user_message=MessageResponse(
                    id=u_row["id"],
                    role=u_row["role"],
                    text=u_row["text"],
                    emotion=u_row["emotion"],
                    created_at=u_row["created_at"],
                ),
                assistant_message=MessageResponse(
                    id=a_row["id"],
                    role=a_row["role"],
                    text=a_row["text"],
                    emotion=a_row["emotion"],
                    created_at=a_row["created_at"],
                ),
            )

    # 5. Lấy tối đa 10 tin nhắn gần nhất làm ngữ cảnh (sắp xếp cũ -> mới)
    ctx_cursor = db.execute(
        """
        SELECT role, text, emotion
        FROM (
            SELECT role, text, emotion, created_at, rowid
            FROM messages
            WHERE conversation_id = ?
            ORDER BY created_at DESC, rowid DESC
            LIMIT 10
        )
        ORDER BY created_at ASC, rowid ASC
        """,
        (conv_id,),
    )
    context = [
        {"role": r["role"], "text": r["text"], "emotion": r["emotion"]}
        for r in ctx_cursor.fetchall()
    ]

    # 6. Gọi Mock AI (Không giữ write lock của SQLite trong lúc chờ phản hồi AI)
    reply_text, reply_emotion = mock_ai.generate_reply(context, normalized_msg)

    user_msg_id = str(uuid.uuid4())
    asst_msg_id = str(uuid.uuid4())
    now_ts = utc_now_iso()

    # 7. Lưu trữ nguyên tử trong một transaction SQLite
    try:
        with db:
            # Lưu tin nhắn người dùng
            db.execute(
                """
                INSERT INTO messages (id, conversation_id, role, text, emotion, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (user_msg_id, conv_id, "user", normalized_msg, None, now_ts),
            )
            # Lưu tin nhắn trợ lý ảo
            db.execute(
                """
                INSERT INTO messages (id, conversation_id, role, text, emotion, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (asst_msg_id, conv_id, "assistant", reply_text, reply_emotion, now_ts),
            )
            # Lưu bản ghi kiểm tra Idempotency (với khóa chính request_id)
            db.execute(
                """
                INSERT INTO idempotency_records (
                    request_id, client_id, conversation_id, normalized_message,
                    user_message_id, assistant_message_id, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (req_id, client_id, conv_id, normalized_msg, user_msg_id, asst_msg_id, now_ts),
            )
            # Cập nhật thời gian updated_at của cuộc trò chuyện
            db.execute(
                "UPDATE conversations SET updated_at = ? WHERE id = ?",
                (now_ts, conv_id),
            )

        return SendMessageResponse(
            user_message=MessageResponse(
                id=user_msg_id,
                role="user",
                text=normalized_msg,
                emotion=None,
                created_at=now_ts,
            ),
            assistant_message=MessageResponse(
                id=asst_msg_id,
                role="assistant",
                text=reply_text,
                emotion=reply_emotion,
                created_at=now_ts,
            ),
        )

    except sqlite3.IntegrityError:
        # Trường hợp hai request đồng thời với cùng request_id:
        # Transaction của request này bị rollback, đọc bản ghi đã commit của request kia
        winner_row = db.execute(
            """
            SELECT client_id, conversation_id, normalized_message, user_message_id, assistant_message_id
            FROM idempotency_records
            WHERE request_id = ?
            """,
            (req_id,),
        ).fetchone()

        if winner_row:
            if (
                winner_row["client_id"] == client_id
                and winner_row["conversation_id"] == conv_id
                and winner_row["normalized_message"] == normalized_msg
            ):
                u_row = db.execute(
                    "SELECT id, role, text, emotion, created_at FROM messages WHERE id = ?",
                    (winner_row["user_message_id"],),
                ).fetchone()
                a_row = db.execute(
                    "SELECT id, role, text, emotion, created_at FROM messages WHERE id = ?",
                    (winner_row["assistant_message_id"],),
                ).fetchone()
                if u_row and a_row:
                    return SendMessageResponse(
                        user_message=MessageResponse(
                            id=u_row["id"],
                            role=u_row["role"],
                            text=u_row["text"],
                            emotion=u_row["emotion"],
                            created_at=u_row["created_at"],
                        ),
                        assistant_message=MessageResponse(
                            id=a_row["id"],
                            role=a_row["role"],
                            text=a_row["text"],
                            emotion=a_row["emotion"],
                            created_at=a_row["created_at"],
                        ),
                    )
            else:
                raise RequestIdConflictException("Request ID đã được sử dụng với nội dung tin nhắn khác")

        raise
