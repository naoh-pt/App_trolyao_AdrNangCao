# Backend Stage 13.1b — Map command punctuation

Verdict: **READY FOR DEVICE TEST**

- Repository: `D:\nam5\semester_1\advance_android\01_troLyAI\troLyAo_ani_integration`.
- Branch: `fix/android-stage13-1-external-actions` throughout this task.
- Initial HEAD/base: `cb026ccfa06ecd70b57e845caf8fe028ab6cae82`.
- Initial `git status --short` was empty. No checkout, merge, reset, rebase or history rewriting was performed.

## Root cause and scope

The map recognizer had forms such as `tìm <place> trên bản đồ`, `mở bản đồ tìm <place>` and `tìm đường đến <place>`, but **no** `tìm trên bản đồ <place>` or `tìm bản đồ <place>` form. Thus the reported command fell through even without its period. Separately, map patterns matched raw text while the shared extracted-text cleaner left terminal `.?!` in captured place names. Existing suffix-anchored forms could also fail when punctuation followed `trên bản đồ`.

Inspected the action service, existing timer/calendar/map tests, message persistence/idempotency tests, quick-reply/provider bypass tests, route and response serializers before editing. The route already checks actions before history, quick replies, RAG or AI. No route or provider change is necessary.

Exact files:

| Status | File |
| --- | --- |
| Modified | `backend/app/services/assistant_action_service.py` |
| Added | `backend/tests/test_map_command_punctuation.py` |
| Added | `review/backend-stage13-1b-map-punctuation.md` |

No Android files, API/DTO schemas, database schemas, dependencies, environment files, settings, provider routing, or calendar Intent code changed.

## Normalization and matching

Appended one fully anchored pattern for `tìm [trên] bản đồ <place>` after the existing patterns, retaining their order and optional existing `xin`/`hãy` prefixes. Recognition still follows map → calendar → timer. The new missing-place form `tìm bản đồ` requests clarification without an action.

Only map parsing strips a terminal run matching `[\s.,?!;:]+$` before matching, then applies the same suffix rule to the extracted query. This handles repeated/mixed terminal punctuation and whitespace, including suffixes separated by spaces. Location casing and internal punctuation remain; internal whitespace retains the existing whitespace-collapse behavior. The shared normalizer/task cleaner and timer/calendar code are unchanged. Blank cleaned input cannot produce a map action. The existing maximum query length remains unchanged.

Raw URI-scheme prefixes and complete package-like identifiers are rejected with the existing plain-place-name clarification. No backend-provided URI, Android package, Intent, or action type is launched or added to the schema. Ordinary sentences are not matched through a loose map-keyword search; the patterns still require explicit anchored command forms.

## Positive and negative coverage

All seven requested commands pass unit recognition and route tests, with these extracted queries:

| Command | Query |
| --- | --- |
| `Tìm trên bản đồ Hồ Gươm` | `Hồ Gươm` |
| `Tìm trên bản đồ Hồ Gươm.` | `Hồ Gươm` |
| `Tìm trên bản đồ Hồ Gươm!` | `Hồ Gươm` |
| `Tìm trên bản đồ Hồ Gươm?` | `Hồ Gươm` |
| `Tìm trên bản đồ Hồ Gươm,` | `Hồ Gươm` |
| `Tìm bản đồ Học viện Kỹ thuật Mật mã.` | `Học viện Kỹ thuật Mật mã` |
| `Tìm đường đến Đại học Bách khoa Hà Nội.` | `Đại học Bách khoa Hà Nội` |

Additional positives cover repeated trailing spaces, `?!`, `,;:`, mixed punctuation/spaces, tab/newline suffixes, all existing command forms, and punctuation inside `Bảo tàng A:B, St. John's - Q.1` and `Bảo tàng A:B, C-D`.

Negative coverage includes blank/punctuation-only locations, ordinary map conversation (`Bản đồ là gì?`, questions about reading maps, school maps and map symbols), quoted commands inside explanatory sentences, raw HTTPS/geo/file/content/javascript/intent/custom schemes, and Android package identifiers. These produce no map action; conversational questions continue normal fallthrough.

Existing timer/calendar tests remain unchanged and pass. A focused regression additionally verifies the 300-second `Học bài` timer and tomorrow's 20:00–20:30 `Nộp bài` calendar event.

## Route, bypass and persistence evidence

For every requested command, tests exercise both USE_REAL_AI=false and true, with RAG_ENABLED=true. Immediate-failure guards replace quick replies, route retrieval/prompt construction, RAG embedding, mock AI generation, AI orchestration/get-provider entrypoints, ProviderService, GeminiProvider and GroqProvider generation. All 14 route cases pass without reaching a guard. SQL traces also confirm the conversation-context history SELECT never executes on either initial send or request replay.

Each case verifies HTTP 200, the exact existing response/message/action field sets (including unchanged nullable action fields), valid message UUIDs/timestamps, matching top-level/nested map actions, happy emotion, correct cleaned query and `sources: []`.

Persistence checks reopen SQLite and assert exactly the complete saved user/assistant rows, unchanged original user text, assistant confirmation containing the cleaned query, one request-id record linked to the same message IDs, and no source records. Replaying the same request_id with outer whitespace returns the identical response/action and creates no duplicates.

The existing persistence contract stores messages and the normalized request text; `_saved_response` reconstructs the structured action from that saved request. There is no separately persisted action column/table. This fix preserves that behavior and verifies reconstructed replay actions without adding a migration or claiming a new action store. History-list behavior is unchanged.

No real Gemini, Groq, RAG, embedding or other external API calls occurred. All new route tests use local TestClient, isolated SQLite files and failure guards. The full suite uses its existing mock/local fixtures.

## Verification

From `backend`:

```powershell
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider tests/test_map_command_punctuation.py tests/test_assistant_action_service.py tests/test_messages.py
# 88 passed, 1 warning in 2.06s

.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider tests
# 469 passed, 1 warning in 27.39s

.\.venv\Scripts\python.exe -m compileall -q app tests
# Exit 0; no output
```

The 53 new tests increase the prior 416-test backend suite to 469. The single warning is the existing installed Starlette/httpx TestClient deprecation. During development, the new schema assertion was corrected to include existing nullable action fields; production DTO/serializer behavior was preserved.

Root checks: `git diff --check` passes; `git status --short`, `git diff --stat`, and `git diff --name-status` show only the expected service/test/report paths. `git diff cb026ccfa06ecd70b57e845caf8fe028ab6cae82 -- android` is empty. No generated artifact, secret, database, dependency or unrelated file is staged.

Full reviewed `git status --short` before staging:

```text
 M backend/app/services/assistant_action_service.py
?? backend/tests/test_map_command_punctuation.py
?? review/backend-stage13-1b-map-punctuation.md
```

Publication: stage only these three files, review the staged diff, commit `fix(backend): accept terminal punctuation in map commands`, and push only `fix/android-stage13-1-external-actions`. No merge into main. Final post-publication status must be empty and is verified in the completion response.

## Device follow-up

Restart the backend from this branch so the running process loads the fix. Send each of the seven commands above as a new request and confirm the map button appears with the expected query. This repair affects backend recognition; it does not alter Calendar launching. Android's Stage 13.1 launcher remains at the previously committed version.
