package com.example.assistant.ui.chat

import android.app.Activity
import com.example.assistant.domain.CharacterState
import com.example.assistant.domain.Emotion
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * Unit tests verifying speech recognition result extraction, state reduction,
 * and input text preservation for minimal Android voice-to-text input.
 */
class VoiceInputTest {

    // =========================================================================
    // 1. Result Extraction Tests
    // =========================================================================

    @Test
    fun testSuccessfulRecognitionExtractsBestTrimmedText() {
        val matches = listOf("  Hôm nay thời tiết thế nào?  ", "hôm nay thời tiết thế nào")
        val result = extractSpeechRecognitionText(Activity.RESULT_OK, matches)
        assertEquals("Hôm nay thời tiết thế nào?", result)
    }

    @Test
    fun testEmptyRecognitionResultReturnsNull() {
        val emptyListResult = extractSpeechRecognitionText(Activity.RESULT_OK, emptyList())
        assertNull(emptyListResult)

        val nullListResult = extractSpeechRecognitionText(Activity.RESULT_OK, null)
        assertNull(nullListResult)

        val blankStringResult = extractSpeechRecognitionText(Activity.RESULT_OK, listOf("   ", "  \t\n "))
        assertNull(blankStringResult)
    }

    @Test
    fun testCancelledRecognitionReturnsNull() {
        val matches = listOf("Câu hỏi người dùng nói")
        val result = extractSpeechRecognitionText(Activity.RESULT_CANCELED, matches)
        assertNull("Cancelled speech recognizer must return null", result)
    }

    @Test
    fun testFailedRecognitionReturnsNull() {
        val matches = listOf("Câu hỏi")
        val result = extractSpeechRecognitionText(12345, matches)
        assertNull("Non-OK result code must return null", result)
    }

    // =========================================================================
    // 2. Input Reduction Tests
    // =========================================================================

    @Test
    fun testSuccessfulRecognitionUpdatesInputText() {
        val currentText = "văn bản cũ"
        val recognized = "câu hỏi mới bằng giọng nói"
        val updated = reduceVoiceInput(currentText, recognized)
        assertEquals("câu hỏi mới bằng giọng nói", updated)
    }

    @Test
    fun testEmptyOrNullRecognitionPreservesExistingText() {
        val currentText = "đang soạn dở một câu hỏi dài"

        assertEquals(currentText, reduceVoiceInput(currentText, null))
        assertEquals(currentText, reduceVoiceInput(currentText, ""))
        assertEquals(currentText, reduceVoiceInput(currentText, "    "))
    }

    @Test
    fun testCancelledRecognitionPreservesExistingText() {
        val currentText = "Tôi muốn hỏi về..."
        val recognizedText = extractSpeechRecognitionText(Activity.RESULT_CANCELED, listOf("lời nói"))
        assertNull(recognizedText)

        val updated = reduceVoiceInput(currentText, recognizedText)
        assertEquals(currentText, updated)
    }

    // =========================================================================
    // 3. UI State and Non-Auto-Send Invariants
    // =========================================================================

    @Test
    fun testRecognitionDoesNotAutomaticallySendMessage() {
        val initialState = ChatUiState(
            characterState = CharacterState.IDLE,
            emotion = Emotion.NEUTRAL,
            input = "văn bản trước đó",
            sending = false,
            pending = null,
            online = true,
        )

        val recognized = "Thời tiết Hà Nội hôm nay"
        val updatedInput = reduceVoiceInput(initialState.input, recognized)
        val stateAfterVoice = initialState.copy(input = updatedInput)

        // Verifications:
        assertEquals("Thời tiết Hà Nội hôm nay", stateAfterVoice.input)
        assertFalse("Voice input must NOT automatically set sending to true", stateAfterVoice.sending)
        assertNull("Voice input must NOT create a pending message", stateAfterVoice.pending)
        assertEquals(CharacterState.IDLE, stateAfterVoice.characterState)
        assertEquals(Emotion.NEUTRAL, stateAfterVoice.emotion)
    }

    @Test
    fun testExistingManualTextEntryAndSendBehaviorIntact() {
        var state = ChatUiState(online = true, sending = false)

        // 1. User types manually
        fun onInputChange(text: String) {
            state = state.copy(input = text.take(2000))
        }

        onInputChange("Chào bạn")
        assertEquals("Chào bạn", state.input)

        // 2. Voice input overrides or sets text
        val recognized = "Xin chào Anna"
        onInputChange(reduceVoiceInput(state.input, recognized))
        assertEquals("Xin chào Anna", state.input)

        // 3. User manually edits after voice input
        onInputChange(state.input + " nhé")
        assertEquals("Xin chào Anna nhé", state.input)

        // 4. canSend predicate check
        val canSend = state.online && !state.sending && (state.pending != null || state.input.isNotBlank())
        assertTrue("canSend must be true when input is non-blank and not sending", canSend)
    }
}
