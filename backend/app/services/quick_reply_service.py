"""Deterministic local quick replies for simple conversational intents."""

import re
import unicodedata
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

VIETNAM_TZ = timezone(timedelta(hours=7))
_WEEKDAYS = ("thứ Hai", "thứ Ba", "thứ Tư", "thứ Năm", "thứ Sáu", "thứ Bảy", "Chủ nhật")

# Accent folding applies only to these new intents; legacy matching stays unchanged.
# Only a complete question with optional address/polite wrappers is accepted.
_LOCAL_TIME_PATTERNS = {
    "time": r"(?:(?:bay gio|hien tai) (?:la )?)?may gio(?: roi)?",
    "date": r"(?:hom nay|ngay hom nay) (?:la )?ngay (?:bao nhieu|may)",
    "weekday": r"(?:hom nay|ngay hom nay) (?:la )?thu may",
    "day_period": r"(?:bay gio|hien tai) (?:dang )?(?:la )?buoi (?:gi|sang hay toi)",
}
_LOCAL_TIME_PATTERNS = {
    intent: re.compile(
        r"(?:anna(?: oi)?\s*,?\s+)?(?:cho (?:minh|toi) hoi )?"
        + pattern + r"(?: (?:nhe|nha|a))?"
    )
    for intent, pattern in _LOCAL_TIME_PATTERNS.items()
}


def _local_time_reply(normalized: str, now: Optional[datetime]) -> Optional[Tuple[str, str]]:
    folded = "".join(
        char for char in unicodedata.normalize("NFD", normalized)
        if unicodedata.category(char) != "Mn"
    ).replace("đ", "d")
    intent = next((key for key, pattern in _LOCAL_TIME_PATTERNS.items() if pattern.fullmatch(folded)), None)
    if intent is None:
        return None
    if now is None:
        local = datetime.now(VIETNAM_TZ)
    else:
        if now.tzinfo is None or now.utcoffset() is None:
            raise ValueError("now must be timezone-aware")
        local = now.astimezone(VIETNAM_TZ)
    if intent == "time":
        reply = f"Bây giờ là {local.hour:02d} giờ {local.minute:02d} phút nhé!"
    elif intent == "date":
        reply = f"Hôm nay là ngày {local:%d/%m/%Y} nhé!"
    elif intent == "weekday":
        reply = f"Hôm nay là {_WEEKDAYS[local.weekday()]}, ngày {local:%d/%m/%Y} nhé!"
    else:
        # Vietnam time: morning 05–10, noon 11–12, afternoon 13–17,
        # evening 18–22, night 23–04 (inclusive hours).
        hour = local.hour
        if 5 <= hour < 11:
            period = "buổi sáng"
        elif 11 <= hour < 13:
            period = "buổi trưa"
        elif 13 <= hour < 18:
            period = "buổi chiều"
        elif 18 <= hour < 23:
            period = "buổi tối"
        else:
            period = "ban đêm"
        reply = f"Bây giờ là {period} nhé!"
    return reply, "happy"

# Supported intent patterns with conservative matching (start and end anchored)
_INTENT_PATTERNS = {
    "greeting": re.compile(
        r"^(xin\s+)?chào(\s+(bạn|cậu|anna))?(\s+(nhé|nha|ạ))?$|"
        r"^(chào(\s+(nhé|nha|ạ)))$|"
        r"^(hi|hello)(\s+(bạn|cậu|anna))?(\s+(nhé|nha|ạ))?$",
        re.IGNORECASE,
    ),
    "thanks": re.compile(
        r"^(cảm|cám)\s+ơn(\s+(bạn|cậu|anna|nhiều))?(\s+(nhiều|nhé|nha|ạ))?$|"
        r"^(cảm|cám)\s+ơn\s+bạn\s+nhiều(\s+(nhé|nha|ạ))?$|"
        r"^thank\s+you(\s+anna)?(\s+(so\s+much|very\s+much))?$|"
        r"^thanks(\s+anna)?(\s+(a\s+lot|so\s+much))?$",
        re.IGNORECASE,
    ),
    "goodbye": re.compile(
        r"^tạm\s+biệt(\s+(bạn|cậu|anna))?(\s+(nhé|nha|ạ))?$|"
        r"^bye(\s*(bye|anna))?(\s+(nhé|nha|ạ))?$|"
        r"^goodbye(\s+anna)?(\s+(nhé|nha|ạ))?$|"
        r"^hẹn\s+gặp\s+lại(\s+(bạn|cậu|anna))?(\s+(nhé|nha|ạ))?$",
        re.IGNORECASE,
    ),
    "identity": re.compile(
        r"^(bạn|cậu)\s+là\s+ai(\s+(thế|vậy|ạ))?$|"
        r"^(bạn|cậu)\s+tên(\s+là)?\s+gì(\s+(thế|vậy|ạ))?$|"
        r"^tên(\s+của)?\s+(bạn|cậu)\s+là\s+gì(\s+(thế|vậy|ạ))?$|"
        r"^anna\s+là\s+ai(\s+(thế|vậy|ạ))?$|"
        r"^ai\s+đây(\s+(thế|vậy|ạ))?$",
        re.IGNORECASE,
    ),
    "capabilities": re.compile(
        r"^(bạn|cậu|anna)\s+(làm\s+được\s+(gì|những\s+gì)|có\s+thể\s+(làm|giúp)(\s+được)?\s+gì(\s+cho\s+mình)?|giúp\s+được\s+gì|biết\s+làm\s+gì)(\s+(thế|vậy|ạ))?$|"
        r"^(bạn|cậu|anna)\s+có\s+thể\s+làm\s+được\s+gì(\s+(thế|vậy|ạ))?$|"
        r"^(bạn|cậu|anna)\s+giúp\s+được\s+những\s+gì(\s+(thế|vậy|ạ))?$",
        re.IGNORECASE,
    ),
}

QUICK_REPLIES = {
    "greeting": (
        "Chào bạn nhé! Mình là Anna, trợ lý ảo của bạn. Rất vui được gặp bạn hôm nay! Bạn cần mình hỗ trợ gì nào?",
        "happy",
    ),
    "thanks": (
        "Không có gì đâu nè! Giúp được bạn là mình vui rồi. Nếu cần thêm gì cứ gọi Anna nhé!",
        "happy",
    ),
    "goodbye": (
        "Tạm biệt bạn nha! Chúc bạn một ngày học tập thật tốt và hẹn gặp lại bạn sớm nhé!",
        "happy",
    ),
    "identity": (
        "Mình là Anna - trợ lý ảo hỗ trợ học tập và đời sống sinh viên tại Học viện Kỹ thuật Mật mã. Rất vui được đồng hành cùng bạn nè!",
        "happy",
    ),
    "capabilities": (
        "Mình có thể hỗ trợ bạn tra cứu thông tin học tập, quy chế tại Học viện Kỹ thuật Mật mã, giải đáp thắc mắc sinh viên và trò chuyện cùng bạn. Bạn cần hỗ trợ việc gì nào?",
        "happy",
    ),
}


def normalize_for_quick_reply(text: str) -> str:
    """Normalize input message: strip whitespace, lowercase, collapse spaces, strip ending punctuation."""
    if not text:
        return ""
    cleaned = text.strip().lower()
    cleaned = re.sub(r"\s+", " ", cleaned)
    cleaned = re.sub(r"[.!?~,;:…]+$", "", cleaned).strip()
    return cleaned


def get_quick_reply(message: str, *, now: Optional[datetime] = None) -> Optional[Tuple[str, str]]:
    """Determine if a message matches a deterministic quick-reply intent.

    Returns (reply_text, emotion) if matched, or None if the message should proceed to AI/RAG.
    Optional timezone-aware ``now`` makes local time replies deterministic in tests.
    Production callers keep using get_quick_reply(message); no machine timezone is used.
    """
    normalized = normalize_for_quick_reply(message)
    if not normalized:
        return None

    for intent, pattern in _INTENT_PATTERNS.items():
        if pattern.match(normalized):
            return QUICK_REPLIES[intent]

    return _local_time_reply(normalized, now)
