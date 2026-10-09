"""Configuration settings for the backend application."""

import os
from pathlib import Path
from typing import Mapping

from dotenv import load_dotenv

# Base directory of the backend project (backend/)
BASE_DIR = Path(__file__).resolve().parent.parent

# Load backend/.env before routers and AI clients are imported. This works with
# ``uvicorn app.main:app --reload`` as well as the top-level entrypoint.
load_dotenv(BASE_DIR / ".env")

# Database file location (defaults to backend/tro_ly_ao.db, excluded by .gitignore)
DEFAULT_DB_PATH = str(BASE_DIR / "tro_ly_ao.db")
DATABASE_PATH = os.getenv("SQLITE_DB_PATH", DEFAULT_DB_PATH)


def _as_bool(value: str | None, default: bool = False) -> bool:
    """Parse environment boolean values without silently accepting typos."""
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


USE_REAL_AI = _as_bool(os.getenv("USE_REAL_AI"), default=False)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
GEMINI_EMBEDDING_MODEL = os.getenv("GEMINI_EMBEDDING_MODEL", "gemini-embedding-2")

def read_timeout_config(environ: Mapping[str, str]) -> tuple[int, int]:
    """Return generation and embedding timeouts within the demo request budget.

    GEMINI_TIMEOUT_MS remains an alias for existing installations. The new
    generation setting takes precedence when both are present.
    """
    generation_raw = environ.get("GEMINI_GENERATION_TIMEOUT_MS")
    if generation_raw is None:
        generation_raw = environ.get("GEMINI_TIMEOUT_MS", "38000")
    embedding_raw = environ.get("RAG_TIMEOUT_MS", "9000")
    try:
        generation = int(generation_raw)
        embedding = int(embedding_raw)
    except (TypeError, ValueError) as exc:
        raise ValueError("AI timeout configuration must use integer milliseconds") from exc
    if not 1 <= generation <= 45000:
        raise ValueError("Gemini generation timeout must be between 1 and 45000 ms")
    if not 1 <= embedding <= 15000:
        raise ValueError("RAG embedding timeout must be between 1 and 15000 ms")
    if generation + embedding > 55000:
        raise ValueError("Combined AI timeout budget must not exceed 55000 ms")
    return generation, embedding


GEMINI_GENERATION_TIMEOUT_MS, RAG_TIMEOUT_MS = read_timeout_config(os.environ)
# Preserve the old exported name for code importing app.config.GEMINI_TIMEOUT_MS.
GEMINI_TIMEOUT_MS = GEMINI_GENERATION_TIMEOUT_MS

RAG_ENABLED = _as_bool(os.getenv("RAG_ENABLED"), default=False)
RAG_ADMIN_TOKEN = os.getenv("RAG_ADMIN_TOKEN")
RAG_COLLECTION = os.getenv("RAG_COLLECTION", "student_handbook_chunks")
RAG_CHROMA_PATH = os.getenv("RAG_CHROMA_PATH", str(BASE_DIR / "chroma_data"))
RAG_TOP_K = int(os.getenv("RAG_TOP_K", "4"))
RAG_MIN_SCORE = float(os.getenv("RAG_MIN_SCORE", "0.70"))
