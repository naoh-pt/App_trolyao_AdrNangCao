"""Pytest configuration and fixtures for testing with an isolated temporary SQLite database."""

import sqlite3
import os
import socket
from typing import Generator
import pytest
from fastapi.testclient import TestClient

# Tests must always use deterministic Mock AI and never the developer's key.
os.environ["USE_REAL_AI"] = "false"
os.environ["RAG_ENABLED"] = "false"
os.environ["GEMINI_API_KEY"] = ""

import app.config as app_config
from app.db.connection import get_connection, get_db, init_db
from app.main import app


@pytest.fixture(autouse=True)
def offline_network(monkeypatch):
    """Fail closed if a fake accidentally attempts a real external connection."""
    original = socket.socket.connect

    def connect(sock, address):
        if isinstance(address, tuple) and address[0] not in {"127.0.0.1", "::1", "localhost"}:
            raise AssertionError("External network is forbidden in automated tests")
        return original(sock, address)

    monkeypatch.setattr(socket.socket, "connect", connect)


@pytest.fixture(autouse=True)
def temp_db_file(tmp_path, monkeypatch):
    """Provide a path to a temporary SQLite database file and isolate configuration."""
    db_file = str(tmp_path / "test_isolated.db")
    monkeypatch.setenv("SQLITE_DB_PATH", db_file)
    monkeypatch.setattr(app_config, "DATABASE_PATH", db_file)
    init_db(db_file)
    return db_file


@pytest.fixture
def client(temp_db_file) -> Generator[TestClient, None, None]:
    """TestClient configured with dependency override pointing to isolated temporary database."""
    def override_get_db() -> Generator[sqlite3.Connection, None, None]:
        conn = get_connection(temp_db_file)
        try:
            yield conn
        finally:
            conn.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
