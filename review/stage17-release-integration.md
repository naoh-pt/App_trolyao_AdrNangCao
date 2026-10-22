# Stage 15–17 main integration — 2026-10-22

The user explicitly requested consolidating the latest source and publishing it to GitHub `main` so another person can clone it. This request authorizes integration after the earlier feature-only Stage 17 release; the historical device-test checklist remains outstanding.

## Included source

- Previous main: `c547e1070bab84faef73cbff479b4db7588b8f62` (Stage 14).
- Stage 15: `7d02d12`, personal memory and in-app check-ins.
- Stage 16: `bdf833f`, companion personalization and supportive check-ins.
- Stage 17: `d6571a3`, natural-language routing, multi-turn Calendar completion and manual mood selection.
- Integration branch: `integration/stage17-release-20261022`.
- Added root README with clone, prerequisites, mock/real AI setup, backend startup, Android connection options and test commands.
- Removed the developer-specific `org.gradle.java.home` from tracked Gradle settings. Each machine selects its own JDK through Android Studio or `JAVA_HOME`.

## Validation

- Fetched origin before integration; origin/main was still the Stage 14 commit above.
- Backend: `.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider` → **1011 passed**, one existing Starlette/httpx deprecation warning, 95.53 seconds. The automatic temporary-database fixture and external-network guard remain enabled.
- Android: `gradlew.bat :app:testDebugUnitTest :app:assembleDebug --console=plain` → **BUILD SUCCESSFUL**, all 44 tasks up to date. Existing XML results contain **262 tests across 19 suites**, zero failures/errors; these tests were reused from Gradle cache in this run.
- `git diff --check` passed before commit.
- No tracked `.env`, `local.properties`, database, Chroma runtime store or virtual environment was found. All 141 character frames and the Gradle Wrapper JAR are tracked.

## Limits and preservation

No physical-device test or live AI/weather request was performed in this integration. Fresh dependency installation on a separate machine was not exercised; installation instructions describe the repository's configuration and the successful local build. New clones need their own SDK/JDK, API keys for real AI and document import for RAG.

The Stage 17 local-data incident remains documented in [the original report](stage17-natural-language-router.md). This integration does not delete or repair its accepted empty rows, inspect personal database content or modify the existing local `.env`. Git history is preserved through a normal merge without force-push.
