"""Bounded surface normalization; original messages remain untouched in persistence."""
import re
import unicodedata


def normalize_intent(text: str) -> str:
    text = " ".join(unicodedata.normalize("NFC", text[:2000]).split()).strip(" .,?!;:")
    # A greeting before a real question is a wrapper, never a complete greeting.
    text = re.sub(r"^xin chào Anna\s*[,!:]\s*(?:cho mình hỏi\s+)?", "", text, flags=re.I)
    text = re.sub(r"^(?:(?:này\s+)?Anna(?:\s+ơi)?\s*[,!:]?\s+(?!(?:là|có thể|giúp được|tên)\b)|làm ơn\s+)", "", text, flags=re.I)
    for _ in range(4):
        updated = re.sub(r"(?:\s+|[,!]\s*)(?:nhé|nha|với|giúp mình|giúp tôi|được không|vậy|cho mình)$", "", text, flags=re.I).strip(" .,?!;:")
        if updated == text:
            break
        text = updated
    text = re.sub(r"^nhớ giúp (?:mình|tôi) là\s+", "hãy nhớ: ", text, flags=re.I)
    # Keep explicit blank-save commands recognizable (and rejected locally).
    if re.fullmatch(r"hãy nhớ", text, re.I):
        text += ": "
    if text.casefold() == "nhớ gì về mình":
        text = "Anna nhớ gì về mình"
    text = re.sub(r"^dẫn (?:mình|tôi) (?:đến|tới)\s+", "chỉ đường đến ", text, flags=re.I)
    text = re.sub(r"^tạo cho (?:mình|tôi) (?:một )?lịch\b", "tạo lịch", text, flags=re.I)
    return text
