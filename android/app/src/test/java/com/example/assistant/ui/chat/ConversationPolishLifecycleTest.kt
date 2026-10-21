package com.example.assistant.ui.chat

import com.example.assistant.domain.CharacterState
import com.example.assistant.domain.Emotion
import org.junit.Assert.*
import org.junit.Test

class ConversationPolishLifecycleTest {
    private fun reply(tts: Boolean = true, reveal: Boolean = true) =
        SpeechAnimationCoordinator().apply {
            onUserSendMessage()
            onReplyReceived("current", Emotion.HAPPY, tts, reveal)
        }

    private fun assertTalk(c: SpeechAnimationCoordinator) {
        assertEquals(ReplyPhase.RevealingOrSpeaking, c.phase)
        assertEquals(CharacterState.TALKING, c.characterState)
        assertEquals(Emotion.NEUTRAL, c.emotion)
    }

    @Test fun pendingRequestIsThinking() {
        val c = SpeechAnimationCoordinator()
        c.onUserSendMessage()
        assertEquals(ReplyPhase.Thinking, c.phase)
        assertEquals(CharacterState.THINKING, c.characterState)
    }

    @Test fun receiptStartsTalkBeforeSpeechStartCallback() { assertTalk(reply()) }

    @Test fun revealFinishesFirstAndTalkWaitsForSpeech() {
        val c = reply()
        assertTrue(c.onRevealCompleted("current"))
        assertTalk(c)
        c.onSpeechCompleted("current")
        assertEquals(ReplyPhase.FinalEmotion, c.phase)
    }

    @Test fun speechFinishesFirstAndTalkWaitsForReveal() {
        val c = reply()
        c.onSpeechCompleted("current")
        assertTalk(c)
        c.onRevealCompleted("current")
        assertEquals(ReplyPhase.FinalEmotion, c.phase)
    }

    @Test fun bothCompleteThenFullEmotionCompletionReturnsIdle() {
        val c = reply()
        c.onSpeechCompleted("current")
        c.onRevealCompleted("current")
        assertEquals(Emotion.HAPPY, c.emotion)
        c.onEmotionDisplayFinished("current")
        assertEquals(ReplyPhase.Idle, c.phase)
        assertEquals(CharacterState.IDLE, c.characterState)
    }

    @Test fun ttsDisabledTalksUntilRevealCompletes() {
        val c = reply(tts = false)
        assertTalk(c)
        c.onRevealCompleted("current")
        assertEquals(ReplyPhase.FinalEmotion, c.phase)
    }

    @Test fun typewriterDisabledTalksUntilSpeechCompletes() {
        val c = reply(reveal = false)
        assertTalk(c)
        c.onSpeechCompleted("current")
        assertEquals(ReplyPhase.FinalEmotion, c.phase)
    }

    @Test fun bothDisabledGoDirectlyToFinalEmotion() {
        assertEquals(ReplyPhase.FinalEmotion, reply(false, false).phase)
    }

    @Test fun stopSpeechWaitsForRevealThenPlaysEmotion() {
        val c = reply()
        assertTrue(c.onSpeechStopped("current"))
        assertTalk(c)
        c.onRevealCompleted("current")
        assertEquals(ReplyPhase.FinalEmotion, c.phase)
    }

    @Test fun replayUsesNewTokenAndPlaysEmotionAfterSpeech() {
        val c = reply(false, false)
        c.onEmotionDisplayFinished()
        c.onReplyReceived("replay", Emotion.SAD, true)
        assertTalk(c)
        assertFalse(c.onSpeechCompleted("current"))
        c.onSpeechCompleted("replay")
        assertEquals(Emotion.SAD, c.emotion)
        assertEquals(ReplyPhase.FinalEmotion, c.phase)
    }

    @Test fun initializationFailureWaitsForReveal() {
        val c = reply()
        assertTrue(c.onSpeechError("current"))
        assertTalk(c)
        c.onRevealCompleted("current")
        assertEquals(ReplyPhase.FinalEmotion, c.phase)
    }

    @Test fun speechFailureAfterRevealPlaysEmotion() {
        val c = reply()
        c.onSpeechStarted("current")
        c.onRevealCompleted("current")
        c.onSpeechError("current")
        assertEquals(ReplyPhase.FinalEmotion, c.phase)
    }

    @Test fun staleSpeechAndRevealAndEmotionCompletionsCannotChangeNewReply() {
        val c = reply()
        c.onReplyReceived("new", Emotion.SAD, true, true)
        assertFalse(c.onSpeechCompleted("current"))
        assertFalse(c.onSpeechError("current"))
        assertFalse(c.onSpeechStopped("current"))
        assertFalse(c.onRevealCompleted("current"))
        c.onEmotionDisplayFinished("current")
        assertTalk(c)
        assertEquals("new", c.activeUtteranceId)
    }

    @Test fun newRequestDuringSpeechOrReplayInvalidatesOldCallbacks() {
        val c = reply()
        c.onUserSendMessage()
        assertFalse(c.onSpeechCompleted("current"))
        assertFalse(c.onRevealCompleted("current"))
        assertEquals(CharacterState.THINKING, c.characterState)
    }

    @Test fun conversationSwitchOrDisposalInvalidatesRevealAndSpeech() {
        val c = reply()
        c.onReset()
        assertFalse(c.onSpeechStarted("current"))
        assertFalse(c.onRevealCompleted("current"))
        assertEquals(ReplyPhase.Idle, c.phase)
    }

    @Test fun backendFailureResetsThinking() {
        val c = SpeechAnimationCoordinator()
        c.onUserSendMessage()
        c.onReset()
        assertEquals(CharacterState.IDLE, c.characterState)
        assertNull(c.activeUtteranceId)
    }

    @Test fun prematureEmotionCallbackCannotEndTalk() {
        val c = reply()
        c.onEmotionDisplayFinished("current")
        assertTalk(c)
    }

    @Test fun neutralResponsePreservesExistingDirectIdleAfterCompletion() {
        val c = SpeechAnimationCoordinator()
        c.onReplyReceived("neutral", Emotion.NEUTRAL, false, true)
        c.onRevealCompleted("neutral")
        assertEquals(ReplyPhase.Idle, c.phase)
    }
}
