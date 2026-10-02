"""Common API dependencies and validation helpers."""

import uuid
from typing import Optional
from fastapi import Header
from app.exceptions import InvalidClientIdException, InvalidIdException


def get_client_id(x_client_id: Optional[str] = Header(None, alias="X-Client-Id")) -> str:
    """Validate and extract the X-Client-Id header.
    
    Must be a non-empty, valid UUID string.
    """
    if not x_client_id or not x_client_id.strip():
        raise InvalidClientIdException("Header X-Client-Id là bắt buộc")
    
    try:
        parsed = uuid.UUID(x_client_id.strip())
        return str(parsed)
    except (ValueError, TypeError, AttributeError):
        raise InvalidClientIdException("Header X-Client-Id phải là định dạng UUID hợp lệ")


def validate_conversation_id(id: str) -> str:
    """Validate that a path parameter conversation ID is a valid UUID."""
    if not id or not id.strip():
        raise InvalidIdException("ID cuộc trò chuyện là bắt buộc")
        
    try:
        parsed = uuid.UUID(id.strip())
        return str(parsed)
    except (ValueError, TypeError, AttributeError):
        raise InvalidIdException("ID cuộc trò chuyện phải là định dạng UUID hợp lệ")
