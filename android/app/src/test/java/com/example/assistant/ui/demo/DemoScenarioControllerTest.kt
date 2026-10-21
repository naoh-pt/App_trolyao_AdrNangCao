package com.example.assistant.ui.demo

import com.example.assistant.domain.CharacterState
import com.example.assistant.ui.chat.ChatUiState
import org.junit.Assert.*
import org.junit.Test

class DemoScenarioControllerTest {
    private fun start(id: String = "quick") = ChatUiState().reduceDemo(DemoCommand.Start(id))
    private fun ChatUiState.navigate(command: DemoCommand) = copy(input = "").reduceDemo(command)

    @Test fun startFillsFirstStep() {
        val state = start()
        assertEquals(0, state.demo.progress!!.index)
        assertEquals("Xin chào Anna", state.input)
        assertFalse(state.sending)
    }
    @Test fun nextFillsFullPrompt() {
        val state = start().navigate(DemoCommand.Next)
        assertEquals(1, state.demo.progress!!.index)
        assertEquals("Mấy giờ rồi?", state.input)
    }
    @Test fun previousReturnsToFirst() = assertEquals(0, start().navigate(DemoCommand.Next).navigate(DemoCommand.Previous).demo.progress!!.index)
    @Test fun cannotMoveBeforeFirst() {
        val state = start()
        assertEquals(state, state.reduceDemo(DemoCommand.Previous))
    }
    @Test fun cannotMoveBeyondLast() {
        var state = start()
        repeat(3) { state = state.navigate(DemoCommand.Next) }
        assertEquals(state, state.reduceDemo(DemoCommand.Next))
    }
    @Test fun stopPreservesDraftAndChat() {
        val state = start().copy(input = "Bản nháp riêng", speechActive = true)
        assertEquals(state.copy(demo = DemoState()), state.reduceDemo(DemoCommand.Stop))
    }
    @Test fun completionOnlyAtFinalStep() {
        var state = start()
        assertEquals(state, state.reduceDemo(DemoCommand.Complete))
        repeat(3) { state = state.navigate(DemoCommand.Next) }
        val completed = state.reduceDemo(DemoCommand.Complete)
        assertTrue(completed.demo.progress!!.completed)
        assertEquals(state.input, completed.input)
        assertFalse(completed.navigate(DemoCommand.Previous).demo.progress!!.completed)
    }
    @Test fun switchingScenarioResetsIndex() {
        val state = start().navigate(DemoCommand.Next).navigate(DemoCommand.Start("full"))
        assertEquals(DemoProgress("full"), state.demo.progress)
    }
    @Test fun stateCopiesDoNotAdvance() {
        val state = start().navigate(DemoCommand.Next)
        repeat(10) { assertEquals(state.demo.progress, state.copy(demo = state.demo.copy()).demo.progress) }
    }
    @Test fun weatherSelectionPreservesExistingDraftUntilConfirmed() {
        val state = start()
        val pending = state.reduceDemo(DemoCommand.Pick("weather_now"))
        assertEquals(state.input, pending.input)
        assertEquals(state.demo.progress, pending.demo.progress)
        val accepted = pending.reduceDemo(DemoCommand.ConfirmReplacement)
        assertEquals("Thời tiết Hà Nội hiện tại thế nào?", accepted.input)
        assertFalse(accepted.sending)
        assertEquals(state.characterState, accepted.characterState)
    }
    @Test fun weatherFillsExactPromptsWithoutSendingOrPlayback() {
        val prompts = listOf("Thời tiết Hà Nội hiện tại thế nào?", "Ngày mai Hà Nội có mưa không?",
            "Nhiệt độ ở Bắc Ninh hôm nay bao nhiêu?", "Hôm nay mình có nên mang áo mưa ở Hà Nội không?")
        DemoQuestionCatalog.questions.filter { it.category == DemoCategory.Weather }.zip(prompts).forEach { (question, prompt) ->
            val initial = ChatUiState()
            val selected = initial.reduceDemo(DemoCommand.Open).reduceDemo(DemoCommand.Pick(question.id))
            assertEquals(prompt, selected.input)
            assertEquals(initial, selected.copy(input = "", demo = DemoState()))
        }
    }
    @Test fun fullScenarioIncludesWeatherAsNinthManualStep() {
        var state = start("full")
        repeat(8) { state = state.navigate(DemoCommand.Next) }
        assertEquals(8, state.demo.progress!!.index)
        assertEquals("Thời tiết Hà Nội hiện tại thế nào?", state.input)
        state = state.navigate(DemoCommand.Next)
        assertEquals("Anna hãy nhớ: mình tên là Hoàn.", state.input)
        state = state.navigate(DemoCommand.Next)
        assertEquals("Anna nhớ gì về mình?", state.input)
        state = state.navigate(DemoCommand.Next)
        assertEquals("Hôm nay mình bị điểm thấp và cảm thấy thất vọng.", state.input)
        assertEquals(state, state.reduceDemo(DemoCommand.Next))
        assertTrue(state.reduceDemo(DemoCommand.Complete).demo.progress!!.completed)
        assertFalse(state.sending)
    }
    @Test fun unknownIdsIgnored() {
        val state = start()
        assertEquals(state, state.reduceDemo(DemoCommand.Pick("missing")))
        assertEquals(state, state.reduceDemo(DemoCommand.Start("missing")))
    }
    @Test fun blankDraftFilledAndSheetClosed() {
        val state = ChatUiState(input = "  ").reduceDemo(DemoCommand.Open).reduceDemo(DemoCommand.Pick("study_tuition"))
        assertEquals(DemoQuestionCatalog.question("study_tuition")!!.prompt, state.input)
        assertFalse(state.demo.sheetOpen)
    }
    @Test fun existingDraftRequiresConfirmation() {
        val state = ChatUiState(input = "Giữ lại").reduceDemo(DemoCommand.Start("full"))
        assertEquals("Giữ lại", state.input)
        assertNull(state.demo.progress)
        assertNotNull(state.demo.pendingSelection)
        val accepted = state.reduceDemo(DemoCommand.ConfirmReplacement)
        assertEquals("Xin chào Anna", accepted.input)
        assertEquals(DemoProgress("full"), accepted.demo.progress)
    }
    @Test fun cancelPreservesDraftAndProgress() {
        val initial = start()
        val canceled = initial.reduceDemo(DemoCommand.Next).reduceDemo(DemoCommand.CancelReplacement)
        assertEquals(initial, canceled)
    }
    @Test fun changedDraftRequiresAnotherReview() {
        val pending = ChatUiState(input = "Một").reduceDemo(DemoCommand.Pick("chat_greeting"))
        val state = pending.copy(input = "Hai").reduceDemo(DemoCommand.ConfirmReplacement)
        assertEquals("Hai", state.input)
        assertEquals("Hai", state.demo.pendingSelection!!.originalDraft)
        assertEquals("Xin chào Anna", state.reduceDemo(DemoCommand.ConfirmReplacement).input)
    }
    @Test fun openingAndDismissingPreserveDraft() {
        val initial = start()
        assertEquals(initial, initial.reduceDemo(DemoCommand.Open).reduceDemo(DemoCommand.Close))
    }
    @Test fun selectionChangesOnlyDraftAndDemo() {
        val original = ChatUiState(characterState = CharacterState.TALKING, speechActive = true, playbackToken = "old", incomingAssistantId = "message", online = false, error = "existing")
        val selected = original.reduceDemo(DemoCommand.Pick("utility_calendar"))
        assertEquals(original, selected.copy(input = original.input, demo = original.demo))
        // The reducer has no send/repository/TTS dependency: no message/request can be created.
        assertFalse(selected.sending)
        assertNull(selected.pending)
    }
    @Test fun sendingAndRetryDraftCannotBeReplaced() {
        listOf(ChatUiState(sending = true), ChatUiState(pending = "retry")).forEach { original ->
            assertEquals(original, original.reduceDemo(DemoCommand.Start("quick")))
            assertEquals(original, original.reduceDemo(DemoCommand.Pick("chat_greeting")))
        }
    }
    @Test fun standalonePickStopsGuideOnlyAfterConfirmation() {
        val original = start()
        val pending = original.reduceDemo(DemoCommand.Pick("time_date"))
        assertEquals(original.demo.progress, pending.demo.progress)
        assertNull(pending.reduceDemo(DemoCommand.ConfirmReplacement).demo.progress)
    }
    @Test fun samePromptNeedsNoConfirmation() {
        val state = start().reduceDemo(DemoCommand.Pick("chat_greeting"))
        assertNull(state.demo.pendingSelection)
        assertEquals("Xin chào Anna", state.input)
    }
    @Test fun noGuideCommandsAreHarmless() {
        val state = ChatUiState()
        listOf(DemoCommand.Next, DemoCommand.Previous, DemoCommand.Complete, DemoCommand.ConfirmReplacement).forEach {
            assertEquals(state, state.reduceDemo(it))
        }
    }
}
