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
    r"^(?:xin\s+)?(?:hãy\s+)?(?:đặt\s+lịch|tạo\s+lịch|lên\s+lịch|thêm\s+lịch|"
    r"nhắc\s+(?:tôi|mình|em|anh|chị|bạn))\b\s*",
    re.IGNORECASE,
)

_WEEKDAY_NUMBER = {
    "2": 0, "hai": 0, "3": 1, "ba": 1, "4": 2, "tư": 2,
    "5": 3, "năm": 3, "6": 4, "sáu": 4, "7": 5, "bảy": 5,
}
_WEEKDAY_DISPLAY = ("Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu", "Thứ Bảy", "Chủ nhật")
_CALENDAR_DATE_PATTERN = re.compile(
    r"(?<!\w)(?:vào\s+)?(?:"
    r"(?P<relative>hôm\s+nay|ngày\s+(?:mai|kia|mốt)|(?:sáng|chiều|tối)\s+mai|mai)|"
    r"(?P<weekend>cuối\s+tuần\s+(?:này|sau|tới))|"
    r"(?P<weekday>(?:thứ\s+(?:[2-7]|hai|ba|tư|năm|sáu|bảy)|chủ\s+nhật)"
    r"(?:\s+(?:tuần\s+(?:này|sau|tới)|tới))?)|"
    r"(?P<slash>\d{1,2}/\d{1,2}(?:/\d{4})?)|"
    r"(?P<words>ngày\s+\d{1,2}\s+tháng\s+\d{1,2}(?:\s+năm\s+\d{4})?)(?!\s+năm\b)"
    r")(?![\w/])", re.IGNORECASE,
)
_CALENDAR_TIME_PATTERN = re.compile(
    r"(?<![\w:/.-])(?:vào\s+)?(?:lúc\s+)?(?P<hour>\d+)"
    r"(?:(?P<colon>:\d+)|\s*(?:giờ|h)(?:\s*(?P<minute>\d+))?)"
    r"(?:\s*(?:buổi\s+)?(?P<period>sáng|trưa|chiều|tối|đêm))?(?![\w:])",
    re.IGNORECASE,
)


def _calendar_clarification(message: str) -> ActionResult:
    return ActionResult(reply=message, emotion="happy", action=None)


def _calendar_time(match: re.Match, date_period: Optional[str]) -> Tuple[Optional[Tuple[int, int]], str]:
    hour = int(match["hour"])
    minute = int(match["colon"][1:] if match["colon"] else match["minute"] or 0)
    period = match["period"].lower() if match["period"] else date_period
    invalid = "Giờ hoặc phút chưa hợp lệ. Bạn hãy cho mình biết giờ cụ thể từ 00:00 đến 23:59 nhé!"
    if hour > 23 or minute > 59 or (date_period and match["period"] and date_period != period):
        return None, invalid
    if period == "sáng":
        if hour > 12:
            return None, invalid
        hour %= 12
    elif period == "trưa":
        if hour not in (11, 12, 13):
            return None, invalid
    elif period == "chiều":
        if hour == 0 or hour > 18:
            return None, invalid
        if hour < 12:
            hour += 12
    elif period in ("tối", "đêm"):
        if hour == 12:
            hour = 0
        elif 1 <= hour <= 11 and not (period == "đêm" and hour <= 5):
            hour += 12
        elif 6 <= hour <= 17:
            return None, invalid
    elif hour <= 12 and hour != 0 and not match["colon"]:
        return None, "Bạn muốn đặt lịch lúc mấy giờ sáng hay tối nè? Bạn nói rõ hơn giúp mình nhé!"
    return (hour, minute), ""


def _calendar_start(match: re.Match, hour: int, minute: int, now: datetime) -> Tuple[Optional[datetime], str]:
    """Resolve one date expression; explicit weeks never silently roll forward."""
    invalid = "Ngày này chưa hợp lệ. Bạn hãy nói rõ ngày, tháng và năm giúp mình nhé!"
    if match["weekend"]:
        return None, "Bạn muốn chọn thứ Bảy hay Chủ nhật cho cuối tuần nè?"
    if match["relative"]:
        expression = match["relative"].lower()
        offset = 0 if expression == "hôm nay" else 2 if expression in ("ngày kia", "ngày mốt") else 1
        target = now.date() + timedelta(days=offset)
    elif match["weekday"]:
        expression = match["weekday"].lower()
        weekday = 6 if expression.startswith("chủ nhật") else _WEEKDAY_NUMBER[expression.split()[1]]
        monday = now.date() - timedelta(days=now.weekday())
        if "tuần này" in expression:
            target = monday + timedelta(days=weekday)
            if target < now.date():
                name = _WEEKDAY_DISPLAY[weekday]
                return None, f"{name} tuần này đã qua rồi. Bạn muốn đặt vào {name.lower()} tuần sau phải không?"
        elif "tuần sau" in expression or "tuần tới" in expression:
            target = monday + timedelta(days=7 + weekday)
        elif expression.endswith("tới"):
            target = now.date() + timedelta(days=(weekday - now.weekday()) % 7)
            candidate = datetime(target.year, target.month, target.day, hour, minute, tzinfo=VIETNAM_TZ)
            if candidate <= now:
                target += timedelta(days=7)
        else:
            return None, "Bạn muốn chọn ngày đó tuần này hay tuần sau nè?"
    else:
        numbers = [int(number) for number in re.findall(r"\d+", match["slash"] or match["words"])]
        day, month = numbers[:2]
        years = [numbers[2]] if len(numbers) == 3 else range(now.year, min(now.year + 9, 10000))
        for year in years:
            try:
                candidate = datetime(year, month, day, hour, minute, tzinfo=VIETNAM_TZ)
            except ValueError:
                continue
            if len(numbers) == 3 or candidate > now:
                return candidate, ""
        return None, invalid
    return datetime(target.year, target.month, target.day, hour, minute, tzinfo=VIETNAM_TZ), ""


def _parse_calendar(raw_text: str, norm_text: str, now: Optional[datetime] = None) -> Optional[ActionResult]:
    """Parse explicit calendar commands with one date and one time, in either order."""
    text = re.sub(r"\s+", " ", raw_text).strip().rstrip(".,?!;: ")
    trigger = _CALENDAR_TRIGGER_PATTERN.match(text)
    if not trigger:
        return None
    body = text[trigger.end():]
    dates = list(_CALENDAR_DATE_PATTERN.finditer(body))
    reminder = "nhắc" in trigger[0].lower()
    # A name such as "Mai" in an explicit relative timer must not become a calendar date.
    if (reminder and re.search(r"\bsau\s+\d", norm_text)
            and not re.search(r"\blúc\s+\d", body, re.IGNORECASE)
            and all((item["relative"] or "").lower() == "mai" for item in dates)):
        return None
    # Keep relative timers in their existing parser unless a calendar date or 'lúc' is explicit.
    if reminder and not dates and not re.search(r"\blúc\s+\d", body, re.IGNORECASE):
        return None
    if len(dates) != 1:
        return _calendar_clarification("Bạn muốn đặt lịch cho hôm nay hay ngày mai nè? Bạn nói rõ một ngày cụ thể giúp mình nhé!")
    date_match = dates[0]
    if date_match["weekend"]:
        return _calendar_clarification("Bạn muốn chọn thứ Bảy hay Chủ nhật cho cuối tuần nè?")
    # Blank matched date spans without moving indices; digits in dates cannot be parsed as time.
    without_date = body[:date_match.start()] + " " * len(date_match[0]) + body[date_match.end():]
    times = list(_CALENDAR_TIME_PATTERN.finditer(without_date))
    if len(times) != 1:
        return _calendar_clarification("Bạn muốn đặt lịch vào mấy giờ nè? Hãy nói cho mình biết một giờ cụ thể nhé!")
    time_match = times[0]
    if re.match(r"\s*(?:buổi\s+)?(?:sáng|trưa|chiều|tối|đêm)\b", without_date[time_match.end():], re.IGNORECASE):
        return _calendar_clarification("Bạn hãy chọn một buổi sáng, chiều hoặc tối cụ thể cho giờ hẹn nhé!")
    relative = (date_match["relative"] or "").lower()
    date_period = relative.split()[0] if relative.startswith(("sáng ", "chiều ", "tối ")) else None
    clock, error = _calendar_time(time_match, date_period)
    if clock is None:
        return _calendar_clarification(error)
    title = without_date[:time_match.start()] + " " + without_date[time_match.end():]
    title = _clean_extracted_text(title).strip(".,?!;: ")
    if not title or not any(character.isalnum() for character in title):
        return _calendar_clarification("Bạn muốn đặt tên sự kiện là gì nè? Hãy cho mình biết việc cần lên lịch nhé!")
    title = title[0].upper() + title[1:]
    if now is None:
        now = datetime.now(VIETNAM_TZ)
    elif now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now must be timezone-aware")
    now_vn = now.astimezone(VIETNAM_TZ)
    try:
        start_dt, error = _calendar_start(date_match, *clock, now_vn)
        if start_dt is None:
            return _calendar_clarification(error)
        end_dt = start_dt + timedelta(minutes=DEFAULT_CALENDAR_DURATION_MINUTES)
    except (ValueError, OverflowError):
        return _calendar_clarification("Ngày này chưa hợp lệ. Bạn hãy chọn một ngày khác nhé!")

    if start_dt <= now_vn or end_dt <= start_dt:
        return _calendar_clarification("Thời gian này đã qua mất rồi nè. Bạn hãy chọn một mốc thời gian trong tương lai nhé!")

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

def recognize_action(message: str, *, now: Optional[datetime] = None) -> Optional[ActionResult]:
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
    cal_res = _parse_calendar(raw, norm, now)
    if cal_res is not None:
        return cal_res

    # 3. Relative Timer check
    timer_res = _parse_timer(raw, norm)
    if timer_res is not None:
        return timer_res

    return None
