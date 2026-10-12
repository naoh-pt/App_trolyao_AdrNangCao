"""Pydantic schemas for Conversation and Message resources."""

from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field, model_serializer

from app.schemas.knowledge import SourceResponse


class ConversationCreate(BaseModel):
    """Optional payload when creating a conversation."""
    title: Optional[str] = Field(default=None, description="Tùy chọn tiêu đề cuộc trò chuyện")


class ConversationResponse(BaseModel):
    """Conversation representation in API responses."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    created_at: str
    updated_at: str


class ConversationListResponse(BaseModel):
    """List response wrapped in items array."""
    items: List[ConversationResponse]


class AssistantActionResponse(BaseModel):
    """Structured allowlisted assistant action proposed to the client."""
    type: str
    label: str
    message: Optional[str] = None
    duration_seconds: Optional[int] = None
    title: Optional[str] = None
    start_at: Optional[str] = None
    end_at: Optional[str] = None
    query: Optional[str] = None


class MessageResponse(BaseModel):
    """Message representation in API responses."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    role: str
    text: str
    emotion: Optional[str] = None
    action: Optional[AssistantActionResponse] = None
    created_at: str

    @model_serializer(mode="wrap")
    def _serialize(self, handler):
        d = handler(self)
        if d.get("action") is None:
            d.pop("action", None)
        return d


class MessageListResponse(BaseModel):
    """Message list response wrapped in items array."""
    items: List[MessageResponse]


class SendMessageRequest(BaseModel):
    """Payload for sending a message to a conversation."""
    request_id: Optional[str] = Field(default=None, description="Client-provided UUID for idempotency")
    message: Optional[str] = Field(default=None, description="User message text (max 2000 chars)")


class SendMessageResponse(BaseModel):
    """Pair of messages returned upon successfully sending a message."""
    user_message: MessageResponse
    assistant_message: MessageResponse
    sources: List[SourceResponse] = Field(default_factory=list)
    action: Optional[AssistantActionResponse] = None

    @model_serializer(mode="wrap")
    def _serialize(self, handler):
        d = handler(self)
        if d.get("action") is None:
            d.pop("action", None)
        return d


class ErrorDetail(BaseModel):
    """Structured error information."""
    code: str
    message: str


class ErrorResponse(BaseModel):
    """Standardized API error envelope."""
    error: ErrorDetail
