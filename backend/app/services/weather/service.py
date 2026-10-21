"""One deterministic path for successes, clarifications and weather failures."""

import logging
import os
from datetime import datetime, timezone
from functools import lru_cache

import httpx

from app.services.personality import normalize_emotion
from .client import PlaceNotFound, WeatherClient, WeatherDataError, read_weather_config
from .formatter import DayUnavailable, format_weather
from .intent import parse_weather_intent

MISSING_LOCATION = 'Bạn muốn xem thời tiết ở đâu? Ví dụ: “Thời tiết Hà Nội ngày mai thế nào?”'
FAILURE = "Anna chưa lấy được dữ liệu thời tiết lúc này. Bạn thử lại sau một chút nhé."
NO_PLACE = "Anna chưa tìm được địa điểm phù hợp. Bạn cho mình tên tỉnh, thành phố hoặc quốc gia cụ thể hơn nhé."


class WeatherService:
    def __init__(self, client: WeatherClient, *, now=lambda: datetime.now(timezone.utc)):
        self.client = client
        self.now = now

    def reply(self, text: str, *, request_id: str = "") -> tuple[str, str] | None:
        intent = parse_weather_intent(text)
        if intent is None:
            return None
        if not intent.location:
            return MISSING_LOCATION, "neutral"
        if not self.client.config.enabled:
            return "Tính năng thời tiết đang tạm tắt. Bạn thử lại sau nhé.", "neutral"
        try:
            place = self.client.geocode(intent.location)
            now = self.now()
            data = self.client.forecast(place, now.astimezone(timezone.utc).date().isoformat())
            reply, emotion = format_weather(intent, place, data, now)
            return reply, normalize_emotion(emotion)
        except PlaceNotFound:
            return NO_PLACE, "neutral"
        except DayUnavailable:
            return "Anna chưa có dự báo cho ngày bạn chọn. Bạn thử lại sau nhé.", "neutral"
        except (httpx.HTTPError, WeatherDataError, ValueError, TypeError, KeyError, OverflowError) as exc:
            logging.warning("Weather failure type=%s request_id=%s", type(exc).__name__, request_id)
            return FAILURE, "neutral"


@lru_cache(maxsize=1)
def get_weather_service() -> WeatherService:
    # app.config has already loaded the existing application environment before route imports.
    return WeatherService(WeatherClient(read_weather_config(os.environ)))


def get_weather_reply(text: str, *, request_id: str = "") -> tuple[str, str] | None:
    return get_weather_service().reply(text, request_id=request_id)
