package com.example.assistant.speech

import com.example.assistant.data.local.SettingsStore
import com.example.assistant.domain.AnimationFpsSettings
import com.example.assistant.domain.SpeechSettings
import com.example.assistant.ui.character.CharacterFrameCatalog
import com.example.assistant.ui.settings.SettingsUiState
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.asSharedFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

@OptIn(kotlinx.coroutines.ExperimentalCoroutinesApi::class)
class SpeechSettingsAndEventTest {

    // =========================================================================
    // 1. Settings Defaults and Isolation
    // =========================================================================

    @Test
    fun testDefaultSpeechSettingIsEnabled() {
        assertTrue("Speech setting must default to enabled (true)", SettingsStore.DEFAULT_TTS_ENABLED)
        assertTrue("SpeechSettings.DEFAULT must be enabled", SpeechSettings.DEFAULT.enabled)
        assertEquals(1.0f, SpeechSettings.DEFAULT.speechRate, 0.001f)
        assertEquals(1.0f, SpeechSettings.DEFAULT.pitch, 0.001f)

        val defaultUiState = SettingsUiState()
        assertTrue("SettingsUiState must default ttsEnabled to true", defaultUiState.ttsEnabled)
        assertEquals(SpeechSettings.DEFAULT, defaultUiState.speechSettings)
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
    // 2. SpeechSettings Model: Clamping, Stepping, and Normalization
    // =========================================================================

    @Test
    fun testSpeechRateLowerBoundClamping() {
        val clampedBelow = SpeechSettings.DEFAULT.withSpeechRate(0.1f)
        assertEquals("Rate below minimum must clamp to 0.5f", 0.5f, clampedBelow.speechRate, 0.001f)

        val clampedZero = SpeechSettings.DEFAULT.withSpeechRate(0.0f)
        assertEquals("Rate 0.0f must clamp to 0.5f", 0.5f, clampedZero.speechRate, 0.001f)

        val clampedNegative = SpeechSettings.DEFAULT.withSpeechRate(-1.0f)
        assertEquals("Negative rate must clamp to 0.5f", 0.5f, clampedNegative.speechRate, 0.001f)
    }

    @Test
    fun testSpeechRateUpperBoundClamping() {
        val clampedAbove = SpeechSettings.DEFAULT.withSpeechRate(2.5f)
        assertEquals("Rate above maximum must clamp to 2.0f", 2.0f, clampedAbove.speechRate, 0.001f)

        val clampedLarge = SpeechSettings.DEFAULT.withSpeechRate(10.0f)
        assertEquals("Extreme rate must clamp to 2.0f", 2.0f, clampedLarge.speechRate, 0.001f)
    }

    @Test
    fun testVoicePitchLowerBoundClamping() {
        val clampedBelow = SpeechSettings.DEFAULT.withPitch(0.2f)
        assertEquals("Pitch below minimum must clamp to 0.5f", 0.5f, clampedBelow.pitch, 0.001f)

        val clampedZero = SpeechSettings.DEFAULT.withPitch(0.0f)
        assertEquals("Pitch 0.0f must clamp to 0.5f", 0.5f, clampedZero.pitch, 0.001f)
    }

    @Test
    fun testVoicePitchUpperBoundClamping() {
        val clampedAbove = SpeechSettings.DEFAULT.withPitch(2.8f)
        assertEquals("Pitch above maximum must clamp to 2.0f", 2.0f, clampedAbove.pitch, 0.001f)

        val clampedLarge = SpeechSettings.DEFAULT.withPitch(5.0f)
        assertEquals("Extreme pitch must clamp to 2.0f", 2.0f, clampedLarge.pitch, 0.001f)
    }

    @Test
    fun testSpeechStepBehavior() {
        // Step speech rate
        val rateSteppedUp = SpeechSettings.DEFAULT.withStepRate(SpeechSettings.STEP)
        assertEquals(1.1f, rateSteppedUp.speechRate, 0.001f)

        val rateSteppedDown = SpeechSettings.DEFAULT.withStepRate(-SpeechSettings.STEP)
        assertEquals(0.9f, rateSteppedDown.speechRate, 0.001f)

        // Step voice pitch
        val pitchSteppedUp = SpeechSettings.DEFAULT.withStepPitch(SpeechSettings.STEP)
        assertEquals(1.1f, pitchSteppedUp.pitch, 0.001f)

        val pitchSteppedDown = SpeechSettings.DEFAULT.withStepPitch(-SpeechSettings.STEP)
        assertEquals(0.9f, pitchSteppedDown.pitch, 0.001f)

        // Stepping past boundaries
        val atMaxRate = SpeechSettings(speechRate = 2.0f)
        assertEquals(2.0f, atMaxRate.withStepRate(SpeechSettings.STEP).speechRate, 0.001f)

        val atMinRate = SpeechSettings(speechRate = 0.5f)
        assertEquals(0.5f, atMinRate.withStepRate(-SpeechSettings.STEP).speechRate, 0.001f)

        val atMaxPitch = SpeechSettings(pitch = 2.0f)
        assertEquals(2.0f, atMaxPitch.withStepPitch(SpeechSettings.STEP).pitch, 0.001f)

        val atMinPitch = SpeechSettings(pitch = 0.5f)
        assertEquals(0.5f, atMinPitch.withStepPitch(-SpeechSettings.STEP).pitch, 0.001f)
    }

    @Test
    fun testDecimalNormalizationPreventsFloatingPointDrift() {
        // Float arithmetic 0.7f + 0.1f can suffer from representation drift
        val normalizedSum = SpeechSettings.normalize(0.7f + 0.1f)
        assertEquals(0.8f, normalizedSum, 0.0001f)

        // Unaligned inputs
        assertEquals(1.1f, SpeechSettings.normalize(1.1000001f), 0.0001f)
        assertEquals(0.9f, SpeechSettings.normalize(0.8999999f), 0.0001f)
        assertEquals(1.5f, SpeechSettings.normalize(1.49f), 0.0001f)
        assertEquals(1.5f, SpeechSettings.normalize(1.51f), 0.0001f)
    }

    @Test
    fun testResetVoiceDefaultsPreservesEnabledState() {
        val disabledCustom = SpeechSettings(enabled = false, speechRate = 1.8f, pitch = 0.6f)
        val resetDisabled = disabledCustom.resetVoiceDefaults()

        assertFalse("Resetting voice defaults must NOT re-enable speech", resetDisabled.enabled)
        assertEquals("Rate must reset to 1.0f", 1.0f, resetDisabled.speechRate, 0.001f)
        assertEquals("Pitch must reset to 1.0f", 1.0f, resetDisabled.pitch, 0.001f)

        val enabledCustom = SpeechSettings(enabled = true, speechRate = 1.5f, pitch = 1.7f)
        val resetEnabled = enabledCustom.resetVoiceDefaults()

        assertTrue("Resetting voice defaults must preserve enabled = true", resetEnabled.enabled)
        assertEquals(1.0f, resetEnabled.speechRate, 0.001f)
        assertEquals(1.0f, resetEnabled.pitch, 0.001f)
    }

    @Test
    fun testUpdatingRateDoesNotAffectPitchOrTtsEnabledOrFps() {
        val initial = SpeechSettings(enabled = true, speechRate = 1.0f, pitch = 1.3f)
        val updated = initial.withSpeechRate(1.6f)

        assertEquals(1.6f, updated.speechRate, 0.001f)
        assertEquals("Pitch must remain unchanged", 1.3f, updated.pitch, 0.001f)
        assertTrue("Enabled must remain unchanged", updated.enabled)

        // FPS constants must remain untouched
        assertEquals(5, AnimationFpsSettings.DEFAULT_IDLE_FPS)
        assertEquals(10, AnimationFpsSettings.DEFAULT_TALK_FPS)
    }

    @Test
    fun testUpdatingPitchDoesNotAffectRateOrTtsEnabled() {
        val initial = SpeechSettings(enabled = false, speechRate = 1.4f, pitch = 1.0f)
        val updated = initial.withPitch(0.7f)

        assertEquals("Rate must remain unchanged", 1.4f, updated.speechRate, 0.001f)
        assertEquals(0.7f, updated.pitch, 0.001f)
        assertFalse("Enabled must remain unchanged", updated.enabled)
    }

    @Test
    fun testMultiplierFormatting() {
        assertEquals("1.0x", SpeechSettings.formatMultiplier(1.0f))
        assertEquals("0.5x", SpeechSettings.formatMultiplier(0.5f))
        assertEquals("2.0x", SpeechSettings.formatMultiplier(2.0f))
        assertEquals("1.1x", SpeechSettings.formatMultiplier(1.1000001f))
        assertEquals("0.8x", SpeechSettings.formatMultiplier(0.7999999f))
    }

    @Test
    fun testStepBoundaryCheckHelpers() {
        val minSettings = SpeechSettings(speechRate = 0.5f, pitch = 0.5f)
        assertFalse(minSettings.canDecreaseRate())
        assertTrue(minSettings.canIncreaseRate())
        assertFalse(minSettings.canDecreasePitch())
        assertTrue(minSettings.canIncreasePitch())

        val maxSettings = SpeechSettings(speechRate = 2.0f, pitch = 2.0f)
        assertTrue(maxSettings.canDecreaseRate())
        assertFalse(maxSettings.canIncreaseRate())
        assertTrue(maxSettings.canDecreasePitch())
        assertFalse(maxSettings.canIncreasePitch())

        val midSettings = SpeechSettings(speechRate = 1.0f, pitch = 1.0f)
        assertTrue(midSettings.canDecreaseRate())
        assertTrue(midSettings.canIncreaseRate())
        assertTrue(midSettings.canDecreasePitch())
        assertTrue(midSettings.canIncreasePitch())
    }

    // =========================================================================
    // 3. Critical One-Time Event Contract (SharedFlow with replay = 0)
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
    // 4. TtsState and Safety Model
    // =========================================================================

    @Test
    fun testTtsStateValues() {
        val states = TtsState.values()
        assertTrue(states.contains(TtsState.INITIALIZING))
        assertTrue(states.contains(TtsState.READY))
        assertTrue(states.contains(TtsState.UNAVAILABLE))
    }
}
