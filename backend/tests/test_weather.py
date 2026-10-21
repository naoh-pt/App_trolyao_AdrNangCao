"""All weather tests use MockTransport; any real HTTP transport is forbidden."""

import copy
import uuid
from datetime import datetime, timezone

import httpx
import pytest

import ai_service
import app.api.v1.conversations as routes
import app.services.rag_service as rag
from app.db.connection import get_connection
from app.services.providers.gemini_provider import GeminiProvider
from app.services.providers.groq_provider import GroqProvider
from app.services.providers.provider_service import ProviderService
from app.services.weather.client import (
    CURRENT, DAILY, FORECAST_URL, GEOCODING_URL, Place, WeatherClient, WeatherConfig,
    read_weather_config,
)
from app.services.weather.formatter import ATTRIBUTION, WMO, format_weather, weather_description, weather_emotion
from app.services.weather.intent import WeatherIntent, parse_weather_intent
from app.services.weather.service import FAILURE, MISSING_LOCATION, NO_PLACE, WeatherService

NOW = datetime(2026, 10, 21, 4, tzinfo=timezone.utc)
PLACE = Place("Hà Nội", "Việt Nam", 21.02, 105.83)
GEO = {"results": [{"name": "Hà Nội", "country": "Vietnam", "country_code": "VN", "latitude": 21.02, "longitude": 105.83}]}
DATA = {
    "timezone": "Asia/Ho_Chi_Minh", "utc_offset_seconds": 25200,
    "current": {"time": "2026-10-21T11:00", "temperature_2m": 27, "apparent_temperature": 29,
                "relative_humidity_2m": 78, "precipitation": 0, "weather_code": 3, "wind_speed_10m": 9},
    "current_units": {"temperature_2m": "°C", "apparent_temperature": "°C", "relative_humidity_2m": "%", "wind_speed_10m": "km/h"},
    "daily": {"time": ["2026-10-21", "2026-10-22", "2026-10-23"], "weather_code": [0, 63, 95],
              "temperature_2m_max": [30, 31, 28], "temperature_2m_min": [23, 24, 22],
              "precipitation_sum": [0, 4, 10], "precipitation_probability_max": [5, 70, 90]},
    "daily_units": {"temperature_2m_max": "°C", "temperature_2m_min": "°C", "precipitation_sum": "mm", "precipitation_probability_max": "%"},
}


@pytest.fixture(autouse=True)
def forbid_real_http(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Weather tests must not perform real HTTP")
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", forbidden)


def make_service(*, geo=None, forecast=None, error=None, clock=None, config=WeatherConfig()):
    calls = []
    def handler(request):
        calls.append(request)
        assert str(request.url).startswith((GEOCODING_URL + "?", FORECAST_URL + "?"))
        if error:
            if isinstance(error, int):
                return httpx.Response(error)
            raise error
        data = (GEO if geo is None else geo) if request.url.host.startswith("geocoding") else (DATA if forecast is None else forecast)
        return httpx.Response(200, json=data)
    kwargs = {"clock": clock} if clock else {}
    client = WeatherClient(config, transport=httpx.MockTransport(handler), **kwargs)
    return WeatherService(client, now=lambda: NOW), calls


@pytest.mark.parametrize("text,place,day,kind", [
    ("Thời tiết Hà Nội hiện tại thế nào?", "hà nội", 0, "current"),
    ("Thời tiết Hà Nội hôm nay thế nào?", "hà nội", 0, "daily"),
    ("Ngày mai Hà Nội có mưa không?", "hà nội", 1, "rain"),
    ("Nhiệt độ ở Bắc Ninh hôm nay bao nhiêu?", "bắc ninh", 0, "daily"),
    ("Hôm nay mình có nên mang áo mưa ở Hà Nội không?", "hà nội", 0, "rain"),
    ("  THỜI TIẾT   HÀ NỘI HIỆN TẠI THẾ NÀO?!  ", "hà nội", 0, "current"),
    ("Thời tiết Hà Nội ngày kia thế nào.", "hà nội", 2, "daily"),
    ("Ngày mai thời tiết Hà Nội thế nào?", "hà nội", 1, "daily"),
])
def test_intent(text, place, day, kind):
    assert parse_weather_intent(text) == WeatherIntent(place, day, kind)


@pytest.mark.parametrize("text", ["Thời tiết là gì?", "Giải thích API thời tiết", "Làm sao xây dựng ứng dụng dự báo thời tiết?", "So sánh thời tiết và khí hậu", "Xin chào Anna", "Viết câu có từ thời tiết", "Tìm bản đồ Hà Nội"])
def test_non_weather(text):
    assert parse_weather_intent(text) is None


@pytest.mark.parametrize("text", ["Thời tiết hôm nay thế nào?", "Thời tiết hiện tại thế nào?", "Ngày mai có mưa không?", "Hôm nay mình có nên mang áo mưa không?", "Thời tiết https://bad.test hiện tại thế nào?"])
def test_missing_or_unsafe_location_no_http(text):
    service, calls = make_service()
    assert service.reply(text) == (MISSING_LOCATION, "neutral")
    assert calls == []


def test_current_and_request_fields():
    service, calls = make_service()
    reply, emotion = service.reply("Thời tiết Hà Nội hiện tại thế nào?")
    assert all(part in reply for part in ["Hà Nội, Việt Nam", "27°C", "29°C", "78%", "9 km/h", ATTRIBUTION])
    assert emotion == "neutral"
    assert len(calls) == 2
    assert dict(calls[0].url.params) == {"name": "hà nội", "count": "5", "language": "vi", "format": "json"}
    params = calls[1].url.params
    assert params["current"] == CURRENT and params["daily"] == DAILY
    assert params["timezone"] == "auto" and params["forecast_days"] == "3"
    assert calls[0].extensions["timeout"]["connect"] == 3
    assert calls[0].extensions["timeout"]["read"] == 6


@pytest.mark.parametrize("query,fragments,emotion", [
    ("Thời tiết Hà Nội hôm nay thế nào?", ["23°C", "30°C", "5%"], "happy"),
    ("Ngày mai Hà Nội có mưa không?", ["24°C", "31°C", "70%", "cân nhắc mang áo mưa"], "neutral"),
    ("Hôm nay mình có nên mang áo mưa ở Hà Nội không?", ["khá thấp", "theo dõi dự báo"], "happy"),
    ("Thời tiết Hà Nội ngày kia thế nào?", ["22°C", "28°C", "dông"], "surprised"),
])
def test_daily_forecasts(query, fragments, emotion):
    service, _ = make_service()
    text, actual = service.reply(query)
    assert all(fragment in text for fragment in fragments)
    assert ATTRIBUTION in text
    assert actual == emotion


@pytest.mark.parametrize("probability,amount,code", [(50, 0, 0), (0, 1, 0), (0, 0, 61)])
def test_rain_recommendation_uses_each_signal(probability, amount, code):
    data = copy.deepcopy(DATA)
    data["daily"]["precipitation_probability_max"][0] = probability
    data["daily"]["precipitation_sum"][0] = amount
    data["daily"]["weather_code"][0] = code
    service, _ = make_service(forecast=data)
    assert "cân nhắc mang áo mưa" in service.reply("Hôm nay mình có nên mang áo mưa ở Hà Nội không?")[0]


@pytest.mark.parametrize("code", list(WMO) + [999])
def test_wmo_mapping_and_allowed_emotions(code):
    assert weather_description(code)
    assert weather_emotion(code) in {"neutral", "happy", "surprised"}
    if code == 999:
        assert "chưa xác định" in weather_description(code)
    if code in {61, 63, 65}:
        assert weather_emotion(code) == "neutral"


def test_unknown_code_formats_without_ai():
    data = copy.deepcopy(DATA)
    data["current"]["weather_code"] = 999
    service, _ = make_service(forecast=data)
    text, emotion = service.reply("Thời tiết Hà Nội hiện tại thế nào?")
    assert "chưa xác định" in text and ATTRIBUTION in text and emotion == "neutral"


def test_vietnam_preference_and_english_alias():
    data = {"results": [dict(GEO["results"][0], country="Other", country_code="US"), dict(GEO["results"][0], name="Hanoi")]}
    service, _ = make_service(geo=data)
    assert service.client.geocode("Hà Nội").label == "Hà Nội, Việt Nam"


def test_foreign_country_qualifier_is_respected():
    data = {"results": [dict(GEO["results"][0], name="Paris"), dict(GEO["results"][0], name="Paris", country="France", country_code="FR")]}
    service, _ = make_service(geo=data)
    assert service.client.geocode("Paris, France").country == "France"


@pytest.mark.parametrize("geo", [{}, {"results": []}, {"results": [{}]}, {"results": [dict(GEO["results"][0], latitude=999)]}, {"results": [dict(GEO["results"][0], name="Unrelated")]}, {"results": [dict(GEO["results"][0], country=None)]}])
def test_no_credible_place(geo):
    service, calls = make_service(geo=geo)
    assert service.reply("Thời tiết Hà Nội hiện tại thế nào?") == (NO_PLACE, "neutral")
    assert len(calls) == 1


@pytest.mark.parametrize("data", [{"results": "bad"}, [], None])
def test_malformed_geocoding(data):
    def handler(request):
        return httpx.Response(200, json=data)
    service = WeatherService(WeatherClient(transport=httpx.MockTransport(handler)), now=lambda: NOW)
    assert service.reply("Thời tiết Hà Nội hiện tại thế nào?") == (FAILURE, "neutral")


@pytest.mark.parametrize("error", [400, 500, httpx.ConnectTimeout("private detail"), httpx.ReadTimeout("private detail"), httpx.ConnectError("private detail")])
def test_network_failure_safe_no_retry(error, caplog):
    service, calls = make_service(error=error)
    assert service.reply("Thời tiết Hà Nội hiện tại thế nào?", request_id="test-id") == (FAILURE, "neutral")
    assert len(calls) == 1
    assert "private detail" not in caplog.text and "Hà Nội" not in caplog.text


def test_forecast_network_failure():
    calls = []
    def handler(request):
        calls.append(request)
        if len(calls) == 1:
            return httpx.Response(200, json=GEO)
        raise httpx.ReadTimeout("do not expose")
    service = WeatherService(WeatherClient(transport=httpx.MockTransport(handler)), now=lambda: NOW)
    assert service.reply("Thời tiết Hà Nội hiện tại thế nào?") == (FAILURE, "neutral")
    assert len(calls) == 2


@pytest.mark.parametrize("section,key,value", [
    ("daily", "time", []), ("daily", "temperature_2m_min", []),
    ("daily", "precipitation_probability_max", [None, None, None]),
    ("current", "temperature_2m", None), ("current", "temperature_2m", float("nan")),
    ("current", "time", "bad"), ("current", "time", "2020-01-01T00:00"),
    ("daily_units", "temperature_2m_min", "°F"), ("current_units", "wind_speed_10m", "mph"),
])
def test_missing_invalid_fields_fail_safely(section, key, value):
    data = copy.deepcopy(DATA)
    data[section][key] = value
    # NaN is invalid JSON too; directly injected data still must be rejected.
    service, _ = make_service()
    service.client.forecast = lambda *args: data
    text = "Thời tiết Hà Nội hôm nay thế nào?" if section.startswith("daily") else "Thời tiết Hà Nội hiện tại thế nào?"
    result = service.reply(text)
    assert result[1] == "neutral"
    assert ATTRIBUTION not in result[0]


@pytest.mark.parametrize("data", [{}, [], {"current": {}, "daily": {}}])
def test_malformed_forecast(data):
    service, _ = make_service(forecast=data)
    assert service.reply("Thời tiết Hà Nội hiện tại thế nào?") == (FAILURE, "neutral")


def test_invalid_json():
    service = WeatherService(WeatherClient(transport=httpx.MockTransport(lambda request: httpx.Response(200, content=b"not-json"))))
    assert service.reply("Thời tiết Hà Nội hiện tại thế nào?") == (FAILURE, "neutral")


def test_cache_hit_and_expiry():
    ticks = [0]
    service, calls = make_service(clock=lambda: ticks[0])
    query = "Thời tiết Hà Nội hiện tại thế nào?"
    service.reply(query)
    service.reply("  THỜI TIẾT HÀ NỘI HIỆN TẠI THẾ NÀO?!")
    assert len(calls) == 2
    ticks[0] = 601
    service.reply(query)
    assert len(calls) == 3  # forecast expired, geocoding retained
    ticks[0] = 86401
    service.reply(query)
    assert len(calls) == 5


def test_provider_local_date_not_computer_or_utc_date():
    data = copy.deepcopy(DATA)
    now = datetime(2026, 10, 20, 18, tzinfo=timezone.utc)  # Already Oct 21 in Vietnam.
    text, _ = format_weather(WeatherIntent("hà nội", 1, "daily"), PLACE, data, now)
    assert "24°C" in text and "31°C" in text


def test_foreign_timezone_used():
    data = copy.deepcopy(DATA)
    data.update(timezone="America/Los_Angeles", utc_offset_seconds=-25200)
    data["daily"]["time"] = ["2026-10-20", "2026-10-21", "2026-10-22"]
    text, _ = format_weather(WeatherIntent("place", 0, "daily"), PLACE, data, NOW)
    assert "23°C" in text and "30°C" in text


@pytest.mark.parametrize("key", ["WEATHER_CONNECT_TIMEOUT_MS", "WEATHER_READ_TIMEOUT_MS", "WEATHER_CACHE_TTL_SECONDS", "WEATHER_GEOCODING_CACHE_TTL_SECONDS"])
@pytest.mark.parametrize("value", ["bad", "0", "-1", "999999999"])
def test_invalid_config_defaults(key, value):
    assert read_weather_config({key: value}) == WeatherConfig()


def test_disabled_weather_no_network():
    service, calls = make_service(config=read_weather_config({"WEATHER_ENABLED": "false"}))
    assert "tạm tắt" in service.reply("Thời tiết Hà Nội hiện tại thế nào?")[0]
    assert calls == []


@pytest.mark.parametrize("question", [
    "Thời tiết Hà Nội hiện tại thế nào?", "Thời tiết Hà Nội hôm nay thế nào?", "Ngày mai Hà Nội có mưa không?",
    "Nhiệt độ ở Bắc Ninh hôm nay bao nhiêu?", "Hôm nay mình có nên mang áo mưa ở Hà Nội không?", "Thời tiết hôm nay thế nào?",
])
def test_route_schema_persistence_replay_bypass(client, temp_db_file, monkeypatch, question):
    def forbidden(*args, **kwargs):
        pytest.fail("Weather reached history/RAG/embedding/provider")
    monkeypatch.setattr(routes, "USE_REAL_AI", True)
    monkeypatch.setattr(routes, "RAG_ENABLED", True)
    for obj, attr in [(routes, "retrieve"), (routes, "prompt_context"), (rag, "_embed"),
                      (ai_service, "generate_reply"), (ai_service, "get_provider_service"),
                      (routes.mock_ai, "generate_reply"), (ProviderService, "generate_reply"),
                      (GeminiProvider, "generate_reply"), (GroqProvider, "generate_reply")]:
        monkeypatch.setattr(obj, attr, forbidden)
    geo = GEO if "Bắc Ninh" not in question else {"results": [dict(GEO["results"][0], name="Bắc Ninh")]}
    service, calls = make_service(geo=geo)
    invocations = []
    def reply(text, **kwargs):
        assert any("INSERT INTO messages" in sql and "'user'" in sql for sql in statements)
        assert not any("INSERT INTO messages" in sql and "'assistant'" in sql for sql in statements)
        invocations.append(text)
        return service.reply(text, **kwargs)
    monkeypatch.setattr(routes, "get_weather_reply", reply)
    statements = []
    from app.main import app
    def traced_db():
        with get_connection(temp_db_file) as db:
            db.set_trace_callback(statements.append)
            yield db
    monkeypatch.setitem(app.dependency_overrides, routes.get_db, traced_db)
    headers = {"X-Client-Id": str(uuid.uuid4())}
    conv = client.post("/api/v1/conversations", headers=headers).json()["id"]
    payload = {"request_id": str(uuid.uuid4()), "message": question}
    url = f"/api/v1/conversations/{conv}/messages"
    first = client.post(url, headers=headers, json=payload)
    assert first.status_code == 200
    body = first.json()
    assert set(body) == {"user_message", "assistant_message", "sources"}
    assert body["sources"] == []
    assert set(body["assistant_message"]) == {"id", "role", "text", "emotion", "created_at"}
    assert body["assistant_message"]["emotion"] in {"neutral", "happy", "sad", "surprised"}
    if "Hà Nội" in question or "Bắc Ninh" in question:
        assert ATTRIBUTION in body["assistant_message"]["text"]
    else:
        assert body["assistant_message"]["text"] == MISSING_LOCATION
    before = len(calls)
    replay = client.post(url, headers=headers, json=payload)
    assert replay.status_code == 200 and replay.json() == body
    assert len(calls) == before and len(invocations) == 1
    assert not any("LIMIT 10" in sql for sql in statements)
    with get_connection(temp_db_file) as db:
        assert db.execute("SELECT count(*) FROM messages WHERE conversation_id = ?", (conv,)).fetchone()[0] == 2
        assert db.execute("SELECT count(*) FROM idempotency_records WHERE request_id = ?", (payload["request_id"],)).fetchone()[0] == 1


def test_route_weather_failure_still_persisted_and_replayed(client, monkeypatch):
    service, calls = make_service(error=500)
    monkeypatch.setattr(routes, "get_weather_reply", service.reply)
    monkeypatch.setattr(ai_service, "generate_reply", lambda *args: pytest.fail("No AI on weather failure"))
    headers = {"X-Client-Id": str(uuid.uuid4())}
    conv = client.post("/api/v1/conversations", headers=headers).json()["id"]
    payload = {"request_id": str(uuid.uuid4()), "message": "Thời tiết Hà Nội hiện tại thế nào?"}
    url = f"/api/v1/conversations/{conv}/messages"
    first = client.post(url, headers=headers, json=payload)
    assert first.status_code == 200 and first.json()["assistant_message"]["text"] == FAILURE
    assert client.post(url, headers=headers, json=payload).json() == first.json()
    assert len(calls) == 1


def test_ownership_and_request_validation_before_weather(client, monkeypatch):
    monkeypatch.setattr(routes, "get_weather_reply", lambda *args, **kwargs: pytest.fail("Weather before validation"))
    owner = {"X-Client-Id": str(uuid.uuid4())}
    stranger = {"X-Client-Id": str(uuid.uuid4())}
    conv = client.post("/api/v1/conversations", headers=owner).json()["id"]
    url = f"/api/v1/conversations/{conv}/messages"
    payload = {"request_id": str(uuid.uuid4()), "message": "Thời tiết Hà Nội hiện tại thế nào?"}
    assert client.post(url, headers=stranger, json=payload).status_code == 404
    assert client.post(url, headers=owner, json=dict(payload, request_id="bad")).status_code == 400


def test_non_weather_keeps_mock_flow_and_quick_replies(client, monkeypatch):
    service, calls = make_service()
    monkeypatch.setattr(routes, "get_weather_reply", service.reply)
    mock_calls = []
    monkeypatch.setattr(routes.mock_ai, "generate_reply", lambda *args: (mock_calls.append(args) or ("Trả lời bình thường", "neutral")))
    headers = {"X-Client-Id": str(uuid.uuid4())}
    conv = client.post("/api/v1/conversations", headers=headers).json()["id"]
    for text in ["Giải thích API thời tiết", "Mấy giờ rồi?", "Tìm trên bản đồ Hồ Gươm.", "Nhắc tôi học bài sau 5 phút"]:
        response = client.post(f"/api/v1/conversations/{conv}/messages", headers=headers, json={"request_id": str(uuid.uuid4()), "message": text})
        assert response.status_code == 200
    assert len(mock_calls) == 1 and calls == []
