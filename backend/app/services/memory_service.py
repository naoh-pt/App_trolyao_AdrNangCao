"""Explicit, owner-scoped personal memory. Call mutations inside a write transaction."""

import re
import unicodedata
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from app.services.assistant_action_service import VIETNAM_TZ, _CALENDAR_DATE_PATTERN, _calendar_start

SENSITIVE_REPLY = "Anna không lưu mật khẩu, mã OTP hoặc thông tin bí mật để bảo vệ bạn nhé."


def clock_now():
    return datetime.now(timezone.utc)


def iso(now):
    return now.astimezone(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def clean(text):
    return " ".join(unicodedata.normalize("NFC", text).split()).strip(" .,!?:;")


def canonical(text):
    return re.sub(r"^(?:mình|tôi|em|bạn)\b", "bạn", clean(text), flags=re.I)


def sensitive(text):
    return bool(re.search(
        r"mật\s*khẩu|password|passphrase|\botp(?:\b|(?=\d))|api[ _-]*key|khóa\s*(?:api|bí mật|riêng)|"
        r"private[ _-]*key|access[ _-]*token|bearer\s+|\btoken\b|-----BEGIN|"
        r"\b(?:\d[ -]?){13,19}\b|AIza[\w-]{20,}|gsk_[\w-]+|sk-[\w-]+|"
        r"\beyJ[\w-]{8,}\.[\w-]{8,}\.[\w-]{8,}", text, re.I))


@dataclass(frozen=True)
class MemoryCommand:
    operation: str
    content: str = ""


def parse_memory_command(text):
    text = " ".join(unicodedata.normalize("NFC", text).split()).strip()
    if clean(text).casefold() in {"anna nhớ gì về mình", "bạn đang nhớ gì về mình"}:
        return MemoryCommand("list")
    match = re.fullmatch(r"(?:Anna\s+)?hãy\s+nhớ(?:\s+rằng\s+|\s*:\s*)(.*)", text, re.I)
    if match:
        return MemoryCommand("save", match[1])
    match = re.fullmatch(r"(?:Anna\s+)?hãy\s+quên\s+(?:(?:việc|thông tin)\s+)?(.*)", text, re.I)
    return MemoryCommand("forget", match[1]) if match else None


def active_memories(db, owner, now=None, limit=30):
    return db.execute(
        "SELECT * FROM personal_memories WHERE client_id = ? AND (expires_at IS NULL OR expires_at > ?) ORDER BY created_at, id LIMIT ?",
        (owner, iso(now or clock_now()), limit),
    ).fetchall()


def owned_memories(db, owner):
    return db.execute("SELECT * FROM personal_memories WHERE client_id = ? ORDER BY created_at, id", (owner,)).fetchall()


def resolve_date(expression, now):
    match = _CALENDAR_DATE_PATTERN.fullmatch(clean(expression))
    if not match:
        return None, "Bạn hãy dùng hôm nay, ngày mai, ngày kia hoặc thứ cụ thể tuần này/tuần sau nhé."
    result, error = _calendar_start(match, 23, 59, now.astimezone(VIETNAM_TZ))
    if result is None:
        return None, error
    if result.date() < now.astimezone(VIETNAM_TZ).date():
        return None, "Ngày này đã qua rồi. Bạn chọn một ngày từ hôm nay trở đi nhé."
    return result.date(), ""


def memory_reply(db, owner, command, now=None):
    now = now or clock_now()
    rows = owned_memories(db, owner) if command.operation == "forget" else active_memories(db, owner, now)
    if command.operation == "list":
        text = "Hiện Anna đang nhớ:\n" + "\n".join(f"{index}. {row['content']}." for index, row in enumerate(rows, 1)) if rows else "Anna chưa lưu điều gì về bạn. Hãy nhắn “Anna hãy nhớ: ...” nhé."
        return text, "happy" if rows else "neutral"
    content = canonical(command.content)
    if command.operation == "forget":
        exact = [row for row in rows if row["normalized_content"] == content.casefold()]
        matches = exact or [row for row in rows if content and content.casefold() in row["normalized_content"]]
        if len(matches) != 1:
            return "Anna chưa xác định được đúng một thông tin. Bạn mở Trí nhớ của Anna hoặc nói cụ thể hơn nhé.", "neutral"
        db.execute("DELETE FROM personal_memories WHERE id = ? AND client_id = ?", (matches[0]["id"], owner))
        return f"Anna đã quên thông tin “{matches[0]['content']}” rồi nhé.", "happy"
    if sensitive(content):
        return SENSITIVE_REPLY, "neutral"
    reminder = re.search(r"[.!]\s*nhắc mình khi mở ứng dụng từ\s+(.+)$", content, re.I)
    remind_on = None
    if reminder:
        remind_on, error = resolve_date(reminder[1], now)
        if remind_on is None:
            return error, "neutral"
        content = clean(content[:reminder.start()])
    elif re.search(r"nhắc.*(?:mở|ứng dụng)", content, re.I):
        return "Bạn hãy dùng “Nhắc mình khi mở ứng dụng từ hôm nay” hoặc “từ ngày mai” nhé.", "neutral"
    if not content or len(content) > 300:
        return "Bạn hãy lưu một thông tin từ 1 đến 300 ký tự nhé.", "neutral"
    stable_fact = bool(re.match(r"bạn (?:tên là|thích)\b", content, re.I))
    dates = [] if stable_fact else list(_CALENDAR_DATE_PATTERN.finditer(content))
    event_date = None
    if dates:
        if len(dates) != 1:
            return "Bạn hãy nói rõ một ngày duy nhất cho sự kiện nhé.", "neutral"
        description = clean(_CALENDAR_DATE_PATTERN.sub("", content))
        description = re.sub(r"\b(?:bạn|vào)\b", "", description, flags=re.I).strip()
        if not any(character.isalnum() for character in description):
            return "Bạn hãy nói rõ sự kiện cần ghi nhớ là gì nhé.", "neutral"
        event_date, error = resolve_date(dates[0][0], now)
        if event_date is None:
            return error, "neutral"
    elif remind_on is not None:
        return "Bạn hãy nói rõ ngày của sự kiện cần ghi nhớ trước nhé.", "neutral"
    if event_date and remind_on and remind_on > event_date:
        return "Ngày bắt đầu nhắc cần vào hoặc trước ngày sự kiện nhé.", "neutral"
    normalized = content.casefold()
    duplicate = db.execute("SELECT * FROM personal_memories WHERE client_id = ? AND normalized_content = ?", (owner, normalized)).fetchone()
    if duplicate:
        if duplicate["expires_at"] is not None and duplicate["expires_at"] <= iso(now):
            return "Thông tin này đã được lưu trữ vì quá hạn. Bạn xóa bản cũ trong Trí nhớ của Anna rồi lưu lại nếu muốn tạo sự kiện mới nhé.", "neutral"
        return f"Anna đã có thông tin này rồi nhé: {content}.", "happy"
    if len(rows) >= 30:
        return "Anna đang lưu đủ 30 thông tin. Bạn xóa bớt trong Trí nhớ của Anna trước nhé.", "neutral"
    kind = "event" if event_date else "profile" if re.match(r"bạn tên là\b", content, re.I) else "preference" if re.match(r"bạn thích\b", content, re.I) else "general"
    try:
        expires = iso(datetime.combine(event_date + timedelta(days=1), datetime.min.time(), VIETNAM_TZ)) if event_date else None
    except (OverflowError, ValueError):
        return "Ngày sự kiện vượt phạm vi hỗ trợ. Bạn chọn ngày gần hơn nhé.", "neutral"
    stamp = iso(now)
    db.execute(
        "INSERT INTO personal_memories (id,client_id,kind,content,normalized_content,event_date,remind_on,expires_at,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
        (str(uuid.uuid4()), owner, kind, content, normalized, str(event_date) if event_date else None, str(remind_on) if remind_on else None, expires, stamp, stamp),
    )
    return f"Anna nhớ rồi nhé: {content}. ✨", "happy"
