"""Configuration settings for the backend application."""

import os
from pathlib import Path

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

try:
    GEMINI_TIMEOUT_MS = int(os.getenv("GEMINI_TIMEOUT_MS", "60000"))
except ValueError:
    GEMINI_TIMEOUT_MS = 60000
