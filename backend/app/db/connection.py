"""SQLite connection manager and database initialization."""

import sqlite3
from pathlib import Path
from typing import Generator, Optional
import app.config as app_config


def get_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    """Create a new SQLite connection with foreign keys enabled."""
    target_path = db_path or app_config.DATABASE_PATH
    Path(target_path).parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(target_path, timeout=15.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    return conn


def init_db(db_path: Optional[str] = None) -> None:
    """Initialize database tables and indexes."""
    with get_connection(db_path) as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                client_id TEXT NOT NULL,
                title TEXT NOT NULL DEFAULT 'Cuộc trò chuyện mới',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_conversations_client_updated
                ON conversations(client_id, updated_at DESC);

            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                conversation_id TEXT NOT NULL,
                role TEXT NOT NULL,
                text TEXT NOT NULL,
                emotion TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_messages_conv_created
                ON messages(conversation_id, created_at ASC);

            CREATE TABLE IF NOT EXISTS idempotency_records (
                request_id TEXT PRIMARY KEY,
                client_id TEXT NOT NULL,
                conversation_id TEXT NOT NULL,
                normalized_message TEXT NOT NULL,
                user_message_id TEXT NOT NULL,
                assistant_message_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
                FOREIGN KEY (user_message_id) REFERENCES messages(id) ON DELETE CASCADE,
                FOREIGN KEY (assistant_message_id) REFERENCES messages(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_idempotency_lookup
                ON idempotency_records(client_id, conversation_id, request_id);
        """)


def get_db() -> Generator[sqlite3.Connection, None, None]:
    """FastAPI dependency yielding an active SQLite connection."""
    conn = get_connection()
    try:
        yield conn
    finally:
        conn.close()
