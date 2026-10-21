"""Conservative, anchored Vietnamese live-weather grammar."""

import re
import unicodedata
from dataclasses import dataclass


def normalize(text: str) -> str:
    return " ".join(unicodedata.normalize("NFC", text).casefold().split()).strip(" .,?!;:")


def name_key(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", normalize(text).replace("đ", "d"))
                   if not unicodedata.combining(c))


@dataclass(frozen=True)
class WeatherIntent:
    location: str | None
    day: int = 0
    kind: str = "current"


DAY = r"hôm nay|ngày mai|ngày kia"
META = r"\b(là gì|giải thích|xây dựng|ứng dụng|so sánh|khí hậu|api|viết|dịch)\b"


def parse_weather_intent(text: str) -> WeatherIntent | None:
    text = normalize(text)
    if re.search(META, text):
        return None
    body = None
    kind = "daily"
    match = re.fullmatch(rf"(?:(?P<day>{DAY}) )?(?:mình |tôi )?có nên mang áo mưa(?: ở (?P<place>.*?))? không", text)
    if match:
        body = " ".join(filter(None, [match["place"], match["day"]]))
        kind = "rain"
    if body is None:
        match = re.fullmatch(rf"(?P<day>{DAY}) (?:ở )?(?P<place>.*?) ?có mưa không", text)
        if match:
            body = f'{match["place"]} {match["day"]}'
            kind = "rain"
    if body is None:
        match = re.fullmatch(r"nhiệt độ(?: ở)? (.*?) (?:là )?bao nhiêu", text)
        if match:
            body = match[1]
    if body is None:
        match = re.fullmatch(rf"(?:(?P<day>{DAY}) )?thời tiết(?: (?P<body>.*))?", text)
        if match:
            body = re.sub(r"(?:^| )(?:thế nào|ra sao)$", "", match["body"] or "")
            body = " ".join(filter(None, [body, match["day"]]))
            kind = "current" if not re.search(DAY, body) else "daily"
    if body is None:
        return None
    days = re.findall(DAY, body)
    if len(days) > 1:
        return WeatherIntent(None)
    day = {"ngày mai": 1, "ngày kia": 2}.get(days[0] if days else "", 0)
    place = re.sub(rf"\b(?:{DAY}|hiện tại)\b", "", body)
    place = re.sub(r"^ở\s+", "", normalize(place))
    # User text is a geocoding name, never an endpoint, URI, package or raw intent.
    if not place or len(place) > 100 or not re.fullmatch(r"[\w .,'’()\-]+", place):
        place = None
    return WeatherIntent(place, day, kind)
