package com.example.assistant.ui.chat

import android.app.Activity
import android.content.ActivityNotFoundException
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.provider.AlarmClock
import android.provider.CalendarContract
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
    return "geo:0,0?q=${encodeUriComponent(query)}"
}

/** Builds the safe Google Maps HTTPS web search URL for map searches. */
fun buildMapWebSearchUrl(query: String): String {
    return "$MAP_WEB_SEARCH_BASE_URL${encodeUriComponent(query)}"
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
        if (startMillis != null) {
            val endMillis = parseIsoTimestampToMillis(dto.endAt) ?: (startMillis + 30 * 60 * 1000L)
            val title = if (!dto.title.isNullOrBlank()) dto.title.trim() else "Sự kiện mới"
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
        val q = dto.query?.trim()
        if (!q.isNullOrBlank()) {
            AssistantActionPayload.MapSearch(query = q)
        } else {
            null
        }
    }

    else -> null
}

/**
 * Pure function building the primary Android [Intent] for a validated [AssistantActionPayload].
 * Uses strictly hardcoded safe intents and never launches arbitrary packages or URIs.
 */
fun buildActionIntent(payload: AssistantActionPayload): Intent = when (payload) {
    is AssistantActionPayload.SetTimer -> {
        Intent(AlarmClock.ACTION_SET_TIMER).apply {
            putExtra(AlarmClock.EXTRA_MESSAGE, payload.message)
            putExtra(AlarmClock.EXTRA_LENGTH, payload.durationSeconds)
            putExtra(AlarmClock.EXTRA_SKIP_UI, true)
        }
    }

    is AssistantActionPayload.CreateCalendarEvent -> {
        Intent(Intent.ACTION_INSERT).apply {
            data = CalendarContract.Events.CONTENT_URI
            putExtra(CalendarContract.Events.TITLE, payload.title)
            putExtra(CalendarContract.EXTRA_EVENT_BEGIN_TIME, payload.startMillis)
            putExtra(CalendarContract.EXTRA_EVENT_END_TIME, payload.endMillis)
            putExtra(CalendarContract.Events.DESCRIPTION, CALENDAR_DEFAULT_DESCRIPTION)
        }
    }

    is AssistantActionPayload.MapSearch -> {
        Intent(Intent.ACTION_VIEW, Uri.parse(buildMapGeoUri(payload.query)))
    }
}

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

/**
 * Safely launches the Android system activity associated with [dto].
 * Returns true if an intent was dispatched, false if unsupported or no compatible app was found.
 * Never crashes; invokes [onError] with a friendly Vietnamese message on failure.
 *
 * Fallback behavior:
 * - MapSearch: tries primary "geo:" intent; on ActivityNotFoundException, falls back to Google Maps web URL.
 * - CreateCalendarEvent: tries primary Calendar ACTION_INSERT intent; on ActivityNotFoundException, falls back to Google Calendar web template URL.
 * - SetTimer: tries Clock ACTION_SET_TIMER.
 * All intents are passed through [prepareForContext] to guarantee safe execution regardless of Context type.
 */
fun launchActionSafely(
    context: Context,
    dto: AssistantActionDto,
    onError: (String) -> Unit = {},
): Boolean {
    val payload = parseActionPayload(dto)
    if (payload == null) {
        onError("Hành động không hợp lệ hoặc dữ liệu bị thiếu.")
        return false
    }

    return when (payload) {
        is AssistantActionPayload.SetTimer -> {
            val intent = try {
                prepareForContext(context, buildActionIntent(payload))
            } catch (e: Exception) {
                onError("Không thể tạo tác vụ: ${e.message}")
                return false
            }
            try {
                context.startActivity(intent)
                true
            } catch (e: ActivityNotFoundException) {
                onError("Không tìm thấy ứng dụng hẹn giờ trên thiết bị.")
                false
            } catch (e: Exception) {
                onError("Không thể thực hiện tác vụ: ${e.message}")
                false
            }
        }

        is AssistantActionPayload.MapSearch -> {
            val primaryIntent = try {
                prepareForContext(context, buildActionIntent(payload))
            } catch (e: Exception) {
                onError("Không thể tạo tác vụ: ${e.message}")
                return false
            }
            try {
                context.startActivity(primaryIntent)
                true
            } catch (e: ActivityNotFoundException) {
                // Primary geo: intent failed, try safe browser fallback
                try {
                    val fallbackIntent = prepareForContext(
                        context,
                        buildMapWebFallbackIntent(payload.query),
                    )
                    context.startActivity(fallbackIntent)
                    true
                } catch (fallbackEx: ActivityNotFoundException) {
                    onError("Không tìm thấy ứng dụng bản đồ trên thiết bị.")
                    false
                } catch (fallbackEx: Exception) {
                    onError("Không thể mở bản đồ: ${fallbackEx.message}")
                    false
                }
            } catch (e: Exception) {
                onError("Không thể thực hiện tác vụ: ${e.message}")
                false
            }
        }

        is AssistantActionPayload.CreateCalendarEvent -> {
            val primaryIntent = try {
                prepareForContext(context, buildActionIntent(payload))
            } catch (e: Exception) {
                onError("Không thể tạo tác vụ: ${e.message}")
                return false
            }
            try {
                context.startActivity(primaryIntent)
                true
            } catch (e: ActivityNotFoundException) {
                // Primary Calendar ACTION_INSERT failed, try safe Google Calendar web template fallback
                try {
                    val fallbackIntent = prepareForContext(
                        context,
                        buildCalendarWebFallbackIntent(
                            title = payload.title,
                            startMillis = payload.startMillis,
                            endMillis = payload.endMillis,
                        ),
                    )
                    context.startActivity(fallbackIntent)
                    true
                } catch (fallbackEx: ActivityNotFoundException) {
                    onError("Không tìm thấy ứng dụng lịch trên thiết bị.")
                    false
                } catch (fallbackEx: Exception) {
                    onError("Không thể mở lịch: ${fallbackEx.message}")
                    false
                }
            } catch (e: Exception) {
                onError("Không thể thực hiện tác vụ: ${e.message}")
                false
            }
        }
    }
}
