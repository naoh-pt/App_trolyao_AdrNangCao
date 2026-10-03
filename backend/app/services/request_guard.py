"""Bounded, process-local ownership for a message request ID."""

from contextlib import contextmanager
from dataclasses import dataclass, field
from threading import Lock
from typing import Iterator

from app.exceptions import RequestInProgressException


WAIT_SECONDS = 35.0


@dataclass
class _Entry:
    lock: Lock = field(default_factory=Lock)
    users: int = 0


_registry_lock = Lock()
_entries: dict[str, _Entry] = {}


@contextmanager
def own_request(request_id: str) -> Iterator[None]:
    """Serialize the same key in this process; remove idle entries safely."""
    with _registry_lock:
        entry = _entries.setdefault(request_id, _Entry())
        entry.users += 1

    acquired = entry.lock.acquire(timeout=WAIT_SECONDS)
    try:
        if not acquired:
            raise RequestInProgressException()
        yield
    finally:
        if acquired:
            entry.lock.release()
        with _registry_lock:
            entry.users -= 1
            if entry.users == 0:
                del _entries[request_id]
