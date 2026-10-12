package com.example.assistant.ui.chat

import android.app.Activity
import android.content.ContextWrapper
import android.content.Intent
import com.example.assistant.data.remote.AssistantActionDto
import com.example.assistant.domain.AnimationFpsSettings
import com.example.assistant.domain.CharacterState
import com.example.assistant.domain.Emotion
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * Unit tests for Stage 11:
 * 1. Emotion animation full frame lifecycle and watchdog calculations.
 * 2. Allowlisted assistant action payload parsing, validation, and labels.
 * 3. Context launch preparation (FLAG_ACTIVITY_NEW_TASK), Map/Calendar URL builders, and web fallbacks.
 */
class Stage11AssistantActionsAndEmotionTest {

    // =========================================================================
    // 1. Emotion Animation Lifecycle & Watchdog Tests
    // =========================================================================

    @Test
    fun testEmotionLongerThan1000MsNotCutOffAt1000Ms() {
        val happyWatchdog = calculateEmotionWatchdogDurationMs(Emotion.HAPPY)
        val sadWatchdog = calculateEmotionWatchdogDurationMs(Emotion.SAD)
        val surprisedWatchdog = calculateEmotionWatchdogDurationMs(Emotion.SURPRISED)

        // happy: 15 frames @ 10 FPS = 1500ms + 400ms margin = 1900ms > 1000ms
        assertTrue("Happy watchdog ($happyWatchdog ms) must exceed old 1000ms cutoff", happyWatchdog > 1000L)
        assertEquals(1900L, happyWatchdog)

        // sad: 21 frames @ 8 FPS = 2625ms + 400ms margin = 3025ms > 1000ms
        assertTrue("Sad watchdog ($sadWatchdog ms) must exceed old 1000ms cutoff", sadWatchdog > 1000L)
        assertEquals(3025L, sadWatchdog)

        // surprised: 23 frames @ 10 FPS = 2300ms + 400ms margin = 2700ms > 1000ms
        assertTrue("Surprised watchdog ($surprisedWatchdog ms) must exceed old 1000ms cutoff", surprisedWatchdog > 1000L)
        assertEquals(2700L, surprisedWatchdog)
    }

    @Test
    fun testSlowConfiguredFpsAllowsCompleteSequence() {
        // Slow FPS: happy at 4 FPS (15 frames @ 4 FPS = 3750ms + 400ms = 4150ms)
        val slowFps = AnimationFpsSettings.DEFAULT.withFps("happy", 4)
        val slowHappyWatchdog = calculateEmotionWatchdogDurationMs(Emotion.HAPPY, slowFps)
        assertEquals(4150L, slowHappyWatchdog)

        // Slow FPS: sad at 4 FPS (21 frames @ 4 FPS = 5250ms + 400ms = 5650ms)
        val slowSadFps = AnimationFpsSettings.DEFAULT.withFps("sad", 4)
        val slowSadWatchdog = calculateEmotionWatchdogDurationMs(Emotion.SAD, slowSadFps)
        assertEquals(5650L, slowSadWatchdog)
    }

    @Test
    fun testNeutralReturnsDirectlyToIdle() {
        // 1. Watchdog for neutral is 0ms (no watchdog needed)
        val neutralWatchdog = calculateEmotionWatchdogDurationMs(Emotion.NEUTRAL)
        assertEquals(0L, neutralWatchdog)

        // 2. Coordinator onSpeechCompleted returns directly to IDLE for neutral
        val coord = SpeechAnimationCoordinator()
        coord.onUserSendMessage()
        coord.onReplyReceived("utt-n", Emotion.NEUTRAL, ttsEnabled = true)
        coord.onSpeechStarted("utt-n")
        coord.onSpeechCompleted("utt-n")
        assertEquals(CharacterState.IDLE, coord.characterState)
        assertEquals(Emotion.NEUTRAL, coord.emotion)

        // 3. Coordinator onReplyReceived without TTS returns directly to IDLE for neutral
        val coordNoTts = SpeechAnimationCoordinator()
        coordNoTts.onUserSendMessage()
        coordNoTts.onReplyReceived("utt-no-tts", Emotion.NEUTRAL, ttsEnabled = false)
        assertEquals(CharacterState.IDLE, coordNoTts.characterState)
        assertEquals(Emotion.NEUTRAL, coordNoTts.emotion)
    }

    @Test
    fun testCompletionCallbackTransitionsToIdle() {
        val nonNeutral = listOf(Emotion.HAPPY, Emotion.SAD, Emotion.SURPRISED)
        for (emotion in nonNeutral) {
            val state = ChatUiState(
                characterState = CharacterState.TALKING,
                emotion = emotion,
            )
            assertTrue(canHandleAnimationFinished(state.characterState, state.emotion))
            val reduced = state.reduceAnimationFinished()
            assertEquals(CharacterState.IDLE, reduced.characterState)
            assertEquals(Emotion.NEUTRAL, reduced.emotion)
        }
    }

    @Test
    fun testStaleCompletionCallbackIsIgnored() {
        // When state has already moved to THINKING (user sent next message)
        val thinkingState = ChatUiState(
            characterState = CharacterState.THINKING,
            emotion = Emotion.NEUTRAL,
            sending = true,
        )
        assertFalse(canHandleAnimationFinished(thinkingState.characterState, thinkingState.emotion))
        assertEquals(thinkingState, thinkingState.reduceAnimationFinished())

        // When state is already IDLE
        val idleState = ChatUiState(
            characterState = CharacterState.IDLE,
            emotion = Emotion.NEUTRAL,
        )
        assertFalse(canHandleAnimationFinished(idleState.characterState, idleState.emotion))
        assertEquals(idleState, idleState.reduceAnimationFinished())
    }

    @Test
    fun testCancellationAndNewRequestRestoresCorrectState() {
        val coord = SpeechAnimationCoordinator()
        coord.onUserSendMessage()
        coord.onReplyReceived("utt-1", Emotion.HAPPY, ttsEnabled = true)
        coord.onSpeechStarted("utt-1")
        assertEquals(CharacterState.TALKING, coord.characterState)

        // User sends another message before speech/emotion completes
        coord.onUserSendMessage()
        assertEquals(CharacterState.THINKING, coord.characterState)
        assertEquals(Emotion.NEUTRAL, coord.emotion)
        assertNull(coord.activeUtteranceId)

        // Reset restores initial IDLE state
        coord.onReset()
        assertEquals(CharacterState.IDLE, coord.characterState)
        assertEquals(Emotion.NEUTRAL, coord.emotion)
    }

    // =========================================================================
    // 2. Assistant Action Parsing & Label Tests
    // =========================================================================

    @Test
    fun testTimerActionParsing() {
        val dto = AssistantActionDto(
            type = "set_timer",
            label = "Đặt hẹn giờ 5 phút",
            message = "Học bài",
            durationSeconds = 300,
        )
        val payload = parseActionPayload(dto)
        assertNotNull(payload)
        assertTrue(payload is AssistantActionPayload.SetTimer)
        val timerPayload = payload as AssistantActionPayload.SetTimer
        assertEquals("Học bài", timerPayload.message)
        assertEquals(300, timerPayload.durationSeconds)
        assertEquals("Đặt hẹn giờ 5 phút", actionButtonLabel(dto))
    }

    @Test
    fun testCalendarActionParsing() {
        val dto = AssistantActionDto(
            type = "create_calendar_event",
            label = "Mở lịch để xác nhận",
            title = "Học Android",
            startAt = "2026-10-10T20:00:00+07:00",
            endAt = "2026-10-10T20:30:00+07:00",
        )
        val payload = parseActionPayload(dto)
        assertNotNull(payload)
        assertTrue(payload is AssistantActionPayload.CreateCalendarEvent)
        val calPayload = payload as AssistantActionPayload.CreateCalendarEvent
        assertEquals("Học Android", calPayload.title)
        assertTrue(calPayload.startMillis > 0L)
        assertTrue(calPayload.endMillis > calPayload.startMillis)
        assertEquals("Mở lịch để xác nhận", actionButtonLabel(dto))
    }

    @Test
    fun testMapSearchActionParsing() {
        val dto = AssistantActionDto(
            type = "map_search",
            label = "Mở bản đồ",
            query = "Học viện Kỹ thuật Mật mã",
        )
        val payload = parseActionPayload(dto)
        assertNotNull(payload)
        assertTrue(payload is AssistantActionPayload.MapSearch)
        val mapPayload = payload as AssistantActionPayload.MapSearch
        assertEquals("Học viện Kỹ thuật Mật mã", mapPayload.query)
        assertEquals("Mở bản đồ", actionButtonLabel(dto))
    }

    @Test
    fun testUnknownOrMalformedActionsIgnoredSafely() {
        // Unknown type
        val unknownDto = AssistantActionDto(type = "arbitrary_app_launch", label = "Khởi chạy")
        assertNull(parseActionPayload(unknownDto))

        // Timer with null duration
        val badTimer = AssistantActionDto(type = "set_timer", label = "Hẹn giờ", durationSeconds = null)
        assertNull(parseActionPayload(badTimer))

        // Timer with zero duration
        val zeroTimer = AssistantActionDto(type = "set_timer", label = "Hẹn giờ", durationSeconds = 0)
        assertNull(parseActionPayload(zeroTimer))

        // Calendar with null startAt
        val badCal = AssistantActionDto(type = "create_calendar_event", label = "Lịch", startAt = null)
        assertNull(parseActionPayload(badCal))

        // Map with blank query
        val blankMap = AssistantActionDto(type = "map_search", label = "Bản đồ", query = "   ")
        assertNull(parseActionPayload(blankMap))
    }

    @Test
    fun testDefaultActionButtonLabelsWhenEmpty() {
        val timer = AssistantActionDto(type = "set_timer", label = "")
        assertEquals("Đặt hẹn giờ", actionButtonLabel(timer))

        val cal = AssistantActionDto(type = "create_calendar_event", label = "")
        assertEquals("Mở lịch để xác nhận", actionButtonLabel(cal))

        val map = AssistantActionDto(type = "map_search", label = "")
        assertEquals("Mở bản đồ", actionButtonLabel(map))
    }

    // =========================================================================
    // 3. Stage 11 Compatibility Fix Tests (Context, Fallbacks & Safety)
    // =========================================================================

    @Test
    fun testNonActivityContextAddsNewTaskFlag() {
        val nonActivityContext = object : ContextWrapper(null) {}
        val testIntent = object : Intent() {
            var flagsAdded: Int = 0
            override fun addFlags(flags: Int): Intent {
                flagsAdded = flagsAdded or flags
                return this
            }
        }
        prepareForContext(nonActivityContext, testIntent)
        assertTrue(
            "FLAG_ACTIVITY_NEW_TASK must be added for non-Activity Context",
            (testIntent.flagsAdded and Intent.FLAG_ACTIVITY_NEW_TASK) != 0,
        )
    }

    @Test
    fun testActivityContextDoesNotAddUnnecessaryNewTaskFlag() {
        val activityContext = object : Activity() {}
        val testIntent = object : Intent() {
            var flagsAdded: Int = 0
            override fun addFlags(flags: Int): Intent {
                flagsAdded = flagsAdded or flags
                return this
            }
        }
        prepareForContext(activityContext, testIntent)
        assertEquals(
            "FLAG_ACTIVITY_NEW_TASK must NOT be added when Activity context is available",
            0,
            testIntent.flagsAdded and Intent.FLAG_ACTIVITY_NEW_TASK,
        )
    }

    @Test
    fun testMapPrimaryIntentRemainsGeo() {
        val query = "Hồ Gươm"
        val geoUri = buildMapGeoUri(query)
        assertTrue("Map primary URI must use geo: scheme", geoUri.startsWith("geo:0,0?q="))
        val expectedEncoded = encodeUriComponent(query)
        assertTrue("Query must be percent-encoded", geoUri.contains(expectedEncoded))
        assertTrue("Percent encoding must encode Vietnamese characters", expectedEncoded.contains("%"))
        assertFalse("Percent encoding must not contain raw spaces", expectedEncoded.contains(" "))

        val payload = parseActionPayload(AssistantActionDto(type = "map_search", query = query)) as AssistantActionPayload.MapSearch
        assertEquals(query, payload.query)
    }

    @Test
    fun testMapBrowserFallbackUrlAndHost() {
        val query = "Hồ Gươm Hà Nội"
        val fallbackUrl = buildMapWebSearchUrl(query)
        assertTrue(
            "Map browser fallback must use official Google Maps HTTPS search endpoint",
            fallbackUrl.startsWith("https://www.google.com/maps/search/?api=1&query="),
        )
        val expectedEncoded = encodeUriComponent(query)
        assertTrue(
            "Query parameters must be percent-encoded",
            fallbackUrl.contains(expectedEncoded),
        )
        assertTrue("Percent encoding must encode Vietnamese characters", expectedEncoded.contains("%"))
        assertFalse("Percent encoding must not contain raw spaces", expectedEncoded.contains(" "))
    }

    @Test
    fun testCalendarNativeIntentRemainsPrimaryAction() {
        val dto = AssistantActionDto(
            type = "create_calendar_event",
            title = "Họp nhóm",
            startAt = "2026-10-10T14:00:00+07:00",
            endAt = "2026-10-10T14:30:00+07:00",
        )
        val payload = parseActionPayload(dto)
        assertNotNull(payload)
        assertTrue(payload is AssistantActionPayload.CreateCalendarEvent)
        val calPayload = payload as AssistantActionPayload.CreateCalendarEvent
        assertEquals("Họp nhóm", calPayload.title)
        assertTrue(calPayload.startMillis > 0L)
        assertEquals(calPayload.startMillis + 30 * 60 * 1000L, calPayload.endMillis)
    }

    @Test
    fun testCalendarBrowserFallbackContainsUtcFormattedDatesAndDetails() {
        // 2026-10-10 14:00:00 UTC+7 is 2026-10-10 07:00:00 UTC
        val startMillis = java.time.Instant.parse("2026-10-10T07:00:00Z").toEpochMilli()
        val endMillis = startMillis + 30 * 60 * 1000L // 2026-10-10T07:30:00Z

        val formattedStart = formatUtcCalendarDate(startMillis)
        val formattedEnd = formatUtcCalendarDate(endMillis)
        assertEquals("20261010T070000Z", formattedStart)
        assertEquals("20261010T073000Z", formattedEnd)

        val fallbackUrl = buildCalendarWebTemplateUrl(
            title = "Học Android",
            startMillis = startMillis,
            endMillis = endMillis,
        )

        assertTrue(
            "Fallback URL must point to Google Calendar web template render",
            fallbackUrl.startsWith("https://calendar.google.com/calendar/render?action=TEMPLATE"),
        )
        val expectedTitleEncoded = encodeUriComponent("Học Android")
        val expectedDescEncoded = encodeUriComponent("Được tạo bởi trợ lý ảo Anna")
        assertTrue("URL must contain URI-encoded title", fallbackUrl.contains("text=$expectedTitleEncoded"))
        assertTrue("URL must contain dates=START/END", fallbackUrl.contains("dates=20261010T070000Z/20261010T073000Z"))
        assertTrue(
            "URL must contain URI-encoded default description",
            fallbackUrl.contains("details=$expectedDescEncoded"),
        )
    }

    @Test
    fun testNoActionLaunchedAutomatically() {
        // Parsing DTOs produces pure immutable data models without executing any system Intents
        val timerDto = AssistantActionDto(type = "set_timer", durationSeconds = 60)
        val calDto = AssistantActionDto(type = "create_calendar_event", startAt = "2026-10-10T10:00:00+07:00")
        val mapDto = AssistantActionDto(type = "map_search", query = "Hà Nội")

        val timerPayload = parseActionPayload(timerDto)
        val calPayload = parseActionPayload(calDto)
        val mapPayload = parseActionPayload(mapDto)

        assertNotNull(timerPayload)
        assertNotNull(calPayload)
        assertNotNull(mapPayload)

        // Actions remain strictly inert until an explicit user button press invokes launchActionSafely
    }
}
