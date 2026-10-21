"""Calendar slot completion. Read/plan first; apply with the message transaction."""
import json
import re
from dataclasses import dataclass
from datetime import timedelta

from app.services.assistant_action_service import (
    ActionResult, _CALENDAR_DATE_PATTERN, _CALENDAR_TIME_PATTERN,
    _CALENDAR_TRIGGER_PATTERN, _calendar_time, recognize_action,
)
from app.services.memory_service import iso, resolve_date

CANCEL = {"thôi", "bỏ qua", "hủy", "hủy tạo lịch", "không cần nữa"}
KEYS = {"title", "date_text", "time_text"}


@dataclass
class CalendarPlan:
    result: ActionResult | None = None
    slots: dict | None = None
    clear: bool = False


def calendar_slots(text):
    """Extract original-case spans using the existing trusted Calendar grammar."""
    dates = list(_CALENDAR_DATE_PATTERN.finditer(text))
    if len(dates) > 1:
        return None
    rest = text
    slots = {}
    if dates:
        slots["date_text"] = dates[0][0]
        rest = rest[:dates[0].start()] + " " * len(dates[0][0]) + rest[dates[0].end():]
    times = list(_CALENDAR_TIME_PATTERN.finditer(rest))
    if len(times) > 1:
        return None
    if times:
        # Infer period only from an explicit date phrase such as "tối mai".
        relative = (dates[0]["relative"] or "").lower() if dates else ""
        period = relative.split()[0] if relative.startswith(("sáng ", "chiều ", "tối ")) else None
        if _calendar_time(times[0], period)[0] is None:
            return None
        slots["time_text"] = times[0][0]
        rest = rest[:times[0].start()] + " " + rest[times[0].end():]
    title = re.sub(r"\s+", " ", rest).strip(" .,?!;:")
    title = re.sub(r"^(?:vào|lúc)\s+|\s+(?:vào|lúc)$", "", title, flags=re.I).strip()
    if title:
        if title.casefold() in {"vào", "lúc"}:
            return slots
        if len(title) > 200:
            return None
        slots["title"] = title
    return slots


def clarification(slots):
    missing = KEYS - slots.keys()
    question = {
        frozenset({"date_text"}): "Bạn muốn tạo lịch vào ngày nào?",
        frozenset({"time_text"}): "Bạn muốn tạo lịch lúc mấy giờ?",
        frozenset({"title"}): "Bạn muốn đặt tiêu đề lịch là gì?",
        frozenset({"date_text", "time_text"}): "Bạn muốn tạo lịch vào ngày nào và lúc mấy giờ?",
        frozenset({"title", "time_text"}): "Bạn muốn tạo lịch gì và lúc mấy giờ?",
        frozenset({"title", "date_text"}): "Bạn muốn tạo lịch gì và vào ngày nào?",
    }.get(frozenset(missing), "Bạn muốn tạo lịch gì, vào ngày nào và lúc mấy giờ?")
    return ActionResult(question, "happy")


def plan_calendar(db, owner, conversation, text, now):
    row = db.execute("SELECT slots_json, expires_at FROM pending_actions WHERE client_id=? AND conversation_id=?", (owner, conversation)).fetchone()
    expired = row is not None and row["expires_at"] <= iso(now)
    old = json.loads(row["slots_json"]) if row is not None and not expired else None
    if old is not None and text.casefold() in CANCEL:
        return CalendarPlan(ActionResult("Được rồi, Anna đã hủy thao tác tạo lịch.", "neutral"), clear=True)
    # Only explicit calendar prefixes create state, never generic reminders/timers.
    trigger = _CALENDAR_TRIGGER_PATTERN.match(text)
    explicit = trigger is not None and "lịch" in trigger[0].casefold()
    if not explicit and old is None:
        return CalendarPlan(clear=expired)
    if not explicit and old is not None:
        replacement = recognize_action(text, now=now)
        if replacement is not None and replacement.action is not None:
            return CalendarPlan(replacement, clear=True)
    if explicit:
        complete = recognize_action(text, now=now)
        if complete is not None and complete.action is not None:
            return CalendarPlan(complete, clear=True)
        slots = calendar_slots(text[trigger.end():])
        if slots is None:
            return CalendarPlan(recognize_action(text, now=now), clear=expired)
    else:
        additions = calendar_slots(text)
        # A date/time-only answer or a recognizable short event title is compatible.
        title = (additions or {}).get("title", "")
        title_ok = (title.casefold() == old.get("title", "").casefold() or
                    ("title" not in old and len(title.split()) <= 12
                     and re.match(r"^(?:học|họp|ôn|làm|đi|thi|gặp)\b", title, re.I)))
        if additions is None or (title and not title_ok) or not additions:
            # Keep valid pending state untouched; never reinterpret arbitrary chat as a title.
            return CalendarPlan(clarification(old))
        if "date_text" in additions:
            _, error = resolve_date(additions["date_text"], now)
            if error:
                return CalendarPlan(ActionResult(error, "neutral"))
        slots = {**old, **additions}
    if "date_text" in slots:
        _, error = resolve_date(slots["date_text"], now)
        if error:
            return CalendarPlan(ActionResult(error, "neutral"), clear=expired)
    if KEYS <= slots.keys():
        result = recognize_action(f"Tạo lịch {slots['title']} {slots['date_text']} {slots['time_text']}", now=now)
        return CalendarPlan(result, None if result.action else slots, clear=bool(result.action))
    return CalendarPlan(clarification(slots), slots)


def apply_calendar(db, owner, conversation, plan, now):
    if plan.clear:
        db.execute("DELETE FROM pending_actions WHERE client_id=? AND conversation_id=?", (owner, conversation))
    if plan.slots is not None:
        slots = plan.slots
        assert set(slots) <= KEYS and all(isinstance(v, str) and len(v) <= 200 for v in slots.values())
        stamp = iso(now)
        db.execute("""INSERT INTO pending_actions
            (client_id,conversation_id,intent,slots_json,missing_slots_json,created_at,updated_at,expires_at)
            VALUES (?,?,'create_calendar_event',?,?,?,?,?)
            ON CONFLICT(client_id,conversation_id) DO UPDATE SET slots_json=excluded.slots_json,
            missing_slots_json=excluded.missing_slots_json,updated_at=excluded.updated_at,expires_at=excluded.expires_at""",
            (owner, conversation, json.dumps(slots, ensure_ascii=False), json.dumps(sorted(KEYS - slots.keys())),
             stamp, stamp, iso(now + timedelta(minutes=10))))
