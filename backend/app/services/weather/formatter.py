"""Validated provider data -> Vietnamese text, without generative formatting."""

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .client import Place, WeatherDataError, number
from .intent import WeatherIntent

ATTRIBUTION = "Nguồn dữ liệu: Open-Meteo."
WMO = {
    0: "trời quang", 1: "trời khá quang", 2: "trời có mây rải rác", 3: "trời nhiều mây",
    45: "có sương mù", 48: "có sương mù đóng băng",
    51: "có mưa phùn nhẹ", 53: "có mưa phùn", 55: "có mưa phùn dày",
    56: "có mưa phùn đóng băng", 57: "có mưa phùn đóng băng",
    61: "có mưa nhẹ", 63: "có mưa", 65: "có mưa lớn",
    66: "có mưa đóng băng", 67: "có mưa đóng băng",
    71: "có tuyết nhẹ", 73: "có tuyết", 75: "có tuyết dày", 77: "có hạt tuyết",
    80: "có mưa rào nhẹ", 81: "có mưa rào", 82: "có mưa rào lớn",
    85: "có tuyết rào", 86: "có tuyết rào lớn", 95: "có dông",
    96: "có dông kèm mưa đá", 99: "có dông kèm mưa đá mạnh",
}
WET_CODES = {51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82, 95, 96, 99}


class DayUnavailable(WeatherDataError):
    pass


def weather_description(code):
    return WMO.get(code, "điều kiện thời tiết chưa xác định")


def weather_emotion(code):
    return "happy" if code in {0, 1} else "surprised" if code in {95, 96, 99} else "neutral"


def provider_timezone(data):
    name = data.get("timezone")
    if not isinstance(name, str) or not name:
        raise WeatherDataError("missing timezone")
    try:
        return ZoneInfo(name)
    except ZoneInfoNotFoundError:
        # Windows installations without IANA data still have the provider's offset.
        offset = number(data.get("utc_offset_seconds"), -50400, 50400)
        return timezone(timedelta(seconds=offset))


def _value(section, units, key, unit, low=-1e6, high=1e6):
    if units.get(key) != unit:
        raise WeatherDataError("unexpected units")
    return number(section.get(key), low, high)


def format_weather(intent: WeatherIntent, place: Place, data: dict, now: datetime) -> tuple[str, str]:
    if now.tzinfo is None:
        raise WeatherDataError("clock must be aware")
    local_now = now.astimezone(provider_timezone(data))
    current = data.get("current")
    daily = data.get("daily")
    cu, du = data.get("current_units"), data.get("daily_units")
    if not all(isinstance(item, dict) for item in (current, daily, cu, du)):
        raise WeatherDataError("missing forecast fields")
    if intent.kind == "current":
        timestamp = datetime.fromisoformat(current.get("time", ""))
        # Open-Meteo supplies local timestamps with timezone=auto, not UTC strings.
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=local_now.tzinfo)
        if abs((local_now - timestamp).total_seconds()) > 7200:
            raise WeatherDataError("stale current observation")
        temp = _value(current, cu, "temperature_2m", "°C", -100, 70)
        feels = _value(current, cu, "apparent_temperature", "°C", -120, 90)
        humidity = _value(current, cu, "relative_humidity_2m", "%", 0, 100)
        wind = _value(current, cu, "wind_speed_10m", "km/h", 0, 500)
        number(current.get("precipitation"), 0, 10000)
        code = number(current.get("weather_code"), 0, 1000)
        text = (f"Hiện tại ở {place.label}, {weather_description(code)}, khoảng {temp:g}°C, "
                f"cảm giác như {feels:g}°C. Độ ẩm {humidity:g}% và gió khoảng {wind:g} km/h.")
    else:
        target = (local_now.date() + timedelta(days=intent.day)).isoformat()
        dates = daily.get("time")
        if not isinstance(dates, list) or target not in dates:
            raise DayUnavailable("requested date unavailable")
        index = dates.index(target)

        def at(key):
            values = daily.get(key)
            if not isinstance(values, list) or len(values) <= index:
                raise WeatherDataError("missing daily value")
            return values[index]

        values = {key: at(key) for key in ("temperature_2m_min", "temperature_2m_max", "precipitation_sum", "precipitation_probability_max", "weather_code")}
        low = _value(values, du, "temperature_2m_min", "°C", -100, 70)
        high = _value(values, du, "temperature_2m_max", "°C", low, 70)
        amount = _value(values, du, "precipitation_sum", "mm", 0, 10000)
        probability = _value(values, du, "precipitation_probability_max", "%", 0, 100)
        code = number(values["weather_code"], 0, 1000)
        when = ("Hôm nay", "Ngày mai", "Ngày kia")[intent.day]
        text = (f"{when} ở {place.label}, dự kiến {weather_description(code)}, nhiệt độ từ {low:g}°C đến {high:g}°C. "
                f"Xác suất có mưa cao nhất khoảng {probability:g}%, lượng giáng thủy dự kiến {amount:g} mm.")
        if intent.kind == "rain":
            text += (" Bạn nên cân nhắc mang áo mưa nhé." if probability >= 40 or amount >= .5 or code in WET_CODES
                     else " Khả năng mưa hiện khá thấp, nhưng bạn vẫn nên theo dõi dự báo trước khi ra ngoài.")
    return f"{text} {ATTRIBUTION}", weather_emotion(code)
