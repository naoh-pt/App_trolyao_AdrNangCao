"""Main entrypoint for the FastAPI backend application."""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1.conversations import router as conversations_router
from app.api.v1.health import router as health_router
from app.db.connection import init_db
from app.exceptions import (
    APIException,
    api_exception_handler,
    generic_exception_handler,
    http_exception_handler,
    validation_exception_handler,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler to initialize SQLite tables on startup."""
    init_db()
    yield


app = FastAPI(
    title="Tro Ly Ao Backend API",
    description="FastAPI backend for 2D Virtual Assistant Android app",
    version="0.2.0",
    lifespan=lifespan,
)

# Exception handlers ensuring uniform error schema: {"error": {"code": "...", "message": "..."}}
app.add_exception_handler(APIException, api_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# Enable CORS for local development and testing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API v1 routes
app.include_router(health_router, prefix="/api/v1")
app.include_router(conversations_router, prefix="/api/v1")


@app.get("/health", include_in_schema=False)
def root_health():
    """Fallback root health check endpoint."""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
