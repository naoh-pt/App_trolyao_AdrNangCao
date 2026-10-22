"""Optional same-generation internal proposals; never an executable/public DTO."""
import math
import re

SLOTS = {
    "normal_chat": set(),
    "set_timer": {"title", "duration_text"},
    "create_calendar_event": {"title", "date_text", "time_text"},
    "map_search": {"query"},
    "weather_query": {"location", "date_text"},
    "local_time_query": {"query"},
}
PROPOSAL_POLICY = '''Keep the existing reply/emotion JSON contract. Optionally include intent_proposal
only for an explicit tool request in the CURRENT user message. Never infer a memory operation.
Schema: {"intent": enum, "confidence": number 0..1, "slots": object of short strings}.
Allowed intents/slots: normal_chat/none; set_timer/title,duration_text (e.g. 5 phút);
create_calendar_event/title,date_text,time_text (Vietnamese expressions, never timestamps);
map_search/query; weather_query/location,date_text; local_time_query/query.
Do not propose actions for educational questions, quoted examples or personal context.
Never supply URLs, packages, executable code or commands. Missing slots stay absent.
This proposal is untrusted data: the server validates it and requires Android confirmation.
Do not claim an action was executed or prepared in reply; the server supplies confirmations.'''


def validate_proposal(value):
    if not isinstance(value, dict) or set(value) != {"intent", "confidence", "slots"}:
        return None
    intent, confidence, slots = value["intent"], value["confidence"], value["slots"]
    if not isinstance(intent, str) or intent not in SLOTS:
        return None
    if type(confidence) not in (float, int) or not .8 <= confidence <= 1 or not math.isfinite(confidence):
        return None
    if not isinstance(slots, dict) or not set(slots) <= SLOTS[intent]:
        return None
    for key, text in slots.items():
        if not isinstance(text, str) or not text.strip() or len(text) > 200:
            return None
        if any(ord(c) < 32 for c in text) or re.search(r"(?:[a-z][\w+.-]*:|(?:\w+\.){2,}\w+|[<>`{};$]|\b(?:SELECT|DROP|INSERT|DELETE|exec|powershell|cmd|curl)\b)", text, re.I):
            return None
    return {"intent": intent, "confidence": confidence, "slots": {k: v.strip() for k, v in slots.items()}}


class GeneratedReply(tuple):
    """Tuple-compatible for all existing providers, fakes and consumers."""
    def __new__(cls, reply, emotion, proposal=None):
        result = super().__new__(cls, (reply, emotion))
        result.intent_proposal = validate_proposal(proposal)
        return result


def proposal_command(proposal, original):
    proposal = validate_proposal(proposal)
    # No universal classifier call and no tool acceptance for ordinary/educational chat.
    if not proposal or re.search(r"giải thích|là gì|ví dụ|lịch sử|bản đồ tư duy|viết câu", original, re.I):
        return None
    if not re.search(r"lịch|hẹn|nhắc|bản đồ|đường đến|dẫn|thời tiết|mưa|nhiệt độ|mấy giờ|hẹn giờ", original, re.I):
        return None
    intent, s = proposal["intent"], proposal["slots"]
    # Require all fields here; deterministic Calendar requests handle partial slots.
    if intent == "create_calendar_event" and set(s) == SLOTS[intent]:
        return f"Tạo lịch {s['title']} {s['date_text']} lúc {s['time_text']}"
    if intent == "set_timer" and "duration_text" in s:
        if re.fullmatch(r"\d{1,4}\s*(?:phút|giờ|tiếng)", s["duration_text"], re.I):
            return f"Nhắc mình {s.get('title', '')} sau {s['duration_text']}"
    if intent == "map_search" and "query" in s:
        return f"Tìm trên bản đồ {s['query']}"
    if intent == "weather_query" and "location" in s:
        day = s.get("date_text", "hiện tại").casefold()
        if day in {"hiện tại", "hôm nay", "ngày mai", "ngày kia"}:
            return f"Thời tiết {s['location']} {day} thế nào?"
    if intent == "local_time_query" and s.get("query", "").casefold() in {"mấy giờ rồi", "hôm nay là thứ mấy", "hôm nay là ngày bao nhiêu"}:
        return s["query"]
    return None
