"""Owner-scoped memory management and one-time conversation-entry check-ins."""

import sqlite3
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel

from app.api.dependencies import get_client_id, validate_conversation_id
from app.db.connection import get_db
from app.exceptions import ConversationNotFoundException
from app.schemas.conversation import MessageResponse
from app.services import memory_service as memory

router = APIRouter(tags=["Memory"])


class MemoryResponse(BaseModel):
    id: str
    kind: str
    content: str
    event_date: Optional[str] = None
    remind_on: Optional[str] = None
    reminded_at: Optional[str] = None
    expires_at: Optional[str] = None
    created_at: str
    updated_at: str
    active: bool = True


class MemoryListResponse(BaseModel):
    items: list[MemoryResponse]


class CheckInResponse(BaseModel):
    message: Optional[MessageResponse] = None


@router.get("/memories", response_model=MemoryListResponse)
def list_memories(client_id: str = Depends(get_client_id), db: sqlite3.Connection = Depends(get_db)):
    stamp = memory.iso(memory.clock_now())
    return MemoryListResponse(items=[MemoryResponse(**dict(row), active=row["expires_at"] is None or row["expires_at"] > stamp)
                                     for row in memory.owned_memories(db, client_id)])


@router.delete("/memories/{memory_id}", status_code=204)
def delete_memory(memory_id: str, client_id: str = Depends(get_client_id), db: sqlite3.Connection = Depends(get_db)):
    memory_id = validate_conversation_id(memory_id)
    with db:
        deleted = db.execute("DELETE FROM personal_memories WHERE id = ? AND client_id = ?", (memory_id, client_id))
        if deleted.rowcount != 1:
            raise HTTPException(404, "Không tìm thấy thông tin ghi nhớ.")
    return Response(status_code=204)


@router.post("/conversations/{conversation_id}/check-in", response_model=CheckInResponse)
def check_in(conversation_id: str, client_id: str = Depends(get_client_id), db: sqlite3.Connection = Depends(get_db)):
    conversation_id = validate_conversation_id(conversation_id)
    now = memory.clock_now()
    stamp = memory.iso(now)
    today = now.astimezone(memory.VIETNAM_TZ).date().isoformat()
    with db:
        db.execute("BEGIN IMMEDIATE")
        if db.execute("SELECT 1 FROM conversations WHERE id = ? AND client_id = ?", (conversation_id, client_id)).fetchone() is None:
            raise ConversationNotFoundException()
        row = db.execute(
            "SELECT * FROM personal_memories WHERE client_id = ? AND remind_on <= ? AND reminded_at IS NULL "
            "AND (expires_at IS NULL OR expires_at > ?) ORDER BY remind_on, created_at, id LIMIT 1",
            (client_id, today, stamp),
        ).fetchone()
        if row is None:
            return CheckInResponse()
        description = memory._CALENDAR_DATE_PATTERN.sub("", row["content"])
        description = memory.clean(description).removesuffix(" vào")
        text = f"Anna nhắc nhẹ nè: {description}. Sự kiện vào ngày {row['event_date']}. Hôm nay mình dành một chút thời gian chuẩn bị nhé! ✨"
        message = MessageResponse(id=str(uuid.uuid4()), role="assistant", text=text, emotion="happy", created_at=stamp)
        db.execute("INSERT INTO messages (id,conversation_id,role,text,emotion,created_at) VALUES (?,?,?,?,?,?)",
                   (message.id, conversation_id, message.role, message.text, message.emotion, stamp))
        db.execute("UPDATE personal_memories SET reminded_at = ?, updated_at = ? WHERE id = ? AND client_id = ? AND reminded_at IS NULL", (stamp, stamp, row["id"], client_id))
        db.execute("UPDATE conversations SET updated_at = ? WHERE id = ? AND client_id = ?", (stamp, conversation_id, client_id))
    return CheckInResponse(message=message)
