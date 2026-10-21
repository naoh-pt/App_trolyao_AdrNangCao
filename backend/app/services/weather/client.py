"""Fixed-host Open-Meteo access with replaceable HTTP transport and bounded caches."""

import math
import time
from dataclasses import dataclass
from threading import Lock
from typing import Mapping

import httpx

from .intent import name_key

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
CURRENT = "temperature_2m,apparent_temperature,relative_humidity_2m,precipitation,weather_code,wind_speed_10m"
DAILY = "weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum,precipitation_probability_max"
COMMON_VN = {"ha noi", "hanoi", "bac ninh", "da nang", "ho chi minh", "hai phong", "hue", "can tho"}


def location_key(text):
    key = name_key(text)
    return "ha noi" if key == "hanoi" else key


class WeatherDataError(ValueError):
    """Unusable or incomplete provider data (message is never exposed to users)."""


class PlaceNotFound(WeatherDataError):
    pass


@dataclass(frozen=True)
class WeatherConfig:
    enabled: bool = True
    connect_ms: int = 3000
    read_ms: int = 6000
    cache_seconds: int = 600
    geocoding_seconds: int = 86400


def read_weather_config(environ: Mapping[str, str]) -> WeatherConfig:
    def bounded(key, default, maximum):
        try:
            value = int(environ.get(key, str(default)))
            return value if 1 <= value <= maximum else default
        except (ValueError, TypeError):
            return default
    return WeatherConfig(
        enabled=environ.get("WEATHER_ENABLED", "true").strip().lower() not in {"false", "0", "off", "no"},
        connect_ms=bounded("WEATHER_CONNECT_TIMEOUT_MS", 3000, 3000),
        read_ms=bounded("WEATHER_READ_TIMEOUT_MS", 6000, 6000),
        cache_seconds=bounded("WEATHER_CACHE_TTL_SECONDS", 600, 3600),
        geocoding_seconds=bounded("WEATHER_GEOCODING_CACHE_TTL_SECONDS", 86400, 86400),
    )


def number(value, low=-1e6, high=1e6) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not low <= value <= high:
        raise WeatherDataError("invalid number")
    return value


@dataclass(frozen=True)
class Place:
    name: str
    country: str
    latitude: float
    longitude: float

    @property
    def label(self):
        return f"{self.name}, {self.country}"


class WeatherClient:
    def __init__(self, config=WeatherConfig(), *, transport=None, clock=time.monotonic):
        self.config = config
        self.transport = transport
        self.clock = clock
        self._geo = {}
        self._weather = {}
        self._lock = Lock()

    def _cached(self, cache, key, ttl, load):
        with self._lock:
            entry = cache.get(key)
            if entry and self.clock() < entry[0]:
                return entry[1]
        value = load()
        with self._lock:
            if len(cache) >= 256:
                cache.clear()
            cache[key] = (self.clock() + ttl, value)
        return value

    def _get(self, url, params):
        timeout = httpx.Timeout(self.config.read_ms / 1000, connect=self.config.connect_ms / 1000)
        # No retries, redirects, arbitrary environment endpoints or provider credentials.
        with httpx.Client(transport=self.transport, timeout=timeout, follow_redirects=False, trust_env=False) as client:
            response = client.get(url, params=params)
            response.raise_for_status()
            result = response.json()
        if not isinstance(result, dict):
            raise WeatherDataError("invalid object")
        return result

    def geocode(self, query: str) -> Place:
        def load():
            data = self._get(GEOCODING_URL, {"name": query, "count": 5, "language": "vi", "format": "json"})
            results = data.get("results", [])
            if not isinstance(results, list):
                raise WeatherDataError("invalid results")
            target, _, qualifier = name_key(query).partition(",")
            target, qualifier = target.strip(), qualifier.strip()
            target = location_key(target)
            candidates = []
            for item in results:
                if not isinstance(item, dict) or not isinstance(item.get("name"), str):
                    continue
                name = location_key(item["name"])
                if name != target and not name.startswith(target + " "):
                    continue
                country, code = item.get("country"), item.get("country_code")
                if not isinstance(country, str) or not country.strip() or not isinstance(code, str):
                    continue
                if qualifier and qualifier not in {name_key(country), name_key(code), name_key(str(item.get("admin1", "")))}:
                    continue
                try:
                    display_name = "Hà Nội" if name == "ha noi" and code == "VN" else item["name"]
                    place = Place(display_name, "Việt Nam" if code == "VN" else country,
                                  number(item.get("latitude"), -90, 90), number(item.get("longitude"), -180, 180))
                except WeatherDataError:
                    continue
                candidates.append(((name == target, code == "VN" and target in COMMON_VN), place))
            if not candidates:
                raise PlaceNotFound("no credible result")
            return max(candidates, key=lambda item: item[0])[1]
        return self._cached(self._geo, name_key(query), self.config.geocoding_seconds, load)

    def forecast(self, place: Place, local_date_key: str) -> dict:
        def load():
            data = self._get(FORECAST_URL, {
                "latitude": place.latitude, "longitude": place.longitude,
                "current": CURRENT, "daily": DAILY, "timezone": "auto", "forecast_days": 3,
                "temperature_unit": "celsius", "wind_speed_unit": "kmh", "precipitation_unit": "mm",
            })
            # Never cache obviously malformed payloads; formatter validates individual fields.
            if not isinstance(data.get("current"), dict) or not isinstance(data.get("daily"), dict):
                raise WeatherDataError("missing forecast")
            return data
        return self._cached(self._weather, (place.latitude, place.longitude, local_date_key), self.config.cache_seconds, load)
