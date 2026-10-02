"""Pydantic schemas for Conversation and Message resources."""

from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


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


class MessageResponse(BaseModel):
    """Message representation in API responses."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    role: str
    text: str
    emotion: Optional[str] = None
    created_at: str


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


class ErrorDetail(BaseModel):
    """Structured error information."""
    code: str
    message: str


class ErrorResponse(BaseModel):
    """Standardized API error envelope."""
    error: ErrorDetail
