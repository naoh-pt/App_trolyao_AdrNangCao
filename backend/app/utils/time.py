"""Time and date helper functions."""

from datetime import datetime, timezone


def utc_now_iso() -> str:
    """Return the current UTC timestamp formatted as ISO 8601 with a 'Z' suffix."""
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")
