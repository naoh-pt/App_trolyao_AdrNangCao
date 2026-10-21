package com.example.assistant.ui.chat

import android.app.Activity
import android.content.ActivityNotFoundException
import android.content.ContextWrapper
import android.content.Intent
import android.provider.AlarmClock
import android.provider.CalendarContract
import com.example.assistant.data.remote.AssistantActionDto
import org.junit.Assert.*
import org.junit.Test
import java.net.URLDecoder
import java.time.Instant

/** Tests the same immutable candidates and ordered dispatch loop used on the phone.
 * Framework Intent getters are no-op Android JVM stubs, so assertions use the production plan.
 */
class ExternalActionLaunchingTest {
    private val activity = object : Activity() {}
    private val applicationContext = object : ContextWrapper(null) {}
    private val calendar = AssistantActionDto(
        type = AssistantActionTypes.CREATE_CALENDAR_EVENT,
        title = "Học Android",
        startAt = "2026-10-22T20:00:00+07:00",
        endAt = "2026-10-22T20:30:00+07:00",
    )
    private val map = AssistantActionDto(type = AssistantActionTypes.MAP_SEARCH, query = "Học viện Kỹ thuật Mật mã.")
    private val timer = AssistantActionDto(type = AssistantActionTypes.SET_TIMER, durationSeconds = 300, message = "Học bài")

    private fun candidates(dto: AssistantActionDto) = buildActionCandidates(requireNotNull(parseActionPayload(dto)))

    @Test fun calendarInsertHasCorrectUriTitleTimesAndDescription() {
        val first = candidates(calendar).first()
        assertEquals(Intent.ACTION_INSERT, first.action)
        assertEquals("content://com.android.calendar/events", first.dataUri)
        assertEquals("Học Android", first.extras[CalendarContract.Events.TITLE])
        assertEquals(Instant.parse("2026-10-22T13:00:00Z").toEpochMilli(), first.extras[CalendarContract.EXTRA_EVENT_BEGIN_TIME])
        assertEquals(Instant.parse("2026-10-22T13:30:00Z").toEpochMilli(), first.extras[CalendarContract.EXTRA_EVENT_END_TIME])
        assertEquals("Được tạo bởi trợ lý ảo Anna", first.extras[CalendarContract.Events.DESCRIPTION])
    }

    @Test fun calendarFallsBackToEditWithSameSafeExtrasThenDateView() {
        val plan = candidates(calendar)
        assertEquals(3, plan.size)
        assertEquals(Intent.ACTION_EDIT, plan[1].action)
        assertEquals(plan[0].dataUri, plan[1].dataUri)
        assertEquals(plan[0].extras, plan[1].extras)
        assertEquals(Intent.ACTION_VIEW, plan[2].action)
        assertEquals("content://com.android.calendar/time/${parseIsoTimestampToMillis(calendar.startAt)}", plan[2].dataUri)
        assertEquals(plan[0].extras, plan[2].extras)
    }

    @Test fun calendarCandidateConstructionDoesNotDispatchOrSaveAnEvent() {
        val plan = candidates(calendar)
        assertEquals(listOf(Intent.ACTION_INSERT, Intent.ACTION_EDIT, Intent.ACTION_VIEW), plan.map { it.action })
        // No provider writes, event ID, skip-UI, or auto-save instruction exists in this plan.
        assertTrue(plan.all { it.extras.keys == setOf(
            CalendarContract.Events.TITLE, CalendarContract.EXTRA_EVENT_BEGIN_TIME,
            CalendarContract.EXTRA_EVENT_END_TIME, CalendarContract.Events.DESCRIPTION,
        ) })
        assertEquals("content://com.android.calendar/events", plan[1].dataUri)
    }

    @Test fun calendarRejectsBlankOrMissingTitle() {
        assertNull(parseActionPayload(calendar.copy(title = "  ")))
        assertNull(parseActionPayload(calendar.copy(title = null)))
    }

    @Test fun calendarRejectsInvalidStartAndExplicitInvalidEnd() {
        for (bad in listOf("", "invalid", "2026-10-22T20:00:00", "https://example.org")) {
            assertNull(parseActionPayload(calendar.copy(startAt = bad)))
            assertNull(parseActionPayload(calendar.copy(endAt = bad)))
        }
        assertNull(parseActionPayload(calendar.copy(startAt = null)))
    }

    @Test fun calendarRejectsEndBeforeOrEqualToStart() {
        assertNull(parseActionPayload(calendar.copy(endAt = calendar.startAt)))
        assertNull(parseActionPayload(calendar.copy(endAt = "2026-10-22T19:59:00+07:00")))
    }

    @Test fun calendarAbsentEndRetainsThirtyMinuteDefault() {
        val payload = parseActionPayload(calendar.copy(endAt = null)) as AssistantActionPayload.CreateCalendarEvent
        assertEquals(30 * 60 * 1000L, payload.endMillis - payload.startMillis)
    }

    @Test fun calendarTrimsTitleWithoutChangingItsContent() {
        assertEquals("Học Android", candidates(calendar.copy(title = "  Học Android  ")).first().extras[CalendarContract.Events.TITLE])
    }

    @Test fun directMalformedPayloadCannotProduceCalendarCandidates() {
        assertTrue(buildActionCandidates(AssistantActionPayload.CreateCalendarEvent("", 10, 20)).isEmpty())
        assertTrue(buildActionCandidates(AssistantActionPayload.CreateCalendarEvent("Học", 20, 10)).isEmpty())
    }

    @Test fun mapsUseGeoThenHttpsWithoutRestrictingAProviderPackage() {
        val plan = candidates(map)
        assertEquals(2, plan.size)
        assertTrue(plan.all { it.action == Intent.ACTION_VIEW && it.extras.isEmpty() })
        assertTrue(plan[0].dataUri!!.startsWith("geo:0,0?q="))
        assertTrue(plan[1].dataUri!!.startsWith("https://www.google.com/maps/search/?api=1&query="))
        // Candidates have only action/data/extras/flags: no package/component override is carried.
        assertFalse(plan.toString().contains("com.google.android.apps.maps"))
    }

    @Test fun vietnameseQueriesAreUtf8EncodedAndTerminalPeriodRemoved() {
        val plan = candidates(map)
        val query = "Học viện Kỹ thuật Mật mã"
        assertEquals("geo:0,0?q=${encodeUriComponent(query)}", plan[0].dataUri)
        assertEquals("https://www.google.com/maps/search/?api=1&query=${encodeUriComponent(query)}", plan[1].dataUri)
        assertEquals(query, URLDecoder.decode(plan[0].dataUri!!.substringAfter("q="), "UTF-8"))
        assertTrue(plan[0].dataUri!!.contains("%E1%BB%8Dc"))
        assertFalse(plan[0].dataUri!!.contains(" "))
    }

    @Test fun trailingConversationalPunctuationAndWhitespaceAreRemoved() {
        for (suffix in listOf(".", "?!", "!!!", ";:", ",", " . ! ? ")) {
            val payload = parseActionPayload(map.copy(query = "  Hồ Gươm$suffix  ")) as AssistantActionPayload.MapSearch
            assertEquals("Hồ Gươm", payload.query)
        }
    }

    @Test fun internalPunctuationIsPreserved() {
        val name = "Bảo tàng A:B, C-D & St. John's (Q.1)"
        assertEquals(name, cleanMapQuery(" $name! "))
        assertEquals("Washington, D.C.", cleanMapQuery("Washington, D.C.!"))
    }

    @Test fun queryDelimitersRemainEncodedLocationText() {
        val name = "A & B #1/2 + C"
        val uri = candidates(map.copy(query = name)).first().dataUri!!
        assertEquals(name, URLDecoder.decode(uri.substringAfter("q="), "UTF-8"))
        assertFalse(uri.contains("&"))
        assertFalse(uri.contains("#"))
        assertFalse(uri.contains("+"))
    }

    @Test fun mapsRejectBlankAndPunctuationOnlyQuery() {
        for (query in listOf(null, "", "  ", "... ?!,;: ")) {
            assertNull(parseActionPayload(map.copy(query = query)))
        }
    }

    @Test fun rawUnsafeSchemesCannotBecomeMapDestinations() {
        for (query in listOf("javascript:alert(1)", "file:/private", "intent:foo", "content:private", "data:text/plain,hi", "custom://foo", "https://example.org", "geo:1,2")) {
            assertNull(parseActionPayload(map.copy(query = query)))
            assertTrue(buildActionCandidates(AssistantActionPayload.MapSearch(query)).isEmpty())
        }
    }

    @Test fun firstCandidateSuccessStopsAllFurtherAttempts() {
        val attempts = mutableListOf<ActionIntentCandidate>()
        val errors = mutableListOf<String>()
        assertTrue(launchActionSafely(activity, map, errors::add, attempts::add))
        assertEquals(listOf(candidates(map).first()), attempts)
        assertTrue(errors.isEmpty())
    }

    @Test fun missingNativeMapHandlerFallsBackToHttps() {
        val attempts = mutableListOf<ActionIntentCandidate>()
        assertTrue(launchActionSafely(activity, map, { fail(it) }) {
            attempts += it
            if (attempts.size == 1) throw ActivityNotFoundException()
        })
        assertEquals(candidates(map), attempts)
    }

    @Test fun unsupportedInsertTriesEditAndStopsOnSuccess() {
        val attempts = mutableListOf<ActionIntentCandidate>()
        assertTrue(launchActionSafely(activity, calendar, { fail(it) }) {
            attempts += it
            if (attempts.size == 1) throw ActivityNotFoundException()
        })
        assertEquals(listOf(Intent.ACTION_INSERT, Intent.ACTION_EDIT), attempts.map { it.action })
    }

    @Test fun calendarTriesDateViewAfterBothEditorCandidatesFail() {
        val attempts = mutableListOf<ActionIntentCandidate>()
        assertTrue(launchActionSafely(activity, calendar, { fail(it) }) {
            attempts += it
            if (attempts.size < 3) throw ActivityNotFoundException()
        })
        assertEquals(candidates(calendar), attempts)
    }

    @Test fun securityFailureDoesNotBlockNextSafeCandidate() {
        var attempts = 0
        assertTrue(launchActionSafely(activity, map, { fail(it) }) {
            attempts++
            if (attempts == 1) throw SecurityException("private exception detail")
        })
        assertEquals(2, attempts)
    }

    @Test fun runtimeContextFailureDoesNotCrashOrBlockFallback() {
        var attempts = 0
        assertTrue(launchActionSafely(applicationContext, map, { fail(it) }) {
            attempts++
            if (attempts == 1) throw IllegalStateException("private context detail")
        })
        assertEquals(2, attempts)
    }

    @Test fun allMapCandidatesFailWithExactlyOneFriendlyError() {
        val errors = mutableListOf<String>()
        var attempts = 0
        assertFalse(launchActionSafely(activity, map, errors::add) {
            attempts++
            throw ActivityNotFoundException()
        })
        assertEquals(2, attempts)
        assertEquals(listOf("Không thể mở ứng dụng bản đồ hoặc trình duyệt trên thiết bị."), errors)
    }

    @Test fun allCalendarCandidatesFailWithExactlyOneFriendlyError() {
        val errors = mutableListOf<String>()
        var attempts = 0
        assertFalse(launchActionSafely(activity, calendar, errors::add) {
            attempts++
            throw SecurityException("sensitive URI detail")
        })
        assertEquals(3, attempts)
        assertEquals(listOf("Không thể mở ứng dụng lịch trên thiết bị."), errors)
    }

    @Test fun timerKeepsPrimaryActionMessageDurationAndSkipUi() {
        val plan = candidates(timer)
        assertEquals(1, plan.size)
        assertEquals(AlarmClock.ACTION_SET_TIMER, plan[0].action)
        assertNull(plan[0].dataUri)
        assertEquals(mapOf(AlarmClock.EXTRA_MESSAGE to "Học bài", AlarmClock.EXTRA_LENGTH to 300,
            AlarmClock.EXTRA_SKIP_UI to true), plan[0].extras)
        var attempts = 0
        assertTrue(launchActionSafely(activity, timer, { fail(it) }) { attempts++ })
        assertEquals(1, attempts)
    }

    @Test fun timerFailureReportsExactlyOneFriendlyError() {
        val errors = mutableListOf<String>()
        assertFalse(launchActionSafely(activity, timer, errors::add) { throw ActivityNotFoundException() })
        assertEquals(listOf("Không tìm thấy ứng dụng hẹn giờ phù hợp trên thiết bị."), errors)
    }

    @Test fun nonActivityContextAddsNewTaskToEveryCandidateCopy() {
        val original = candidates(calendar)
        val attempts = mutableListOf<ActionIntentCandidate>()
        assertFalse(launchActionSafely(applicationContext, calendar, {}) {
            attempts += it
            throw ActivityNotFoundException()
        })
        assertEquals(3, attempts.size)
        assertTrue(attempts.all { it.flags and Intent.FLAG_ACTIVITY_NEW_TASK != 0 })
        assertTrue(original.all { it.flags == 0 })
        assertEquals(original, candidates(calendar))
    }

    @Test fun activityContextDoesNotAddNewTask() {
        assertTrue(launchActionSafely(activity, map, { fail(it) }) { assertEquals(0, it.flags) })
    }

    @Test fun oneTapCanProduceOnlyOneSuccessfulDispatch() {
        var attempts = 0
        var successes = 0
        assertTrue(launchActionSafely(activity, calendar, { fail(it) }) {
            attempts++
            if (attempts < 2) throw ActivityNotFoundException()
            successes++
        })
        assertEquals(2, attempts)
        assertEquals(1, successes)
    }

    @Test fun malformedPayloadReportsOnceAndDoesNotLaunch() {
        val errors = mutableListOf<String>()
        assertFalse(launchActionSafely(activity, calendar.copy(title = ""), errors::add) { fail("Invalid calendar must not launch") })
        assertEquals(listOf("Không thể mở ứng dụng lịch trên thiết bị."), errors)
    }

    @Test fun unknownActionCannotLaunchArbitraryIntent() {
        val errors = mutableListOf<String>()
        assertFalse(launchActionSafely(activity, AssistantActionDto(type = "javascript"), errors::add) { fail("Unknown action must not launch") })
        assertEquals(1, errors.size)
    }

    /** Recording framework adapter checks real setter calls despite JVM framework getters being stubs. */
    private class RecordingIntent : Intent() {
        val recordedExtras = mutableMapOf<String, Any?>()
        var recordedFlags = 0
        var packageAssigned = false
        override fun addFlags(flags: Int): Intent { recordedFlags = recordedFlags or flags; return this }
        override fun putExtra(name: String, value: String?): Intent { recordedExtras[name] = value; return this }
        override fun putExtra(name: String, value: Long): Intent { recordedExtras[name] = value; return this }
        override fun putExtra(name: String, value: Int): Intent { recordedExtras[name] = value; return this }
        override fun putExtra(name: String, value: Boolean): Intent { recordedExtras[name] = value; return this }
        override fun setPackage(packageName: String?): Intent { packageAssigned = true; return this }
    }

    @Test fun intentAdapterTransfersCalendarExtrasAndNewTaskFlag() {
        val candidate = candidates(calendar).first().copy(flags = Intent.FLAG_ACTIVITY_NEW_TASK)
        val recording = RecordingIntent()
        val intent = candidate.toIntent { action ->
            assertEquals(Intent.ACTION_INSERT, action)
            recording
        }
        assertSame(recording, intent)
        assertEquals(candidate.extras, recording.recordedExtras)
        assertEquals(Intent.FLAG_ACTIVITY_NEW_TASK, recording.recordedFlags)
        assertFalse(recording.packageAssigned)
    }

    @Test fun intentAdapterTransfersTimerIntBooleanAndMessageExtras() {
        val candidate = candidates(timer).first()
        val recording = RecordingIntent()
        candidate.toIntent { recording }
        assertEquals(candidate.extras, recording.recordedExtras)
        assertEquals(300, recording.recordedExtras[AlarmClock.EXTRA_LENGTH])
        assertEquals(true, recording.recordedExtras[AlarmClock.EXTRA_SKIP_UI])
    }

    @Test fun materializingSharedMapCandidateCreatesDistinctIntentsWithoutSettingPackage() {
        val candidate = candidates(map).first()
        val first = candidate.toIntent { RecordingIntent() } as RecordingIntent
        val second = candidate.toIntent { RecordingIntent() } as RecordingIntent
        assertNotSame(first, second)
        assertFalse(first.packageAssigned)
        assertFalse(second.packageAssigned)
        assertEquals(0, candidate.flags)
    }
}
