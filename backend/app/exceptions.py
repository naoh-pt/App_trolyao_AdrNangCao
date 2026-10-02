"""Custom exceptions and error handlers matching the API contract."""

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


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Fallback handler for unhandled exceptions to prevent leaking tracebacks."""
    return JSONResponse(
        status_code=500,
        content={"error": {"code": "INTERNAL_ERROR", "message": "Đã xảy ra lỗi máy chủ nội bộ"}},
    )
