"""Configuration settings for the backend application."""

import os
from pathlib import Path

# Base directory of the backend project (backend/)
BASE_DIR = Path(__file__).resolve().parent.parent

# Database file location (defaults to backend/tro_ly_ao.db, excluded by .gitignore)
DEFAULT_DB_PATH = str(BASE_DIR / "tro_ly_ao.db")
DATABASE_PATH = os.getenv("SQLITE_DB_PATH", DEFAULT_DB_PATH)
