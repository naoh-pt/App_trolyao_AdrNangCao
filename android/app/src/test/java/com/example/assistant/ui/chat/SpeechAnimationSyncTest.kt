package com.example.assistant.ui.chat

import com.example.assistant.domain.CharacterState
import com.example.assistant.domain.Emotion
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test

/**
 * Unit tests verifying synchronization between character animation states
 * and Android Text-to-Speech (TTS) utterance lifecycle.
 */
class SpeechAnimationSyncTest {

    private lateinit var coordinator: SpeechAnimationCoordinator

    @Before
    fun setUp() {
        coordinator = SpeechAnimationCoordinator()
    }

    // =========================================================================
    // 1. Thinking becomes talk when active TTS starts
    // =========================================================================

    @Test
    fun testThinkingBecomesTalkWhenActiveTtsStarts() {
        // User sends message -> enters THINKING
        coordinator.onUserSendMessage()
        assertEquals(CharacterState.THINKING, coordinator.characterState)
        assertEquals(Emotion.NEUTRAL, coordinator.emotion)

        // Backend reply arrives with TTS enabled -> remains in THINKING until TTS starts
        coordinator.onReplyReceived("utt-1", Emotion.HAPPY, ttsEnabled = true)
        assertEquals("utt-1", coordinator.activeUtteranceId)
        assertEquals(CharacterState.THINKING, coordinator.characterState)

        // TTS starts speaking -> transitions to TALKING + NEUTRAL (loops "talk" animation)
        val started = coordinator.onSpeechStarted("utt-1")
        assertTrue("Speech start must succeed for active utterance", started)
        assertEquals(CharacterState.TALKING, coordinator.characterState)
        assertEquals(Emotion.NEUTRAL, coordinator.emotion)
    }

    // =========================================================================
    // 2. Talk remains active until onDone
    // =========================================================================

    @Test
    fun testTalkRemainsActiveUntilOnDone() {
        coordinator.onUserSendMessage()
        coordinator.onReplyReceived("utt-1", Emotion.HAPPY, ttsEnabled = true)
        coordinator.onSpeechStarted("utt-1")

        assertEquals(CharacterState.TALKING, coordinator.characterState)
        assertEquals(Emotion.NEUTRAL, coordinator.emotion)

        // Unrelated or duplicate events do not disrupt TALKING
        val ignoredOther = coordinator.onSpeechStarted("utt-unknown")
        assertFalse(ignoredOther)
        assertEquals(CharacterState.TALKING, coordinator.characterState)
        assertEquals(Emotion.NEUTRAL, coordinator.emotion)

        // Still active
        assertEquals("utt-1", coordinator.activeUtteranceId)
    }

    // =========================================================================
    // 3. onDone transitions through non-neutral response emotion and then idle
    // =========================================================================

    @Test
    fun testOnDoneTransitionsThroughNonNeutralResponseEmotionAndThenIdle() {
        val nonNeutralEmotions = listOf(Emotion.HAPPY, Emotion.SAD, Emotion.SURPRISED)

        for (emotion in nonNeutralEmotions) {
            val coord = SpeechAnimationCoordinator()
            coord.onUserSendMessage()
            coord.onReplyReceived("utt-$emotion", emotion, ttsEnabled = true)
            coord.onSpeechStarted("utt-$emotion")

            assertEquals(CharacterState.TALKING, coord.characterState)
            assertEquals(Emotion.NEUTRAL, coord.emotion)

            // Speech completes -> transitions to TALKING + non-neutral emotion
            val completed = coord.onSpeechCompleted("utt-$emotion")
            assertTrue(completed)
            assertNull("Active utterance must be cleared on completion", coord.activeUtteranceId)
            assertEquals(CharacterState.TALKING, coord.characterState)
            assertEquals(emotion, coord.emotion)

            // Once brief emotion display / one-shot completes -> returns to IDLE + NEUTRAL
            coord.onEmotionDisplayFinished()
            assertEquals(CharacterState.IDLE, coord.characterState)
            assertEquals(Emotion.NEUTRAL, coord.emotion)
        }
    }

    // =========================================================================
    // 4. Neutral completion returns to idle
    // =========================================================================

    @Test
    fun testNeutralCompletionReturnsDirectlyToIdle() {
        coordinator.onUserSendMessage()
        coordinator.onReplyReceived("utt-neutral", Emotion.NEUTRAL, ttsEnabled = true)
        coordinator.onSpeechStarted("utt-neutral")

        assertEquals(CharacterState.TALKING, coordinator.characterState)
        assertEquals(Emotion.NEUTRAL, coordinator.emotion)

        // OnDone for neutral -> returns directly to IDLE without emotional intermediate
        val completed = coordinator.onSpeechCompleted("utt-neutral")
        assertTrue(completed)
        assertNull(coordinator.activeUtteranceId)
        assertEquals(CharacterState.IDLE, coordinator.characterState)
        assertEquals(Emotion.NEUTRAL, coordinator.emotion)
    }

    // =========================================================================
    // 5. onError does not leave the character in talk
    // =========================================================================

    @Test
    fun testOnErrorDoesNotLeaveCharacterInTalkForNeutral() {
        coordinator.onUserSendMessage()
        coordinator.onReplyReceived("utt-err", Emotion.NEUTRAL, ttsEnabled = true)
        coordinator.onSpeechStarted("utt-err")

        // TTS error occurs
        val errorHandled = coordinator.onSpeechError("utt-err")
        assertTrue(errorHandled)
        assertNull(coordinator.activeUtteranceId)
        assertEquals(CharacterState.IDLE, coordinator.characterState)
        assertEquals(Emotion.NEUTRAL, coordinator.emotion)
    }

    @Test
    fun testOnErrorDoesNotLeaveCharacterInTalkForNonNeutral() {
        coordinator.onUserSendMessage()
        coordinator.onReplyReceived("utt-err-happy", Emotion.HAPPY, ttsEnabled = true)
        coordinator.onSpeechStarted("utt-err-happy")

        // TTS error occurs -> shows emotion safely, then can finish to idle
        val errorHandled = coordinator.onSpeechError("utt-err-happy")
        assertTrue(errorHandled)
        assertNull(coordinator.activeUtteranceId)
        assertEquals(CharacterState.TALKING, coordinator.characterState)
        assertEquals(Emotion.HAPPY, coordinator.emotion)

        coordinator.onEmotionDisplayFinished()
        assertEquals(CharacterState.IDLE, coordinator.characterState)
        assertEquals(Emotion.NEUTRAL, coordinator.emotion)
    }

    // =========================================================================
    // 6. TTS disabled preserves response-emotion behavior
    // =========================================================================

    @Test
    fun testTtsDisabledPreservesResponseEmotionBehavior() {
        coordinator.onUserSendMessage()
        assertEquals(CharacterState.THINKING, coordinator.characterState)

        // Reply received when TTS is disabled
        coordinator.onReplyReceived("utt-disabled", Emotion.HAPPY, ttsEnabled = false)
        assertNull("TTS disabled must not hold active utterance ID", coordinator.activeUtteranceId)
        assertEquals(CharacterState.TALKING, coordinator.characterState)
        assertEquals(Emotion.HAPPY, coordinator.emotion)

        // When one-shot completes -> returns to IDLE
        coordinator.onEmotionDisplayFinished()
        assertEquals(CharacterState.IDLE, coordinator.characterState)
        assertEquals(Emotion.NEUTRAL, coordinator.emotion)
    }

    @Test
    fun testTtsDisabledNeutralReply() {
        coordinator.onUserSendMessage()
        coordinator.onReplyReceived("utt-disabled-neutral", Emotion.NEUTRAL, ttsEnabled = false)
        assertEquals(CharacterState.TALKING, coordinator.characterState)
        assertEquals(Emotion.NEUTRAL, coordinator.emotion)

        coordinator.onEmotionDisplayFinished()
        assertEquals(CharacterState.IDLE, coordinator.characterState)
        assertEquals(Emotion.NEUTRAL, coordinator.emotion)
    }

    // =========================================================================
    // 7. Stale callback from an old utterance cannot override a newer state
    // =========================================================================

    @Test
    fun testStaleCallbackFromOldUtteranceCannotOverrideNewerState() {
        // First reply: utt-1
        coordinator.onUserSendMessage()
        coordinator.onReplyReceived("utt-1", Emotion.HAPPY, ttsEnabled = true)
        coordinator.onSpeechStarted("utt-1")

        // Second reply arrives: utt-2
        coordinator.onReplyReceived("utt-2", Emotion.SAD, ttsEnabled = true)
        assertEquals("utt-2", coordinator.activeUtteranceId)

        // Stale completion from utt-1 arrives
        val staleHandled = coordinator.onSpeechCompleted("utt-1")
        assertFalse("Stale utterance completion must be rejected", staleHandled)

        // Verify state is NOT overwritten by stale utt-1
        assertEquals("utt-2", coordinator.activeUtteranceId)
        assertEquals(Emotion.SAD, coordinator.pendingResponseEmotion)

        // Stale error from utt-1 arrives
        val staleErrorHandled = coordinator.onSpeechError("utt-1")
        assertFalse("Stale utterance error must be rejected", staleErrorHandled)

        // Valid start for utt-2
        assertTrue(coordinator.onSpeechStarted("utt-2"))
        assertEquals(CharacterState.TALKING, coordinator.characterState)
        assertEquals(Emotion.NEUTRAL, coordinator.emotion)

        // Valid done for utt-2
        assertTrue(coordinator.onSpeechCompleted("utt-2"))
        assertEquals(CharacterState.TALKING, coordinator.characterState)
        assertEquals(Emotion.SAD, coordinator.emotion)
    }

    // =========================================================================
    // 8. Sending a new message cancels/invalidates the previous speech state
    // =========================================================================

    @Test
    fun testSendingNewMessageCancelsAndInvalidatesPreviousSpeechState() {
        // Bot is speaking utt-1
        coordinator.onUserSendMessage()
        coordinator.onReplyReceived("utt-1", Emotion.HAPPY, ttsEnabled = true)
        coordinator.onSpeechStarted("utt-1")
        assertEquals(CharacterState.TALKING, coordinator.characterState)
        assertEquals("utt-1", coordinator.activeUtteranceId)

        // User sends a new message while utt-1 was speaking
        coordinator.onUserSendMessage()
        assertEquals(CharacterState.THINKING, coordinator.characterState)
        assertEquals(Emotion.NEUTRAL, coordinator.emotion)
        assertNull("activeUtteranceId must be cleared on new send", coordinator.activeUtteranceId)

        // Old callback from utt-1 arrives late
        val staleStart = coordinator.onSpeechStarted("utt-1")
        val staleDone = coordinator.onSpeechCompleted("utt-1")
        val staleErr = coordinator.onSpeechError("utt-1")

        assertFalse(staleStart)
        assertFalse(staleDone)
        assertFalse(staleErr)

        // Character remains safely in THINKING for the new request
        assertEquals(CharacterState.THINKING, coordinator.characterState)
        assertEquals(Emotion.NEUTRAL, coordinator.emotion)
    }

    // =========================================================================
    // 9. Reset and Interruption Handling
    // =========================================================================

    @Test
    fun testSpeechStoppedResetsToIdle() {
        coordinator.onUserSendMessage()
        coordinator.onReplyReceived("utt-stop", Emotion.HAPPY, ttsEnabled = true)
        coordinator.onSpeechStarted("utt-stop")

        val stopped = coordinator.onSpeechStopped("utt-stop")
        assertTrue(stopped)
        assertNull(coordinator.activeUtteranceId)
        assertEquals(CharacterState.IDLE, coordinator.characterState)
        assertEquals(Emotion.NEUTRAL, coordinator.emotion)
    }

    @Test
    fun testResetRestoresInitialIdleState() {
        coordinator.onUserSendMessage()
        coordinator.onReplyReceived("utt-active", Emotion.HAPPY, ttsEnabled = true)
        coordinator.onSpeechStarted("utt-active")

        coordinator.onReset()
        assertNull(coordinator.activeUtteranceId)
        assertEquals(CharacterState.IDLE, coordinator.characterState)
        assertEquals(Emotion.NEUTRAL, coordinator.emotion)
    }
}
