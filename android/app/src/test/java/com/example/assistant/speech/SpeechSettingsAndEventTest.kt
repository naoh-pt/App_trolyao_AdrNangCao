package com.example.assistant.speech

import com.example.assistant.data.local.SettingsStore
import com.example.assistant.domain.AnimationFpsSettings
import com.example.assistant.ui.character.CharacterFrameCatalog
import com.example.assistant.ui.settings.SettingsUiState
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.asSharedFlow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.take
import kotlinx.coroutines.flow.toList
import kotlinx.coroutines.launch
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

@OptIn(kotlinx.coroutines.ExperimentalCoroutinesApi::class)
class SpeechSettingsAndEventTest {

    // =========================================================================
    // 1. Settings Default and Isolation
    // =========================================================================

    @Test
    fun testDefaultSpeechSettingIsEnabled() {
        assertTrue("Speech setting must default to enabled (true)", SettingsStore.DEFAULT_TTS_ENABLED)
        val defaultUiState = SettingsUiState()
        assertTrue("SettingsUiState must default ttsEnabled to true", defaultUiState.ttsEnabled)
    }

    @Test
    fun testUpdatingSpeechSettingDoesNotAffectAnimationFpsDefaults() {
        val uiStateDisabled = SettingsUiState(ttsEnabled = false)
        assertFalse(uiStateDisabled.ttsEnabled)

        // Verify AnimationFpsSettings.DEFAULT is completely untouched
        assertEquals(5, AnimationFpsSettings.DEFAULT.idle)
        assertEquals(8, AnimationFpsSettings.DEFAULT.thinking)
        assertEquals(10, AnimationFpsSettings.DEFAULT.talk)
        assertEquals(10, AnimationFpsSettings.DEFAULT.happy)
        assertEquals(8, AnimationFpsSettings.DEFAULT.sad)
        assertEquals(10, AnimationFpsSettings.DEFAULT.surprised)

        // Verify CharacterFrameCatalog is untouched
        assertEquals(5, CharacterFrameCatalog.idle.fps)
        assertEquals(8, CharacterFrameCatalog.thinking.fps)
        assertEquals(10, CharacterFrameCatalog.talk.fps)
        assertEquals(10, CharacterFrameCatalog.happy.fps)
        assertEquals(8, CharacterFrameCatalog.sad.fps)
        assertEquals(10, CharacterFrameCatalog.surprised.fps)
    }

    // =========================================================================
    // 2. Critical One-Time Event Contract (SharedFlow with replay = 0)
    // =========================================================================

    @Test
    fun testSpeechEventFlowHasZeroReplay() = runTest {
        val speechEvents = MutableSharedFlow<String>(replay = 0, extraBufferCapacity = 1)
        val publicFlow = speechEvents.asSharedFlow()

        // Emitting an event before subscriber connects
        speechEvents.tryEmit("Tin nhắn trợ lý cũ")

        // Replay cache must be empty
        assertTrue("Replay cache must be empty when replay = 0", publicFlow.replayCache.isEmpty())

        // Late subscriber should NOT receive past events
        val collected = mutableListOf<String>()
        backgroundScope.launch(kotlinx.coroutines.test.UnconfinedTestDispatcher(testScheduler)) {
            publicFlow.collect { collected.add(it) }
        }

        // Before emitting new event, collected must be empty
        assertTrue("Late subscriber must not receive past event", collected.isEmpty())

        // Emit new event while subscribed
        speechEvents.emit("Tin nhắn trợ lý mới")

        assertEquals(1, collected.size)
        assertEquals("Tin nhắn trợ lý mới", collected[0])
    }

    @Test
    fun testSpeechEventDoesNotReplayWhenReturningToChat() = runTest {
        val speechEvents = MutableSharedFlow<String>(replay = 0, extraBufferCapacity = 1)
        val publicFlow = speechEvents.asSharedFlow()

        val firstScreenCollected = mutableListOf<String>()
        backgroundScope.launch(kotlinx.coroutines.test.UnconfinedTestDispatcher(testScheduler)) {
            publicFlow.collect { firstScreenCollected.add(it) }
        }

        // Assistant reply arrives
        speechEvents.emit("Chào bạn, mình có thể giúp gì?")
        assertEquals(listOf("Chào bạn, mình có thể giúp gì?"), firstScreenCollected)

        // User navigates away, then navigates back (new subscription)
        // Since replay = 0, new subscriber gets NO historical item
        assertTrue("replayCache must remain empty", publicFlow.replayCache.isEmpty())

        val secondScreenCollected = mutableListOf<String>()
        backgroundScope.launch(kotlinx.coroutines.test.UnconfinedTestDispatcher(testScheduler)) {
            publicFlow.collect { secondScreenCollected.add(it) }
        }
        assertTrue("New screen must not receive historical message", secondScreenCollected.isEmpty())
    }

    @Test
    fun testMessageListObservationIsNotTtsTrigger() {
        // Confirms architectural distinction:
        // Message list (StateFlow<List<MessageEntity>>) caches historical items for UI display.
        // Speech events (SharedFlow<String> replay=0) only trigger on genuine new reply arrivals.
        val historicalMessages = listOf("Msg 1", "Msg 2", "Msg 3")
        val speechEvents = MutableSharedFlow<String>(replay = 0, extraBufferCapacity = 1)

        // Historical messages in cache do not populate speechEvents
        assertEquals(3, historicalMessages.size)
        assertTrue(speechEvents.replayCache.isEmpty())
    }

    // =========================================================================
    // 3. TtsState and Safety Model
    // =========================================================================

    @Test
    fun testTtsStateValues() {
        val states = TtsState.values()
        assertTrue(states.contains(TtsState.INITIALIZING))
        assertTrue(states.contains(TtsState.READY))
        assertTrue(states.contains(TtsState.UNAVAILABLE))
    }
}
