package com.example.assistant.ui.chat

import com.example.assistant.domain.CharacterState
import com.example.assistant.domain.Emotion
import com.example.assistant.ui.character.CharacterFrameCatalog
import com.example.assistant.ui.character.PlaybackMode
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class ChatAnimationIntegrationTest {

    // =========================================================================
    // 1. Exact FPS and Duration Specifications
    // =========================================================================

    @Test
    fun testExactFpsValuesForStage3() {
        assertEquals("idle must be 8 FPS", 8, CharacterFrameCatalog.idle.fps)
        assertEquals("thinking must be 8 FPS", 8, CharacterFrameCatalog.thinking.fps)
        assertEquals("talk must be 10 FPS", 10, CharacterFrameCatalog.talk.fps)
        assertEquals("happy must be 10 FPS", 10, CharacterFrameCatalog.happy.fps)
        assertEquals("sad must be 8 FPS", 8, CharacterFrameCatalog.sad.fps)
        assertEquals("surprised must be 10 FPS", 10, CharacterFrameCatalog.surprised.fps)
    }

    @Test
    fun testTotalDurationsReflectNewFps() {
        // idle: 32 frames @ 8 FPS -> 125ms * 32 = 4000ms
        assertEquals(125L, CharacterFrameCatalog.idle.frameDurationMs)
        assertEquals(4000L, CharacterFrameCatalog.idle.totalDurationMs)

        // thinking: 30 frames @ 8 FPS -> 125ms * 30 = 3750ms
        assertEquals(125L, CharacterFrameCatalog.thinking.frameDurationMs)
        assertEquals(3750L, CharacterFrameCatalog.thinking.totalDurationMs)

        // talk: 19 frames @ 10 FPS -> 100ms * 19 = 1900ms
        assertEquals(100L, CharacterFrameCatalog.talk.frameDurationMs)
        assertEquals(1900L, CharacterFrameCatalog.talk.totalDurationMs)

        // happy: 15 frames @ 10 FPS -> 100ms * 15 = 1500ms
        assertEquals(100L, CharacterFrameCatalog.happy.frameDurationMs)
        assertEquals(1500L, CharacterFrameCatalog.happy.totalDurationMs)

        // sad: 21 frames @ 8 FPS -> 125ms * 21 = 2625ms
        assertEquals(125L, CharacterFrameCatalog.sad.frameDurationMs)
        assertEquals(2625L, CharacterFrameCatalog.sad.totalDurationMs)

        // surprised: 23 frames @ 10 FPS -> 100ms * 23 = 2300ms
        assertEquals(100L, CharacterFrameCatalog.surprised.frameDurationMs)
        assertEquals(2300L, CharacterFrameCatalog.surprised.totalDurationMs)
    }

    @Test
    fun testEmotionalOneShotDurationsExceedOldFixedTimer() {
        // Confirms why old fixed 2000ms timer cut off sad (2625ms) and surprised (2300ms)
        assertTrue(
            "sad duration (2625ms) exceeds 2000ms timer",
            CharacterFrameCatalog.sad.totalDurationMs > 2000L,
        )
        assertTrue(
            "surprised duration (2300ms) exceeds 2000ms timer",
            CharacterFrameCatalog.surprised.totalDurationMs > 2000L,
        )
        assertEquals(PlaybackMode.ONE_SHOT, CharacterFrameCatalog.sad.mode)
        assertEquals(PlaybackMode.ONE_SHOT, CharacterFrameCatalog.surprised.mode)
        assertEquals(PlaybackMode.ONE_SHOT, CharacterFrameCatalog.happy.mode)
        assertEquals(PlaybackMode.LOOP, CharacterFrameCatalog.talk.mode)
    }

    // =========================================================================
    // 2. State Transition Guards (canHandleAnimationFinished)
    // =========================================================================

    @Test
    fun testCanHandleAnimationFinishedOnlyForEmotionalTalking() {
        // Emotional one-shots in TALKING state must be handled
        assertTrue(canHandleAnimationFinished(CharacterState.TALKING, Emotion.HAPPY))
        assertTrue(canHandleAnimationFinished(CharacterState.TALKING, Emotion.SAD))
        assertTrue(canHandleAnimationFinished(CharacterState.TALKING, Emotion.SURPRISED))

        // Neutral talk is controlled by the 2s timer, NOT animation finished callback
        assertFalse(canHandleAnimationFinished(CharacterState.TALKING, Emotion.NEUTRAL))

        // IDLE state must never accept animation finished callbacks
        for (emotion in Emotion.values()) {
            assertFalse(canHandleAnimationFinished(CharacterState.IDLE, emotion))
        }

        // THINKING state (sending message) must never be interrupted by obsolete callbacks
        for (emotion in Emotion.values()) {
            assertFalse(canHandleAnimationFinished(CharacterState.THINKING, emotion))
        }
    }

    // =========================================================================
    // 3. State Reducer Tests (reduceAnimationFinished)
    // =========================================================================

    @Test
    fun testReduceAnimationFinishedTransitionsToIdleAndNeutral() {
        val emotionalStates = listOf(Emotion.HAPPY, Emotion.SAD, Emotion.SURPRISED)

        for (emotion in emotionalStates) {
            val current = ChatUiState(
                characterState = CharacterState.TALKING,
                emotion = emotion,
                sending = false,
            )
            val updated = current.reduceAnimationFinished()

            assertEquals(CharacterState.IDLE, updated.characterState)
            assertEquals(Emotion.NEUTRAL, updated.emotion)
        }
    }

    @Test
    fun testReduceAnimationFinishedIgnoresNonQualifyingStates() {
        // 1. Neutral TALKING state must not be modified by one-shot finished reducer
        val neutralTalking = ChatUiState(
            characterState = CharacterState.TALKING,
            emotion = Emotion.NEUTRAL,
        )
        assertEquals(neutralTalking, neutralTalking.reduceAnimationFinished())

        // 2. THINKING state must not be modified
        val thinking = ChatUiState(
            characterState = CharacterState.THINKING,
            emotion = Emotion.NEUTRAL,
            sending = true,
        )
        assertEquals(thinking, thinking.reduceAnimationFinished())

        // 3. IDLE state must not be modified
        val idle = ChatUiState(
            characterState = CharacterState.IDLE,
            emotion = Emotion.NEUTRAL,
        )
        assertEquals(idle, idle.reduceAnimationFinished())
    }

    // =========================================================================
    // 4. Race Condition & Concurrency Scenarios
    // =========================================================================

    @Test
    fun testRaceConditionNewMessageSentWhileEmotionalAnimationActive() {
        // 1. Bot replied with HAPPY -> currently TALKING + HAPPY
        val talkingHappy = ChatUiState(
            characterState = CharacterState.TALKING,
            emotion = Emotion.HAPPY,
        )

        // 2. User quickly sends a new message -> state changes to THINKING + NEUTRAL, sending = true
        val sendingState = talkingHappy.copy(
            characterState = CharacterState.THINKING,
            emotion = Emotion.NEUTRAL,
            sending = true,
            pending = "hello again",
        )

        // 3. Now the old HAPPY animation's completion callback fires
        assertFalse(canHandleAnimationFinished(sendingState.characterState, sendingState.emotion))
        val stateAfterObsoleteCallback = sendingState.reduceAnimationFinished()

        // 4. Verify the state was NOT clobbered back to IDLE
        assertEquals(CharacterState.THINKING, stateAfterObsoleteCallback.characterState)
        assertEquals(Emotion.NEUTRAL, stateAfterObsoleteCallback.emotion)
        assertTrue(stateAfterObsoleteCallback.sending)
        assertEquals("hello again", stateAfterObsoleteCallback.pending)
    }

    @Test
    fun testRaceConditionNewChatCreatedWhileEmotionalAnimationActive() {
        // 1. Bot replied with SURPRISED -> TALKING + SURPRISED
        val talkingSurprised = ChatUiState(
            characterState = CharacterState.TALKING,
            emotion = Emotion.SURPRISED,
        )

        // 2. User clicks new chat -> fresh state created
        val freshChatState = ChatUiState()
        assertEquals(CharacterState.IDLE, freshChatState.characterState)
        assertEquals(Emotion.NEUTRAL, freshChatState.emotion)

        // 3. Obsolete callback from SURPRISED animation arrives
        assertFalse(canHandleAnimationFinished(freshChatState.characterState, freshChatState.emotion))
        val stateAfterCallback = freshChatState.reduceAnimationFinished()

        assertEquals(CharacterState.IDLE, stateAfterCallback.characterState)
        assertEquals(Emotion.NEUTRAL, stateAfterCallback.emotion)
    }

    @Test
    fun testDuplicateCallbackHandledSafely() {
        val talkingSad = ChatUiState(
            characterState = CharacterState.TALKING,
            emotion = Emotion.SAD,
        )

        // First callback
        val state1 = talkingSad.reduceAnimationFinished()
        assertEquals(CharacterState.IDLE, state1.characterState)
        assertEquals(Emotion.NEUTRAL, state1.emotion)

        // Duplicate second callback
        val state2 = state1.reduceAnimationFinished()
        assertEquals(CharacterState.IDLE, state2.characterState)
        assertEquals(Emotion.NEUTRAL, state2.emotion)
    }
}
