# Stage 13 release integration

Verdict: **INTEGRATION VERIFIED — READY FOR MAIN**

## Repository and immutable checkpoints

Repository: `D:\nam5\semester_1\advance_android\01_troLyAI\troLyAo_ani_integration`.

| Checkpoint | Branch/reference | Exact SHA |
| --- | --- | --- |
| Original main | `origin/main` before integration | `8121d510a845dac761438f6e597e68d8f1872b1d` |
| Verified source | `fix/android-stage13-1-external-actions` and its origin reference | `f85fb1961294cf72a659a66f961fa9840f851d2d` |
| DEVICE_TESTED_SHA | Exact source HEAD supplied for release | `f85fb1961294cf72a659a66f961fa9840f851d2d` |
| Device-tested backup, pushed and remote-confirmed | `backup/stable-stage13-1-device-tested-20261021` | `f85fb1961294cf72a659a66f961fa9840f851d2d` |
| Pre-merge main backup, pushed and remote-confirmed | `backup/main-before-stage13-20261021` | `8121d510a845dac761438f6e597e68d8f1872b1d` |
| Integration merge | `integration/stage13-release-20261021` | `4bf31f05a641d7bbba0af8126cbcbe13e6c9eb34` |

The working tree and index were clean at entry. Fetch confirmed local/remote source equality (ahead/behind 0/0). The source's merge base is the original main SHA above; `git merge-base --is-ancestor origin/main origin/fix/android-stage13-1-external-actions` passed. No unexpected main commits existed. No unpushed source commit needed publishing.

Both backup names and the integration name were checked locally and on origin before creation; none existed. Device-tested backup was created and pushed first, before the main backup or any merge. Its tree equals source HEAD, including every tracked backend and Android file. The backup branches remain untouched after creation.

Integration was created directly from original origin/main, then merged with `--no-ff` and message `merge: integrate Stage 13 conversation and action improvements`. It had **zero conflicts**. Merge parents are original main and source HEAD. `git diff --exit-code origin/fix/android-stage13-1-external-actions HEAD` passed immediately after the merge, proving exact tree equality with the device-tested source.

## Complete source commits included

Chronological order:

1. `ef63047e3320175b15d0e51982d323832f77eac5` — `feat(backend): add local time and date quick replies`
2. `f464e50634c378ec88a45edef8f9d8126ed08006` — `feat(android): add polished typewriter chat lifecycle`
3. `cb026ccfa06ecd70b57e845caf8fe028ab6cae82` — `fix(android): restore calendar and map action launching`
4. `f73d92fde7ad03f7576eb2ed49898ef4934c1188` — `fix(backend): accept terminal punctuation in map commands`
5. `f85fb1961294cf72a659a66f961fa9840f851d2d` — `fix(backend): expand Vietnamese calendar command parsing`

Source-to-original-main summary: **26 files, 2,729 insertions, 335 deletions**. These comprise nine Android production files, six Android test files, three backend production files, three backend test files and five existing stage reports. The full source name-status/stat and each expected implementation were audited before merging. The only new integration change is this report; **no product code or behavior was changed during integration**.

## Backend functionality audited

- Stage 12 current local time, date, weekday and day-period quick replies use Vietnam UTC+07:00 with deterministic injected-clock tests and conservative full-question matching.
- Local action order remains map → calendar → timer, before quick replies/history/RAG/AI. Recognized local requests retain empty sources and bypass context fetching, retrieval, embeddings, provider orchestration, mock AI, Gemini and Groq.
- Map parsing includes the new explicit command forms and terminal `. , ? ! ; :`/whitespace cleanup, retains internal punctuation, and rejects empty locations/raw schemes/package identifiers.
- Calendar grammar supports hôm nay, ngày mai/mai, ngày kia/mốt; both date/time orders; sáng/trưa/chiều/tối/đêm and giờ/h/colon formats; all weekday numeric/spelled forms; tuần này/sau/tới; nearest weekday tới; and explicit slash/word dates. Monday starts each week. Ambiguous or past explicit dates/times and weekends clarify rather than produce malformed actions.
- Calendar timestamps remain aware ISO 8601 with +07:00, with nonblank title, valid future start and strictly later end. Default duration remains 30 minutes. The source route binds relative-date replay to the persisted original request timestamp.
- Existing timer behavior, request ownership, persistence, schema/DTO fields, conflict handling and idempotency remain compatible and covered by the full suite. No provider/RAG implementation, schema, dependency, or environment template is changed by these source commits.

## Android functionality audited

- The enabled-by-default DataStore setting **Hiệu ứng hiện chữ dần** controls gradual display of newly received assistant replies. Complete text remains in the message model/Room; existing history/user messages appear immediately without automatic reveal replay.
- Standard character-boundary segmentation plus conservative combining/emoji joining preserves Vietnamese and emoji. Reveal duration is bounded around 0.3–4.5 seconds, independently of animation FPS. Bubble tap skips only the active reveal.
- The existing coordinator models Thinking → RevealingOrSpeaking → FinalEmotion → Idle. Talk persists until reveal and speech terminate; non-neutral final emotion uses the existing complete-cycle player/watchdog. IDs/tokens invalidate stale callbacks and lifecycle cancellation prevents disposed UI updates.
- Latest-reply Dừng đọc/Đọc lại controls use complete text. Explicit replay is distinct from automatic speech; history collection does not start either automatically.
- Timer retains ACTION_SET_TIMER, duration/message and skip-UI. Calendar has ordered insert/edit/date-view candidates; Maps has geo/HTTPS candidates. Safe dispatch tries alternatives on launch failures, stops on first success, uses NEW_TASK for non-Activity contexts, and reports one friendly failure. No forced Maps package or resolveActivity preflight is present.
- The action button is a sibling outside the clickable text surface. Launches remain explicit taps behind the existing duplicate-tap guard, with no composition/navigation-driven automatic launch.
- FPS, font-size controls, speech/voice-input behavior, backend URL settings, character assets/frame ordering, layout/IME/transparency, Gradle configuration, manifest, API DTOs and package/SDK settings remain present. Protected paths were compared to original main and are unchanged except the already reviewed display-setting addition in its own file.

## Integration verification

Backend, from `backend`:

```powershell
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider tests
.\.venv\Scripts\python.exe -m compileall -q app tests
```

Result: **696 passed, zero failures/errors/skips**, 31.31 seconds. Compileall: **exit 0**, no output. One existing Starlette/httpx TestClient deprecation warning remains. Tests use existing mocks/fakes, isolated temporary SQLite and local route clients; new local-action route tests explicitly forbid provider/retrieval/embedding execution.

Android, from `android`:

```powershell
$env:JAVA_HOME = "C:\Program Files\Android\Android Studio\jbr"
$env:ANDROID_HOME = "$env:LOCALAPPDATA\Android\Sdk"
.\gradlew.bat testDebugUnitTest
# Initial command succeeded but reused up-to-date prior results.
.\gradlew.bat testDebugUnitTest --rerun-tasks
# Forced fresh execution: BUILD SUCCESSFUL in 46s, 25 tasks executed.
.\gradlew.bat assembleDebug
# BUILD SUCCESSFUL in 2s; incremental outputs remain up to date.
```

All 14 fresh XML suite results were inspected, with new run timestamps:

| Suite | Tests | Passed | Failed | Errors | Skipped |
| --- | ---: | ---: | ---: | ---: | ---: |
| AnimationFpsSettingsTest | 16 | 16 | 0 | 0 | 0 |
| ChatDisplaySettingsTest | 5 | 5 | 0 | 0 | 0 |
| TypewriterSettingsTest | 3 | 3 | 0 | 0 | 0 |
| SpeechSettingsAndEventTest | 17 | 17 | 0 | 0 | 0 |
| CharacterAnimationPlayerTest | 10 | 10 | 0 | 0 | 0 |
| CharacterFrameResourcesTest | 6 | 6 | 0 | 0 | 0 |
| ChatAnimationIntegrationTest | 9 | 9 | 0 | 0 | 0 |
| ConversationPolishLifecycleTest | 18 | 18 | 0 | 0 | 0 |
| ExternalActionLaunchingTest | 34 | 34 | 0 | 0 | 0 |
| ReplyRevealTest | 22 | 22 | 0 | 0 | 0 |
| SpeechAnimationSyncTest | 12 | 12 | 0 | 0 | 0 |
| Stage11AssistantActionsAndEmotionTest | 18 | 18 | 0 | 0 | 0 |
| VoiceInputTest | 9 | 9 | 0 | 0 | 0 |
| UnitTest | 7 | 7 | 0 | 0 | 0 |
| **Total** | **186** | **186** | **0** | **0** | **0** |

APK exists at `D:\nam5\semester_1\advance_android\01_trolyAI\troLyAo_ani_integration\android\app\build\outputs\apk\debug\app-debug.apk`, **17,046,512 bytes**. git check-ignore confirms it is ignored; git ls-files confirms it is not tracked. It is not staged or installed on a phone.

## Repository, artifact and credential audit

- `git diff --check` passes both for the source range and the integration working tree.
- Required tracked-file queries return no ZIP, APK, database, actual .env, local.properties, virtual environment or Android build output. No generated/sensitive file entered the merge or index.
- All tracked UTF-8 text files were scanned without printing secret values. No recognizable real Google/Groq/OpenAI/AWS credential signatures or private-key blocks were found. Credential assignments in root/backend .env.example were verified empty/placeholders; application configuration reads credentials from environment. Local .env contents were not printed or edited.
- No merge conflict markers were found in tracked text. No manual conflict resolution was needed.
- Gradle wrappers (including wrapper JAR/properties), backend requirements, root/backend environment templates and Android/backend README instructions remain tracked.
- **No real Gemini, Groq, embedding, RAG, weather, web-search or other external API calls occurred.** Network activity was limited to authorized Git operations; tests used existing local mocks/fakes. No Full Access permission was requested. Existing managed approval was used for linked Git metadata and Gradle cache/SDK operations.
- No branch, user file, report, asset, environment, database or signing file was deleted or modified outside the requested integration scope. No source files outside the repository were edited.

## Status, limitations and main gate

Final integration-branch `git status --short` after committing this report is empty (no lines), checked before pushing the integration branch. Immediately before report creation, it was also empty. Only this report is staged/committed for integration documentation.

```text
```

Publish this report with `docs(review): record Stage 13 release integration`, then push `integration/stage13-release-20261021`. Before merging into main, refresh origin/main and require it to equal the original SHA above. Main publication is conditional on the clean integration push and a conflict-free main merge, followed by another full backend run, compileall, fresh Android JVM run, assembleDebug and hygiene checks. Final main/report commit SHAs and final-main results are recorded in the completion response because they do not yet exist at this report's commit.

Known limitations retained from the tested source: typewriter is Android presentation after a full backend response, not backend streaming; deterministic Calendar grammar deliberately clarifies ambiguous hours, bare weekdays and unspecified weekends; external apps/TTS engines differ by device and date-view fallback may show a date rather than an editor; actions require external-app confirmation and no calendar provider writes occur. JVM tests do not replace physical rendering/Intent/TTS tests. The user has supplied the release's physical-device acceptance; no new device install or paid/live API validation was performed during integration.

Do not delete source, integration or backup branches after publication. Stage 14 is not started. Recommended next branch: `feature/stage14-personal-memory`.
