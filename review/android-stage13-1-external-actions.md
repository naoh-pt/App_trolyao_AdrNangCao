# Android Stage 13.1 — Calendar and Maps external actions

Verdict: **READY FOR DEVICE TEST**

## Repository and base

- Repository: `D:\nam5\semester_1\advance_android\01_troLyAI\troLyAo_ani_integration` (Windows resolves the existing `01_trolyAI` spelling to the same directory).
- Branch: `fix/android-stage13-1-external-actions`.
- Base branch: `origin/feature/android-stage13-conversation-polish`.
- Exact base SHA: `f464e50634c378ec88a45edef8f9d8126ed08006`.
- Initial working tree was clean. Fetch verified the remote Stage 13 branch at exactly the local committed HEAD. The requested fix branch did not exist locally or remotely and was created directly from that verified HEAD.
- No Stage 13 changes are omitted. No merge into Stage 13 or main, no push to main, and no history rewriting.
- Authorized Git operations required sandbox access to this checkout's linked-worktree Git metadata. Gradle required access to the existing cache and SDK. No source files outside the repository were modified.

## Findings and root-cause evidence

Inspected AssistantActionDispatcher, ChatScreen, ChatViewModel, action DTOs/parsing, AndroidManifest, existing action tests, and the Stage 11/13 reports using `rg` and UTF-8 reads before editing. No repository AGENTS.md was found.

The existing code already had a Maps geo → HTTPS fallback, a Calendar insert → Google Calendar web-template fallback, and non-Activity NEW_TASK handling. It did **not** call resolveActivity or force the Google Maps package. Those suspected causes were therefore not attributed to this regression.

Confirmed implementation defects:

1. Calendar offered no native ACTION_EDIT or calendar-date ACTION_VIEW fallback when an installed calendar did not accept ACTION_INSERT. The Stage 11 report's recorded device evidence explicitly says Calendar ACTION_INSERT could not resolve on that phone. A browser template could open a web page, but could not repair the missing native-calendar alternatives.
2. Both previous launch branches tried a fallback only after ActivityNotFoundException. SecurityException and other runtime Context/launch failures immediately abandoned all alternatives. Those catches exposed exception messages to the user and recorded no candidate-specific diagnostic evidence. The new loop recovers through all safe candidates after these failures.
3. Map queries retained conversational terminal punctuation. Cleanup now searches the intended place name while preserving internal punctuation. This is a query-quality defect; punctuation by itself is not proof of a failure to open an app.
4. Calendar parsing silently substituted a title for blank input and replaced explicitly malformed end times with a default; it did not reject end <= start. Validation now rejects these malformed payloads before any dispatch.

The exact runtime exception behind the reported Maps failure cannot be established from repository code alone. No phone logcat or new device execution was available, and no claim is made that the manifest or typewriter consumed that tap. This hotfix closes the observed code-level failure paths and adds privacy-safe diagnostics for physical-device retesting. A target app can also accept startActivity and then ignore a URI; successful dispatch cannot verify another app's rendered UI.

## Exact changed files

| Status | Path |
| --- | --- |
| Modified | `android/app/src/main/java/com/example/assistant/ui/chat/AssistantActionDispatcher.kt` |
| Modified | `android/app/src/test/java/com/example/assistant/ui/chat/Stage11AssistantActionsAndEmotionTest.kt` |
| Added | `android/app/src/test/java/com/example/assistant/ui/chat/ExternalActionLaunchingTest.kt` |
| Added | `review/android-stage13-1-external-actions.md` |

The existing Stage 11 test retains all assertions. Its no-automatic-launch Calendar fixture now supplies a valid title to comply with the requested blank-title rejection. No existing tests were deleted or weakened.

## Ordered candidates and validation

`buildActionCandidates` creates immutable action/data/extras/flags descriptions, which are directly exercised by JVM tests. `buildActionIntents` exposes the corresponding framework Intents, and the existing primary-only builder remains a compatibility entrypoint. Each production dispatch materializes a fresh Intent. No backend field supplies an Intent, package, component, action name, or raw destination URI.

Calendar order:

1. ACTION_INSERT with `CalendarContract.Events.CONTENT_URI`.
2. ACTION_EDIT with the same event URI and extras.
3. ACTION_VIEW at `content://com.android.calendar/time/<startMillis>`.

The insert/edit candidates retain trimmed title, begin/end epoch milliseconds, and `Được tạo bởi trợ lý ảo Anna`. The view candidate carries the same safe extras; the platform's date-view contract uses its time URI and may ignore editor extras. It opens near the requested start time rather than promising an event-creation form. No event ID is guessed and no CalendarProvider writes occur. The user must create/save any event in the external app. The old Calendar web-template helper remains for compatibility with the existing tests, but is not part of this hotfix's ordered launch path.

The [Android Calendar intent contract](https://developer.android.com/identity/providers/calendar-provider#calendar-intents) documents collection INSERT/EDIT and time-based VIEW, along with handing event confirmation to the Calendar UI without calendar permissions.

Calendar parsing rejects missing/blank title, missing/invalid/timezone-less start, explicitly invalid end, and end <= start. An absent end retains the existing 30-minute default, with overflow-safe addition. No arbitrary backend URI is used.

Maps order:

1. ACTION_VIEW with `geo:0,0?q=<encoded query>`.
2. ACTION_VIEW with `https://www.google.com/maps/search/?api=1&query=<encoded query>`.

Both remain implicit and package-free so any compatible map app/browser can handle them. The query is trimmed; harmless trailing `. , ? ! ; :` and suffix whitespace are removed. Internal punctuation remains, including apostrophes, colons, slashes, commas, hyphens, and periods. Meaningful terminal dotted initialisms such as `D.C.` are preserved. Empty/punctuation-only queries are rejected. URI-like inputs such as javascript/file/intent/content/data/geo and scheme-plus-`://` are rejected; all accepted text is encoded strictly as a UTF-8 search parameter (spaces become `%20`, delimiters cannot introduce parameters or a new URI scheme).

Timer remains a single AlarmClock.ACTION_SET_TIMER candidate with the existing message, duration in seconds and EXTRA_SKIP_UI=true. Default message and positive-duration validation are preserved.

## Dispatch, errors, manifest and clicks

- `launchActionSafely` parses the DTO once and dispatches candidates sequentially. It returns immediately after the first successful startActivity, so one tap has at most one successful external launch.
- Every attempt receives a candidate copy. For any Context that is not directly an Activity, its copy gains FLAG_ACTIVITY_NEW_TASK before a new Intent is created. Original candidates are untouched. Activity contexts do not receive an unnecessary flag. Tests also exercise the actual adapter's putExtra/addFlags calls using a recording Intent subclass, avoiding misleading assertions against no-op framework getters.
- RuntimeException recovery includes ActivityNotFoundException, SecurityException and framework Context failures. It advances to the next candidate. Only after exhausting candidates (or rejecting an invalid payload) is one friendly message reported. Timer: `Không tìm thấy ứng dụng hẹn giờ phù hợp trên thiết bị.` Calendar: `Không thể mở ứng dụng lịch trên thiết bị.` Maps: `Không thể mở ứng dụng bản đồ hoặc trình duyệt trên thiết bị.` Unknown action types retain a generic invalid-action message.
- Failed attempts log only the allowlisted action type, one-based candidate index and exception class under tag `AssistantActions`. No exception message, URI, title, query, conversation text, secret or stack trace is logged or exposed.
- resolveActivity was absent and remains absent. Controlled startActivity attempts avoid package-visibility preflight false negatives.
- **AndroidManifest.xml is unchanged.** No queries are needed for this direct-dispatch approach; no QUERY_ALL_PACKAGES or Calendar read/write permissions were added.
- **ChatScreen.kt is unchanged.** In MessageBubble, the skip clickable is attached only to the text Surface. ActionCardButton is a sibling following that Surface inside a non-clickable Column, separated by its existing spacer. Its onClick invokes only onActionClick(action), with no call to onSkip. The action callback is executed only from the button, behind the existing ViewModel rapid-tap guard. No launch occurs during composition or LaunchedEffect, so recomposition and returning from another app cannot automatically relaunch it. Labels, styling, placement, visibility and confirmation semantics are preserved.
- There is no Compose UI/device-test runner in the current JVM setup. Click isolation was verified structurally; no synthetic callback holder or heavy UI test dependency was introduced merely to mirror that structure. The existing typewriter skip/controller regression tests still pass; physical pointer-event checks are explicitly listed below.

## Verification

From `android`:

```powershell
$env:JAVA_HOME = "C:\Program Files\Android\Android Studio\jbr"
$env:ANDROID_HOME = "$env:LOCALAPPDATA\Android\Sdk"
.\gradlew.bat testDebugUnitTest
.\gradlew.bat assembleDebug
```

Final tests: **BUILD SUCCESSFUL in 10s**. Final assembleDebug: **BUILD SUCCESSFUL in 8s**. An earlier development compile caught receiver shadowing inside Intent.apply; it was corrected before final verification, with adapter regression tests added. No Gradle/SDK/dependency changes were necessary.

Inspected all 14 XML suite files in `android/app/build/test-results/testDebugUnitTest`:

| Suite | Executed | Passed | Failed | Errors | Skipped |
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

The 34 new tests exercise Calendar URI/order/extras/validation/default duration, map cleanup/encoding/unsafe-input rejection/package-free construction, native/browser fallbacks, SecurityException/runtime failures, exactly one final error, NEW_TASK copies, timer preservation, one successful launch per tap, and framework-adapter extras/flags/fresh-object behavior. All 152 existing regression tests remain, including Stage 13 history/reveal, TTS/animation synchronization, voice input, settings persistence, FPS/font settings and timer/calendar/map actions.

APK: `D:\nam5\semester_1\advance_android\01_trolyAI\troLyAo_ani_integration\android\app\build\outputs\apk\debug\app-debug.apk`, 17,046,512 bytes. It is ignored by Git and neither tracked nor staged. No APK was installed on a phone.

Root verification ran git diff --check, status --short, diff --stat, diff --name-status, diff --cached --name-status, and the requested artifact query. diff --check passes with no output. `git ls-files "*.apk" "*.zip" "*.db" "*.sqlite" "*.sqlite3" "local.properties" ".env"` returns no paths. The staged diff is limited to the four paths listed above, with no artifact, secret, image, backend or unrelated change.

Backend source, API DTOs/paths/timeouts, RAG/providers, voice input, TTS, typewriter, animations/FPS, settings/font size, all character images/frames, layout/IME and conversation/persistence/request-ID logic are untouched. No real Gemini/Groq/embedding/RAG or other external API calls occurred. Network access was limited to authorized Git operations and reading public Android documentation; tests used local injected launchers, with no external app opened.

## Publication and final status

Commit message: `fix(android): restore calendar and map action launching`. Push only `fix/android-stage13-1-external-actions` to origin, without merging into Stage 13 or main.

Full final `git status --short` after successful commit/push is empty (no lines), verified again at closeout. The completion response supplies the resulting commit SHA and push result.

```text
```

## Exact physical-device checklist

Install this APK yourself. Keep the phone's existing Calendar/Maps/browser apps enabled for the primary pass. Use a local/mock backend if avoiding external AI providers. No action should launch until its confirmation button is tapped.

| Send exactly | Tap and verify |
| --- | --- |
| `Tìm trên bản đồ Học viện Kỹ thuật Mật mã` | Tap Mở bản đồ once: map app/chooser or HTTPS browser search opens for the correct Vietnamese place. |
| `Tìm trên bản đồ Hồ Gươm.` | Tap Mở bản đồ: search is for Hồ Gươm without the terminal period. |
| `Tìm đường đến Đại học Bách khoa Hà Nội` | Tap the proposed map confirmation: the correct destination search opens; this patch does not change the backend's map-search contract into turn-by-turn navigation. |
| `Tạo lịch học Android vào ngày mai lúc 8 giờ tối` | Tap Mở lịch để xác nhận: verify tomorrow 20:00, correct title, end after start and Anna description in an editor when supported. If both editor actions are unavailable, verify the calendar opens near that date/time. Save only if you intend to create the event. |
| `Thêm lịch họp nhóm ngày mai lúc 19 giờ` | Tap Calendar confirmation and verify tomorrow 19:00 with correct title/time. Cancel and confirm no event was saved. |
| `Nhắc tôi học bài sau 5 phút` | Tap timer confirmation: existing Clock behavior starts/configures a 300-second timer, preserving skip-UI behavior. |

Then verify:

1. While an action reply is still revealing, tap its action button: exactly one external UI opens. On returning, there is no relaunch. Repeat after reveal completes.
2. Separately tap the revealing text bubble outside the action button: text completes immediately and no external app opens. Repeat with TTS active; TTS and emotion sequencing must retain Stage 13 behavior.
3. Return from Maps/Calendar, rotate or trigger recomposition, and reopen conversation history: no automatic action launch. A later deliberate tap may launch again; rapid duplicate taps remain guarded.
4. Where practical on a test phone/profile, test a device without a geo handler but with a browser to exercise HTTPS, and a calendar supporting edit/view but not insert. Do not disable/uninstall personal apps solely for this test. If no compatible handler exists, expect exactly one friendly Vietnamese error with no exception details.
5. Confirm existing voice input, settings, typewriter toggle, FPS/font size, history, keyboard layout, TTS stop/replay and full emotion cycles still work. The existing lifecycle stops output when leaving chat for an external app.
6. If a launch still fails, capture `adb logcat -s AssistantActions` while tapping once and record action type/candidate index/exception class. The diagnostic tag intentionally omits location/event/conversation content. A successful startActivity with no resulting UI requires checking the target app on the device; JVM tests cannot certify it.
