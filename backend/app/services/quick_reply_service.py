"""Deterministic local quick replies for simple conversational intents."""

import re
from typing import Optional, Tuple

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


def get_quick_reply(message: str) -> Optional[Tuple[str, str]]:
    """Determine if a message matches a deterministic quick-reply intent.

    Returns (reply_text, emotion) if matched, or None if the message should proceed to AI/RAG.
    """
    normalized = normalize_for_quick_reply(message)
    if not normalized:
        return None

    for intent, pattern in _INTENT_PATTERNS.items():
        if pattern.match(normalized):
            return QUICK_REPLIES[intent]

    return None
