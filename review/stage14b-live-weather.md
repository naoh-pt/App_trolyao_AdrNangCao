# Stage 14B — Deterministic live weather

Verdict: **READY FOR DEVICE TEST**

- Repository: `D:\nam5\semester_1\advance_android\01_trolyAI\troLyAo_ani_integration`
- Branch: `feature/stage14-demo-weather`
- Device-tested Stage 14A baseline: `ff99247f928e954bc8e1fe41c4b18001855c58d7` (local and remote feature HEAD matched before edits; tree/index were clean).
- Checkpoint: `backup/stage14a-demo-picker-20261021`, created and pushed at exactly `ff99247f928e954bc8e1fe41c4b18001855c58d7`.
- Main remains `b765d9945e6ca2961792350db44cd9cc58a96ac1`; no merge or main push.

## Exact files

Modified:

1. `.env.example`
2. `backend/.env.example`
3. `backend/README.md`
4. `backend/app/api/v1/conversations.py`
5. `android/app/src/main/java/com/example/assistant/ui/demo/DemoQuestionCatalog.kt`
6. `android/app/src/test/java/com/example/assistant/ui/demo/DemoCatalogTest.kt`
7. `android/app/src/test/java/com/example/assistant/ui/demo/DemoScenarioControllerTest.kt`

Added:

8. `backend/app/services/weather/__init__.py`
9. `backend/app/services/weather/intent.py`
10. `backend/app/services/weather/client.py`
11. `backend/app/services/weather/formatter.py`
12. `backend/app/services/weather/service.py`
13. `backend/tests/test_weather.py`
14. `review/stage14b-live-weather.md`

## Intent and location handling

Anchored Vietnamese patterns recognize weather, temperature, rain and raincoat questions. Input is NFC-normalized, case-folded, whitespace-collapsed and stripped of terminal conversational punctuation. The five supported samples are:

- `Thời tiết Hà Nội hiện tại thế nào?`
- `Thời tiết Hà Nội hôm nay thế nào?`
- `Ngày mai Hà Nội có mưa không?`
- `Nhiệt độ ở Bắc Ninh hôm nay bao nhiêu?`
- `Hôm nay mình có nên mang áo mưa ở Hà Nội không?`

Supported time expressions: `hiện tại` (current conditions), `hôm nay`, `ngày mai`, `ngày kia` (daily forecast). This is not a general date parser. Educational/meta patterns and unrelated chat are not intercepted, including all four required educational examples. Missing or unusable location returns the persisted local clarification:

> Bạn muốn xem thời tiết ở đâu? Ví dụ: “Thời tiết Hà Nội ngày mai thế nào?”

No network call occurs for that clarification. The tool never uses GPS, IP location or a default city. Places are limited to names, not URLs/schemes/packages. HTTP hosts are constants; no endpoint environment override exists. Geocoding requests `name`, `count=5`, `language=vi`, `format=json`. Results require credible normalized exact/boundary-prefix name matches, country and finite valid coordinates. Common Vietnamese names prefer VN among equally close matches; Hanoi/Ha Noi aliases are recognized. Explicit comma-separated country/admin qualifiers are respected; foreign places are not forced to Vietnam. No credible match produces a friendly request for a more specific place. Labels include resolved name/country, with Việt Nam localized.

## HTTP, forecast, formatting, and caches

Uses the existing HTTPX dependency with injectable MockTransport, fixed HTTPS hosts, no retries, redirects, arbitrary user URLs, provider credentials, or proxy-environment routing. Production endpoints:

- `https://geocoding-api.open-meteo.com/v1/search`
- `https://api.open-meteo.com/v1/forecast`

Forecast fields:

- Current: `temperature_2m`, `apparent_temperature`, `relative_humidity_2m`, `precipitation`, `weather_code`, `wind_speed_10m`.
- Daily: `weather_code`, `temperature_2m_max`, `temperature_2m_min`, `precipitation_sum`, `precipitation_probability_max`.
- `timezone=auto`, `forecast_days=3`, Celsius, km/h, mm explicitly requested. Returned units are validated for displayed measurements.

Date selection uses an injectable aware clock in the returned IANA timezone (provider offset fallback on systems without timezone data). Provider-local timestamps are not treated as UTC or adjusted using a hardcoded Vietnam offset. Current observations more than two hours from the clock are rejected. Dates are selected by actual daily date strings, not assumed array positions.

WMO mapping includes clear/mainly clear/partly cloudy/overcast, fog, drizzle, freezing drizzle/rain, rain, showers, snow and thunderstorms/hail. Unknown codes use an explicit unknown-condition description. Clear/mainly clear → happy; thunderstorms/hail → surprised; ordinary rain/cloud and failures → neutral. Results pass the existing emotion normalizer; no rain-based sad emotion.

Responses are deterministic Vietnamese text, usually 3–4 sentences. Rain advice uses maximum probability (at least 40%), precipitation amount (at least 0.5 mm), or a wet WMO code, without claiming certainty. Every successful result contains `Nguồn dữ liệu: Open-Meteo.`. Existing `sources` requires RAG document IDs/filenames/pages/scores, so Weather leaves `sources: []`; no API/Android DTO change was made.

Defaults (added only to tracked examples and README):

```text
WEATHER_ENABLED=true
WEATHER_CONNECT_TIMEOUT_MS=3000
WEATHER_READ_TIMEOUT_MS=6000
WEATHER_CACHE_TTL_SECONDS=600
WEATHER_GEOCODING_CACHE_TTL_SECONDS=86400
```

The existing application environment loader remains unchanged. No new key is required. Invalid/nonpositive/excessive numbers fall back to documented defaults. Connect is capped at 3 seconds; read/write/pool at 6 seconds per HTTP request. These are HTTPX I/O timeouts, not an absolute total deadline; a cold query has two sequential calls. No retry or AI timeout budget is used. Backend laptop outbound Internet is required. `WEATHER_ENABLED=false` returns a local disabled response, never AI generation.

Thread-protected RAM caches are bounded at 256 entries each, geocoding 24 hours and weather 10 minutes by default. Keys normalize place names and use coordinates/date for forecasts; cache expiry uses an injectable monotonic clock. No Redis, database table, dependency, or migration was added. Network/HTTP/JSON/schema/units failures return a friendly normal response, never exception details or invented AI weather. Missing requested dates have a specific friendly response. Logs contain only failure class and validated route request ID, never provider payloads, location text, secrets or URLs.

## Route ordering and persistence

Existing validation, request ownership lock, conversation ownership check and stored `request_id` response lookup execute first. Existing timer/calendar/map recognition and quick replies keep their priority. Weather intent is checked before the history SELECT, RAG or provider orchestration. For a recognized Weather query, the existing atomic transaction rechecks ownership and inserts the user message, executes the tool, then inserts the assistant and idempotency record and updates the conversation. Both messages and replay record commit together, or all roll back. No partially persisted user-only result is introduced. SQL-trace tests verify the user INSERT precedes tool execution and that history retrieval is absent.

Replay returns the stored response before any tool invocation, with identical message IDs/content and zero additional Open-Meteo calls. Clarifications, disabled and failure replies are persisted and replayed normally too. Non-weather history/RAG/AI/quota fallback behavior remains unchanged; the common reply validator preserves prior validation semantics.

Forbidden-call tests enable real-AI/RAG flags but replace retrieval, embeddings, prompt context, AI service, provider orchestration, Gemini, Groq and mock generation with failing sentinels. Weather succeeds without invoking them. Ownership/invalid-request tests prove the tool is not called before validation. Existing regressions cover actions, quick replies, quotas, persistence, ownership and idempotency.

## Android

Only catalog and catalog/controller tests changed. Weather category and all four entries are enabled, requiring backend + Internet, with AI/RAG flags false. Raincoat prompt now explicitly names Hà Nội. Enabling the existing category removes its disabled Stage 14B UI state without editing the sheet. The four prompts keep stable IDs.

Demo đầy đủ appends `weather_now` as its ninth manual step. Demo nhanh 3 phút stays at 4 steps; Demo không phụ thuộc quota stays at 6 without Weather. Catalog remains 25 questions across six categories. Existing confirmation, draft-only selection, bottom sheet, keyboard, navigation, progress, Send, voice, typewriter, TTS and animation code is unchanged. Tests verify all exact Weather prompts fill drafts without sending or changing non-demo state.

## Verification

Backend, existing virtual environment:

```powershell
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider tests/test_weather.py
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider tests
.\.venv\Scripts\python.exe -m compileall -q app tests
```

- Targeted: **117 passed**, 0 failures/errors/skips.
- Full: **813 passed**, 0 failures/errors/skips.
- Existing FastAPI/Starlette HTTPX TestClient deprecation warning only; no tests weakened, deleted or skipped.
- Compileall: success.
- All automated Weather tests use MockTransport; an autouse guard rejects real HTTP transport. No real external API calls occur during automated tests.

Android, existing Android Studio JBR and SDK:

```powershell
$env:JAVA_HOME = "C:\Program Files\Android\Android Studio\jbr"
$env:ANDROID_HOME = "$env:LOCALAPPDATA\Android\Sdk"
.\gradlew.bat testDebugUnitTest
.\gradlew.bat assembleDebug
```

- XML totals: **219 tests, 219 passed, 0 failures, 0 errors, 0 skipped**.
- `assembleDebug`: **BUILD SUCCESSFUL**.
- APK exists locally: `D:\nam5\semester_1\advance_android\01_trolyAI\troLyAo_ani_integration\android\app\build\outputs\apk\debug\app-debug.apk`; ignored and untracked, not installed or committed.
- `git diff --check`: passed; exact staged path and diff review required before commit.
- Tracked artifact query for APK/ZIP/database/local.properties/.env: no matches.

Optional live smoke ran only after required offline tests and Android build passed, without changing network/firewall/proxy/credentials/permissions: **one Hà Nội Geocoding request and one Forecast request**, both successful. Returned fields/units/timezone parsed, formatter succeeded, attribution present, emotion allowed. No exploratory requests or retry occurred. Documentation pages were consulted separately: [Forecast API](https://open-meteo.com/en/docs), [Geocoding API](https://open-meteo.com/en/docs/geocoding-api).

Real `backend/.env` and secrets were not inspected or edited by this task. Only tracked non-secret example settings changed. No real Gemini, Groq, RAG, embedding or other AI calls occurred. No GPS/location permission, manifest change, database migration, RAG/provider/Anna-personality modification, signing/local config change, dependency change or character asset change. Main is untouched.

Full pre-commit `git status --short` (untracked directories contain only the exact source files above; Python caches are ignored):

```text
 M .env.example
 M android/app/src/main/java/com/example/assistant/ui/demo/DemoQuestionCatalog.kt
 M android/app/src/test/java/com/example/assistant/ui/demo/DemoCatalogTest.kt
 M android/app/src/test/java/com/example/assistant/ui/demo/DemoScenarioControllerTest.kt
 M backend/.env.example
 M backend/README.md
 M backend/app/api/v1/conversations.py
?? backend/app/services/weather/
?? backend/tests/test_weather.py
?? review/stage14b-live-weather.md
```

Post-commit/push status must be empty; the delivery response records the final check.

## Physical-device checklist

1. Restart the existing backend normally (no API key change needed), with outbound Internet on its laptop. Open Weather category in the Stage 14A picker; verify it is enabled.
2. Select a question and verify it only fills the editable input: no automatic Send, thinking, speech or reveal. Verify replacement confirmation preserves an existing draft when canceled.
3. Explicitly send `Thời tiết Hà Nội hiện tại thế nào?`.
4. Send `Ngày mai Hà Nội có mưa không?`.
5. Send `Nhiệt độ ở Bắc Ninh hôm nay bao nhiêu?`.
6. Send `Hôm nay mình có nên mang áo mưa ở Hà Nội không?`.
7. Send `Thời tiết hôm nay thế nào?`; verify Anna asks for a location.
8. Verify `Nguồn dữ liệu: Open-Meteo.` appears with successful results, sensible values and no guaranteed rain claim.
9. Verify TTS, typewriter skip/gradual reveal, emotion/full-cycle animation, speech stop/replay and input microphone remain functional.
10. Verify Calendar, Maps, timer, RAG, normal AI chat and both Stage 14A tabs still work. Run Demo đầy đủ through its new ninth Weather step; quick and no-quota scenarios retain their original order.
11. Replay/retry safely and verify no crash or duplicate persisted message pair for the same request ID. A new manual Send uses a new request ID normally and may reuse the cache.
12. To exercise a real failure rather than a cache hit, temporarily disconnect backend Internet after restarting the backend (or wait over 10 minutes), then send a Weather query. Verify the friendly failure, neutral emotion and no AI-invented forecast; reconnect normally.

## Known limitations

Deterministic grammar is intentionally narrow; no arbitrary dates, general web search or automatic contextual/GPS location. Ambiguous/unavailable geocoding may require a city/country qualifier. Forecasts are estimates and can be up to 10 minutes old in cache. Two HTTPX I/O-limited requests are not a hard whole-operation deadline. RAM caches/request locks are for the existing single-worker demo, not distributed deployment. To meet user-first persistence while retaining atomicity, a cold Weather lookup holds the existing SQLite write transaction during its bounded HTTP calls; concurrent writes can encounter the existing SQLite busy timeout. No database timeout/configuration was changed. Actual phone interaction and offline-failure UX still require device verification.
