package com.example.assistant.ui.chat

import android.app.Activity
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.provider.AlarmClock
import android.provider.CalendarContract
import android.util.Log
import com.example.assistant.data.remote.AssistantActionDto
import java.net.URLEncoder
import java.nio.charset.StandardCharsets
import java.time.Instant
import java.time.OffsetDateTime
import java.time.ZoneOffset
import java.time.format.DateTimeFormatter
import java.util.Locale

/** Allowlisted assistant action type strings. */
object AssistantActionTypes {
    const val SET_TIMER = "set_timer"
    const val CREATE_CALENDAR_EVENT = "create_calendar_event"
    const val MAP_SEARCH = "map_search"
}

const val CALENDAR_DEFAULT_DESCRIPTION = "Được tạo bởi trợ lý ảo Anna"
const val MAP_WEB_SEARCH_BASE_URL = "https://www.google.com/maps/search/?api=1&query="
const val CALENDAR_WEB_TEMPLATE_BASE_URL = "https://calendar.google.com/calendar/render"

private val UTC_CALENDAR_DATE_FORMATTER: DateTimeFormatter =
    DateTimeFormatter.ofPattern("yyyyMMdd'T'HHmmss'Z'", Locale.US)
        .withZone(ZoneOffset.UTC)

/** Safely percent-encodes a URI query parameter in UTF-8 (space as %20). */
fun encodeUriComponent(value: String): String {
    return URLEncoder.encode(value, StandardCharsets.UTF_8.name()).replace("+", "%20")
}

/** Formats an epoch millisecond timestamp as UTC ISO compact string (yyyyMMdd'T'HHmmss'Z'). */
fun formatUtcCalendarDate(epochMillis: Long): String {
    return UTC_CALENDAR_DATE_FORMATTER.format(Instant.ofEpochMilli(epochMillis))
}

/** Builds the safe geo: URI for map searches. */
fun buildMapGeoUri(query: String): String {
    return "geo:0,0?q=${encodeUriComponent(requireNotNull(cleanMapQuery(query)))}"
}

/** Builds the safe Google Maps HTTPS web search URL for map searches. */
fun buildMapWebSearchUrl(query: String): String {
    return "$MAP_WEB_SEARCH_BASE_URL${encodeUriComponent(requireNotNull(cleanMapQuery(query)))}"
}

/** Plain location text only; never accept a backend URI as a launch destination. */
fun cleanMapQuery(query: String?): String? {
    var cleaned = query?.trim() ?: return null
    if (Regex("(?i)^(?:[a-z][a-z0-9+.-]*://|(?:javascript|file|intent|content|data|geo):)").containsMatchIn(cleaned)) return null
    cleaned = cleaned.trimEnd { it.isWhitespace() || it in ",?!;:" }
    // Preserve meaningful final initialisms such as D.C.; remove conversational periods otherwise.
    if (!Regex("(?:\\p{L}\\.){2,}$").containsMatchIn(cleaned)) {
        cleaned = cleaned.trimEnd { it.isWhitespace() || it in ".,?!;:" }
    }
    return cleaned.takeIf { it.isNotBlank() }
}

/** Builds the fallback Intent for web browser map search. */
fun buildMapWebFallbackIntent(query: String): Intent {
    return Intent(Intent.ACTION_VIEW, Uri.parse(buildMapWebSearchUrl(query)))
}

/** Builds the safe Google Calendar web template URL for calendar event creation. */
fun buildCalendarWebTemplateUrl(
    title: String,
    startMillis: Long,
    endMillis: Long,
    description: String = CALENDAR_DEFAULT_DESCRIPTION,
): String {
    val encodedTitle = encodeUriComponent(title)
    val startDate = formatUtcCalendarDate(startMillis)
    val endDate = formatUtcCalendarDate(endMillis)
    val encodedDesc = encodeUriComponent(description)
    return "$CALENDAR_WEB_TEMPLATE_BASE_URL?action=TEMPLATE&text=$encodedTitle&dates=$startDate/$endDate&details=$encodedDesc"
}

/** Builds the fallback Intent for web browser calendar template. */
fun buildCalendarWebFallbackIntent(
    title: String,
    startMillis: Long,
    endMillis: Long,
    description: String = CALENDAR_DEFAULT_DESCRIPTION,
): Intent {
    return Intent(Intent.ACTION_VIEW, Uri.parse(buildCalendarWebTemplateUrl(title, startMillis, endMillis, description)))
}

/**
 * Prepares a caller-owned Intent. Candidate materialization always creates a fresh Intent.
 * Ensures [intent] has [Intent.FLAG_ACTIVITY_NEW_TASK] if [context] is not an [Activity].
 * Does not add the flag unnecessarily when an [Activity] context is available.
 */
internal fun prepareForContext(context: Context, intent: Intent): Intent {
    if (context !is Activity) {
        intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
    }
    return intent
}

/** Pure structured payloads for allowlisted assistant actions. */
sealed interface AssistantActionPayload {
    data class SetTimer(
        val message: String,
        val durationSeconds: Int,
    ) : AssistantActionPayload

    data class CreateCalendarEvent(
        val title: String,
        val startMillis: Long,
        val endMillis: Long,
    ) : AssistantActionPayload

    data class MapSearch(
        val query: String,
    ) : AssistantActionPayload
}

/** Parses an ISO 8601 timestamp string (e.g. "2026-10-10T20:00:00+07:00") to epoch milliseconds. */
fun parseIsoTimestampToMillis(isoString: String?): Long? {
    if (isoString.isNullOrBlank()) return null
    return try {
        OffsetDateTime.parse(isoString).toInstant().toEpochMilli()
    } catch (_: Exception) {
        try {
            Instant.parse(isoString).toEpochMilli()
        } catch (_: Exception) {
            null
        }
    }
}

/**
 * Pure parsing of [AssistantActionDto] into typed [AssistantActionPayload].
 * Returns null if the action type is unknown or if mandatory fields are missing/invalid.
 */
fun parseActionPayload(dto: AssistantActionDto): AssistantActionPayload? = when (dto.type) {
    AssistantActionTypes.SET_TIMER -> {
        val duration = dto.durationSeconds
        if (duration != null && duration > 0) {
            val msg = if (!dto.message.isNullOrBlank()) dto.message.trim() else "Hẹn giờ"
            AssistantActionPayload.SetTimer(message = msg, durationSeconds = duration)
        } else {
            null
        }
    }

    AssistantActionTypes.CREATE_CALENDAR_EVENT -> {
        val startMillis = parseIsoTimestampToMillis(dto.startAt)
        val title = dto.title?.trim()
        val endMillis = if (dto.endAt == null && startMillis != null) {
            runCatching { Math.addExact(startMillis, 30 * 60 * 1000L) }.getOrNull()
        } else parseIsoTimestampToMillis(dto.endAt)
        if (startMillis != null && endMillis != null && endMillis > startMillis && !title.isNullOrBlank()) {
            AssistantActionPayload.CreateCalendarEvent(
                title = title,
                startMillis = startMillis,
                endMillis = endMillis,
            )
        } else {
            null
        }
    }

    AssistantActionTypes.MAP_SEARCH -> {
        val q = cleanMapQuery(dto.query)
        if (!q.isNullOrBlank()) {
            AssistantActionPayload.MapSearch(query = q)
        } else {
            null
        }
    }

    else -> null
}

/** Immutable description of an allowlisted Intent; also usable without Android framework stubs. */
data class ActionIntentCandidate(
    val action: String,
    val dataUri: String? = null,
    val extras: Map<String, Any> = emptyMap(),
    val flags: Int = 0,
) {
    /** Each dispatch gets a new framework object; shared candidates are never mutated. */
    internal fun toIntent(createIntent: (String) -> Intent = { Intent(it) }): Intent = createIntent(action).apply {
        dataUri?.let { data = if (it == CALENDAR_EVENTS_URI) CalendarContract.Events.CONTENT_URI else Uri.parse(it) }
        this@ActionIntentCandidate.extras.forEach { (key, value) ->
            when (value) {
                is String -> putExtra(key, value)
                is Long -> putExtra(key, value)
                is Int -> putExtra(key, value)
                is Boolean -> putExtra(key, value)
            }
        }
        addFlags(this@ActionIntentCandidate.flags)
    }
}

internal const val CALENDAR_EVENTS_URI = "content://com.android.calendar/events"

/** Only fixed platform actions/URI roots and typed, validated extras are constructed. */
fun buildActionCandidates(payload: AssistantActionPayload): List<ActionIntentCandidate> = when (payload) {
    is AssistantActionPayload.SetTimer -> if (payload.durationSeconds > 0) listOf(
        ActionIntentCandidate(AlarmClock.ACTION_SET_TIMER, extras = mapOf(
            AlarmClock.EXTRA_MESSAGE to payload.message,
            AlarmClock.EXTRA_LENGTH to payload.durationSeconds,
            AlarmClock.EXTRA_SKIP_UI to true,
        )),
    ) else emptyList()

    is AssistantActionPayload.CreateCalendarEvent -> {
        if (payload.title.isBlank() || payload.endMillis <= payload.startMillis) emptyList() else {
            val extras = mapOf(
                CalendarContract.Events.TITLE to payload.title.trim(),
                CalendarContract.EXTRA_EVENT_BEGIN_TIME to payload.startMillis,
                CalendarContract.EXTRA_EVENT_END_TIME to payload.endMillis,
                CalendarContract.Events.DESCRIPTION to CALENDAR_DEFAULT_DESCRIPTION,
            )
            listOf(
                ActionIntentCandidate(Intent.ACTION_INSERT, CALENDAR_EVENTS_URI, extras),
                ActionIntentCandidate(Intent.ACTION_EDIT, CALENDAR_EVENTS_URI, extras),
                // Opens a calendar date, never writes/saves an event or guesses an event ID.
                ActionIntentCandidate(Intent.ACTION_VIEW,
                    "content://com.android.calendar/time/${payload.startMillis}", extras),
            )
        }
    }

    is AssistantActionPayload.MapSearch -> {
        val query = cleanMapQuery(payload.query)
        if (query == null) emptyList() else listOf(
            ActionIntentCandidate(Intent.ACTION_VIEW, buildMapGeoUri(query)),
            ActionIntentCandidate(Intent.ACTION_VIEW, buildMapWebSearchUrl(query)),
        )
    }
}

fun buildActionIntents(payload: AssistantActionPayload): List<Intent> =
    buildActionCandidates(payload).map { it.toIntent() }

/** Compatibility entrypoint for callers needing only the primary candidate. */
fun buildActionIntent(payload: AssistantActionPayload): Intent = buildActionIntents(payload).first()

/**
 * Returns user-facing label text for an assistant action button.
 */
fun actionButtonLabel(dto: AssistantActionDto): String {
    if (dto.label.isNotBlank()) return dto.label
    return when (dto.type) {
        AssistantActionTypes.SET_TIMER -> "Đặt hẹn giờ"
        AssistantActionTypes.CREATE_CALENDAR_EVENT -> "Mở lịch để xác nhận"
        AssistantActionTypes.MAP_SEARCH -> "Mở bản đồ"
        else -> "Thực hiện"
    }
}

internal fun actionLaunchError(type: String): String = when (type) {
    AssistantActionTypes.SET_TIMER -> "Không tìm thấy ứng dụng hẹn giờ phù hợp trên thiết bị."
    AssistantActionTypes.CREATE_CALENDAR_EVENT -> "Không thể mở ứng dụng lịch trên thiết bị."
    AssistantActionTypes.MAP_SEARCH -> "Không thể mở ứng dụng bản đồ hoặc trình duyệt trên thiết bị."
    else -> "Hành động không hợp lệ hoặc dữ liệu bị thiếu."
}

/**
 * Parse once, then try the allowlisted candidates in order. The injected launcher observes the
 * exact immutable candidate used by production; it enables JVM tests without fake Android Intents.
 * No preflight resolveActivity: package visibility must not prevent an otherwise valid dispatch.
 */
fun launchActionSafely(
    context: Context,
    dto: AssistantActionDto,
    onError: (String) -> Unit = {},
    launchCandidate: (ActionIntentCandidate) -> Unit = { context.startActivity(it.toIntent()) },
): Boolean {
    val payload = parseActionPayload(dto)
    val candidates = payload?.let(::buildActionCandidates).orEmpty()
    for ((index, candidate) in candidates.withIndex()) {
        val prepared = candidate.copy(flags = candidate.flags or
            if (context is Activity) 0 else Intent.FLAG_ACTIVITY_NEW_TASK)
        try {
            launchCandidate(prepared)
            return true
        } catch (exception: RuntimeException) {
            // Includes ActivityNotFoundException, SecurityException and framework Context failures.
            // Do not log exception messages, payload content, URI, title, or map query.
            Log.w("AssistantActions", "action=${dto.type} candidate=${index + 1} exception=${exception.javaClass.simpleName}")
        }
    }
    onError(actionLaunchError(dto.type))
    return false
}
