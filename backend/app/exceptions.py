"""Custom exceptions and error handlers matching the API contract."""

import sqlite3

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class APIException(Exception):
    """Base API exception that renders to {"error": {"code": "...", "message": "..."}}."""

    def __init__(self, status_code: int, code: str, message: str):
        self.status_code = status_code
        self.code = code
        self.message = message
        super().__init__(message)


class InvalidClientIdException(APIException):
    def __init__(self, message: str = "Header X-Client-Id không hợp lệ hoặc bị thiếu (yêu cầu định dạng UUID)"):
        super().__init__(status_code=400, code="INVALID_CLIENT_ID", message=message)


class InvalidIdException(APIException):
    def __init__(self, message: str = "ID cuộc trò chuyện không hợp lệ (yêu cầu định dạng UUID)"):
        super().__init__(status_code=400, code="INVALID_ID", message=message)


class ConversationNotFoundException(APIException):
    def __init__(self, message: str = "Cuộc trò chuyện không tồn tại"):
        super().__init__(status_code=404, code="NOT_FOUND", message=message)


class InvalidMessageException(APIException):
    def __init__(self, message: str = "Nội dung tin nhắn không hợp lệ"):
        super().__init__(status_code=400, code="INVALID_MESSAGE", message=message)


class InvalidRequestIdException(APIException):
    def __init__(self, message: str = "request_id là bắt buộc và phải là định dạng UUID hợp lệ"):
        super().__init__(status_code=400, code="INVALID_REQUEST_ID", message=message)


class RequestIdConflictException(APIException):
    def __init__(self, message: str = "Request ID đã được sử dụng với nội dung tin nhắn khác"):
        super().__init__(status_code=409, code="REQUEST_ID_CONFLICT", message=message)


class LLMUnavailableException(APIException):
    def __init__(self, message: str = "Không thể kết nối AI"):
        super().__init__(status_code=503, code="LLM_UNAVAILABLE", message=message)


class LLMTimeoutException(APIException):
    def __init__(self, message: str = "Yêu cầu xử lý AI quá thời gian chờ"):
        super().__init__(status_code=504, code="LLM_TIMEOUT", message=message)


class RequestInProgressException(APIException):
    def __init__(self):
        super().__init__(503, "REQUEST_IN_PROGRESS", "Yêu cầu đang xử lý; vui lòng thử lại với cùng request_id")


class InvalidAIReplyException(APIException):
    def __init__(self):
        super().__init__(503, "LLM_UNAVAILABLE", "AI không trả về câu trả lời hợp lệ")


class RAGUnavailableException(APIException):
    def __init__(self, message: str = "Kho kiến thức hiện chưa sẵn sàng"):
        super().__init__(503, "RAG_UNAVAILABLE", message)


class InvalidDocumentException(APIException):
    def __init__(self, message: str = "Tài liệu không hợp lệ hoặc không thể trích xuất văn bản"):
        super().__init__(400, "INVALID_DOCUMENT", message)


class AdminAuthorizationException(APIException):
    def __init__(self):
        super().__init__(403, "FORBIDDEN", "Thiếu hoặc sai X-Admin-Token")


async def api_exception_handler(request: Request, exc: APIException) -> JSONResponse:
    """Handle custom API exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.code, "message": exc.message}},
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Handle Starlette/FastAPI HTTPExceptions with standard error shape."""
    code = "NOT_FOUND" if exc.status_code == 404 else ("BAD_REQUEST" if exc.status_code == 400 else "ERROR")
    message = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": code, "message": message}},
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle request validation errors without exposing internal tracebacks."""
    errors = exc.errors()
    msg = errors[0].get("msg", "Dữ liệu yêu cầu không hợp lệ") if errors else "Dữ liệu yêu cầu không hợp lệ"
    return JSONResponse(
        status_code=400,
        content={"error": {"code": "BAD_REQUEST", "message": f"Dữ liệu không hợp lệ: {msg}"}},
    )


async def sqlite_operational_exception_handler(request: Request, exc: sqlite3.OperationalError) -> JSONResponse:
    """Expose only transient lock contention as a retryable error."""
    error_code = getattr(exc, "sqlite_errorcode", None)
    busy = (error_code is not None and error_code & 0xFF in {sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED})
    busy = busy or "locked" in str(exc).lower() or "busy" in str(exc).lower()
    if busy:
        return JSONResponse(
            status_code=503,
            content={"error": {"code": "DATABASE_BUSY", "message": "Cơ sở dữ liệu đang bận; thử lại với cùng request_id"}},
            headers={"Retry-After": "1"},
        )
    return await generic_exception_handler(request, exc)


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Fallback handler for unhandled exceptions to prevent leaking tracebacks."""
    return JSONResponse(
        status_code=500,
        content={"error": {"code": "INTERNAL_ERROR", "message": "Đã xảy ra lỗi máy chủ nội bộ"}},
    )
