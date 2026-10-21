"""Deterministic assistant action recognition service for Anna.

Supports:
- Relative timer: set_timer
- Calendar event: create_calendar_event
- Map search: map_search

Never generates arbitrary deep links, URIs, or package names.
All actions require explicit user confirmation via UI action buttons.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import re
from typing import Any, Dict, Optional, Tuple

VIETNAM_TZ = timezone(timedelta(hours=7), name="Asia/Ho_Chi_Minh")

# Timer duration limits: 1 minute (60s) to 24 hours (86400s)
MIN_TIMER_SECONDS = 60
MAX_TIMER_SECONDS = 86400

# Calendar default duration: 30 minutes
DEFAULT_CALENDAR_DURATION_MINUTES = 30

# Max allowed place query length
MAX_MAP_QUERY_LENGTH = 200


@dataclass
class AssistantAction:
    type: str
    label: str
    message: Optional[str] = None
    duration_seconds: Optional[int] = None
    title: Optional[str] = None
    start_at: Optional[str] = None
    end_at: Optional[str] = None
    query: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "label": self.label,
            "message": self.message,
            "duration_seconds": self.duration_seconds,
            "title": self.title,
            "start_at": self.start_at,
            "end_at": self.end_at,
            "query": self.query,
        }


@dataclass
class ActionResult:
    reply: str
    emotion: str
    action: Optional[AssistantAction] = None


def normalize_vietnamese_text(text: str) -> str:
    """Normalize whitespace and lowercase for intent pattern matching."""
    if not text:
        return ""
    cleaned = text.strip().lower()
    cleaned = re.sub(r"\s+", " ", cleaned)
    cleaned = re.sub(r"[.!?~,;:…]+$", "", cleaned).strip()
    return cleaned


def _clean_extracted_text(text: str) -> str:
    """Clean extracted task or place text preserving proper casing structure."""
    if not text:
        return ""
    cleaned = re.sub(r"\s+", " ", text.strip())
    cleaned = re.sub(r"^[,\-–—:;\s]+|[,\-–—:;\s]+$", "", cleaned).strip()
    return cleaned


# =============================================================================
# 1. Relative Timer Parsing
# =============================================================================

_TIMER_TRIGGER_PATTERN = re.compile(
    r"^(?:xin\s+)?(?:hãy\s+)?(?:hẹn\s+giờ|nhắc\s+(?:tôi|mình|em|anh|chị|bạn|giúp\s+mình|giúp\s+tôi))|"
    r"\bsau\s+\d+\s*(?:phút|giờ|tiếng)\b|"
    r"\bhẹn\s+giờ\b",
    re.IGNORECASE,
)

_TIMER_DURATION_PATTERN = re.compile(
    r"(?:sau\s+)?(\d+)\s*(phút|giờ|tiếng)(?:\s+nữa)?",
    re.IGNORECASE,
)


def _parse_timer(raw_text: str, norm_text: str) -> Optional[ActionResult]:
    """Parse relative timer requests or clarification responses."""
    # Calendar requests containing 'đặt lịch' or 'lúc' should not be treated as timers
    if re.search(r"\b(đặt\s+lịch|tạo\s+lịch|lên\s+lịch|lúc\s+\d+|hôm\s+nay|ngày\s+mai|tối\s+mai|sáng\s+mai)\b", norm_text):
        return None

    # Must match timer trigger
    if not _TIMER_TRIGGER_PATTERN.search(norm_text):
        return None

    duration_match = _TIMER_DURATION_PATTERN.search(norm_text)
    if not duration_match:
        # User requested a reminder/timer but omitted the duration
        return ActionResult(
            reply="Bạn muốn mình nhắc việc này sau bao lâu nữa nè? Bạn hãy cho mình biết số phút hoặc số giờ cụ thể nhé!",
            emotion="happy",
            action=None,
        )

    val_str, unit = duration_match.group(1), duration_match.group(2).lower()
    val = int(val_str)

    if unit == "phút":
        duration_seconds = val * 60
        duration_display = f"{val} phút"
        label = f"Đặt hẹn giờ {val} phút"
    else:  # "giờ" or "tiếng"
        duration_seconds = val * 3600
        duration_display = f"{val} giờ"
        label = f"Đặt hẹn giờ {val} giờ"

    if duration_seconds < MIN_TIMER_SECONDS:
        return ActionResult(
            reply="Thời gian hẹn giờ phải từ 1 phút trở lên nè. Bạn muốn mình hẹn giờ bao lâu?",
            emotion="happy",
            action=None,
        )

    if duration_seconds > MAX_TIMER_SECONDS:
        return ActionResult(
            reply="Thời gian hẹn giờ tối đa là 24 giờ thôi nè. Bạn hãy chọn khoảng thời gian ngắn hơn nhé!",
            emotion="happy",
            action=None,
        )

    # Extract user task text
    # Strip leading trigger from raw_text
    task_candidate = re.sub(
        r"^(?:xin\s+)?(?:hãy\s+)?(?:hẹn\s+giờ|nhắc\s+(?:tôi|mình|em|anh|chị|bạn|giúp\s+mình|giúp\s+tôi))\s*",
        "",
        raw_text,
        flags=re.IGNORECASE,
    )
    # Strip duration part
    task_candidate = re.sub(
        r"(?:sau\s+)?\d+\s*(?:phút|giờ|tiếng)(?:\s+nữa)?",
        "",
        task_candidate,
        flags=re.IGNORECASE,
    )
    # Strip words like 'để', 'cho', 'về việc'
    task_candidate = re.sub(r"^(?:để|cho|về\s+việc)\s+", "", task_candidate.strip(), flags=re.IGNORECASE)
    task_text = _clean_extracted_text(task_candidate)

    if task_text:
        # Title case first letter
        task_display = task_text[0].upper() + task_text[1:] if len(task_text) > 1 else task_text.upper()
        reply = f"Được rồi! Sau {duration_display} Anna sẽ nhắc bạn {task_text.lower()} nhé."
        message = task_display
    else:
        reply = f"Được rồi! Mình đã chuẩn bị bộ hẹn giờ {duration_display} cho bạn rồi nhé."
        message = f"Hẹn giờ {duration_display}"

    return ActionResult(
        reply=reply,
        emotion="happy",
        action=AssistantAction(
            type="set_timer",
            label=label,
            message=message,
            duration_seconds=duration_seconds,
        ),
    )


# =============================================================================
# 2. Calendar Event Parsing
# =============================================================================

_CALENDAR_TRIGGER_PATTERN = re.compile(
    r"\b(đặt\s+lịch|tạo\s+lịch|lên\s+lịch|thêm\s+lịch)\b|"
    r"^(?:xin\s+)?(?:hãy\s+)?nhắc\s+(?:tôi|mình|em|anh|chị|bạn)\s+.*?\b(lúc\s+\d+|hôm\s+nay|ngày\s+mai|tối\s+mai|sáng\s+mai)\b",
    re.IGNORECASE,
)


def _parse_calendar(raw_text: str, norm_text: str) -> Optional[ActionResult]:
    """Parse calendar event requests with strict time validation in Asia/Ho_Chi_Minh."""
    if not _CALENDAR_TRIGGER_PATTERN.search(norm_text):
        return None

    # Check Day
    day_offset: Optional[int] = None
    if "hôm nay" in norm_text:
        day_offset = 0
    elif any(d in norm_text for d in ("ngày mai", "tối mai", "sáng mai", "chiều mai", " mai")):
        day_offset = 1

    if day_offset is None:
        return ActionResult(
            reply="Bạn muốn đặt lịch cho hôm nay hay ngày mai nè? Bạn nói rõ ngày và giờ giúp mình nhé!",
            emotion="happy",
            action=None,
        )

    # Check Time
    # Look for HH:MM format first
    colon_time = re.search(r"\b(\d{1,2}):(\d{2})\b", norm_text)
    hour: Optional[int] = None
    minute: int = 0

    if colon_time:
        hour = int(colon_time.group(1))
        minute = int(colon_time.group(2))
    else:
        hour_match = re.search(r"\b(?:lúc\s+)?(\d{1,2})\s*(?:giờ|h)\s*(\d{1,2})?\b", norm_text)
        if hour_match:
            hour = int(hour_match.group(1))
            if hour_match.group(2):
                minute = int(hour_match.group(2))

    if hour is None or hour < 0 or hour > 23 or minute < 0 or minute > 59:
        return ActionResult(
            reply="Bạn muốn đặt lịch vào mấy giờ nè? Hãy nói cho mình biết giờ cụ thể nhé!",
            emotion="happy",
            action=None,
        )

    # Check AM/PM modifiers
    has_sang = bool(re.search(r"\b(sáng|buổi sáng|sáng mai)\b", norm_text))
    has_chieu = bool(re.search(r"\b(chiều|buổi chiều|chiều mai)\b", norm_text))
    has_toi = bool(re.search(r"\b(tối|buổi tối|tối mai|đêm)\b", norm_text))

    if has_sang:
        if hour == 12:
            hour = 0
    elif has_chieu or has_toi:
        if 1 <= hour <= 11:
            hour += 12
    elif hour <= 12 and not colon_time:
        # Ambiguous 12-hour without modifier (e.g. "lúc 8 giờ")
        return ActionResult(
            reply="Bạn muốn đặt lịch lúc mấy giờ sáng hay tối nè? Bạn nói rõ hơn giúp mình nhé!",
            emotion="happy",
            action=None,
        )

    now_vn = datetime.now(VIETNAM_TZ)
    target_date = (now_vn + timedelta(days=day_offset)).date()
    start_dt = datetime(target_date.year, target_date.month, target_date.day, hour, minute, 0, tzinfo=VIETNAM_TZ)

    if start_dt <= now_vn:
        return ActionResult(
            reply="Thời gian này đã qua mất rồi nè. Bạn hãy chọn một mốc thời gian trong tương lai nhé!",
            emotion="happy",
            action=None,
        )

    end_dt = start_dt + timedelta(minutes=DEFAULT_CALENDAR_DURATION_MINUTES)

    # Extract event title
    title_candidate = re.sub(
        r"^(?:xin\s+)?(?:hãy\s+)?(?:đặt\s+lịch|tạo\s+lịch|lên\s+lịch|thêm\s+lịch|nhắc\s+(?:tôi|mình|em|anh|chị|bạn))\s*",
        "",
        raw_text,
        flags=re.IGNORECASE,
    )
    # Remove time and date markers
    title_candidate = re.sub(
        r"\b(?:lúc\s+)?\d{1,2}(?::\d{2}|\s*(?:giờ|h)(?:\s*\d{1,2})?)\s*(?:sáng|chiều|tối|đêm)?\b",
        "",
        title_candidate,
        flags=re.IGNORECASE,
    )
    title_candidate = re.sub(
        r"\b(?:hôm\s+nay|ngày\s+mai|tối\s+mai|sáng\s+mai|chiều\s+mai|mai)\b",
        "",
        title_candidate,
        flags=re.IGNORECASE,
    )
    title_candidate = _clean_extracted_text(title_candidate)
    title = (title_candidate[0].upper() + title_candidate[1:]) if title_candidate else "Sự kiện mới"

    reply = f'Mình đã chuẩn bị lịch hẹn "{title}" cho bạn rồi nè. Bạn nhấn nút bên dưới để mở ứng dụng Lịch và xác nhận nhé!'
    return ActionResult(
        reply=reply,
        emotion="happy",
        action=AssistantAction(
            type="create_calendar_event",
            label="Mở lịch để xác nhận",
            title=title,
            start_at=start_dt.isoformat(),
            end_at=end_dt.isoformat(),
        ),
    )


# =============================================================================
# 3. Map Search Parsing
# =============================================================================

_MAP_EXACT_PATTERNS = [
    # "tìm ... trên bản đồ"
    re.compile(r"^(?:xin\s+)?(?:hãy\s+)?tìm\s+(.*?)\s+trên\s+bản\s+đồ$", re.IGNORECASE),
    # "mở bản đồ tìm ..."
    re.compile(r"^(?:xin\s+)?(?:hãy\s+)?mở\s+bản\s+đồ(?:\s+tìm)?\s+(.*?)$", re.IGNORECASE),
    # "chỉ đường đến/tới ..."
    re.compile(r"^(?:xin\s+)?(?:hãy\s+)?chỉ\s+đường\s+(?:đến|tới|về)\s+(.*?)$", re.IGNORECASE),
    # "tìm đường đến/tới ..."
    re.compile(r"^(?:xin\s+)?(?:hãy\s+)?tìm\s+đường\s+(?:đến|tới|về)\s+(.*?)$", re.IGNORECASE),
    # "bản đồ đến/tới ..."
    re.compile(r"^(?:xin\s+)?(?:hãy\s+)?bản\s+đồ\s+(?:đến|tới)\s+(.*?)$", re.IGNORECASE),
    # "tìm [trên] bản đồ ..." (explicit command prefix, not a general map keyword)
    re.compile(r"^(?:xin\s+)?(?:hãy\s+)?tìm\s+(?:trên\s+)?bản\s+đồ\s+(.*?)$", re.IGNORECASE),
]


def _parse_map(raw_text: str, norm_text: str) -> Optional[ActionResult]:
    """Parse map search requests safely extracting query text without raw URIs."""
    # Check if this is an empty map command
    if norm_text in ("mở bản đồ", "bản đồ", "tìm trên bản đồ", "tìm bản đồ", "chỉ đường", "tìm đường"):
        return ActionResult(
            reply="Bạn muốn tìm địa điểm nào trên bản đồ nè? Hãy nói cho mình biết tên địa điểm nhé!",
            emotion="happy",
            action=None,
        )

    query: Optional[str] = None
    # Map-only cleanup: preserve casing/internal punctuation and timer/calendar parsing.
    map_text = re.sub(r"[\s.,?!;:]+$", "", raw_text)
    for pattern in _MAP_EXACT_PATTERNS:
        m = pattern.match(map_text)
        if m:
            query = m.group(1).strip()
            break

    if not query:
        return None

    cleaned_query = re.sub(r"[\s.,?!;:]+$", "", re.sub(r"\s+", " ", query).strip())

    # Accept a place name, never a raw URI scheme or Android package identifier.
    if re.search(r"^[a-z][a-z0-9+.-]*:", cleaned_query, re.IGNORECASE) or re.fullmatch(
        r"(?:[a-z][a-z0-9_]*\.){2,}[a-z][a-z0-9_]*", cleaned_query, re.IGNORECASE
    ):
        return ActionResult(
            reply="Bạn hãy nhập tên địa điểm bằng chữ thay vì đường dẫn nhé!",
            emotion="happy",
            action=None,
        )

    if not cleaned_query:
        return ActionResult(
            reply="Bạn muốn tìm địa điểm nào trên bản đồ nè? Hãy nói cho mình biết tên địa điểm nhé!",
            emotion="happy",
            action=None,
        )

    if len(cleaned_query) > MAX_MAP_QUERY_LENGTH:
        cleaned_query = cleaned_query[:MAX_MAP_QUERY_LENGTH].strip()

    reply = f'Mình đã tìm thấy địa điểm "{cleaned_query}" cho bạn. Bạn bấm nút bên dưới để mở bản đồ nhé!'
    return ActionResult(
        reply=reply,
        emotion="happy",
        action=AssistantAction(
            type="map_search",
            label="Mở bản đồ",
            query=cleaned_query,
        ),
    )


# =============================================================================
# Main Entry Point
# =============================================================================

def recognize_action(message: str) -> Optional[ActionResult]:
    """Deterministically recognize assistant actions for timers, calendar events, and maps.

    Returns:
    - ActionResult with an allowlisted AssistantAction when matched and valid.
    - ActionResult with action=None when the intent is recognized but requires clarification.
    - None when the message is not an action intent and should proceed to quick replies / AI.
    """
    if not message or not message.strip():
        return None

    norm = normalize_vietnamese_text(message)
    raw = message.strip()

    # 1. Map Search check
    map_res = _parse_map(raw, norm)
    if map_res is not None:
        return map_res

    # 2. Calendar Event check
    cal_res = _parse_calendar(raw, norm)
    if cal_res is not None:
        return cal_res

    # 3. Relative Timer check
    timer_res = _parse_timer(raw, norm)
    if timer_res is not None:
        return timer_res

    return None
