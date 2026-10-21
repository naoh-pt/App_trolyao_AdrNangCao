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
    @Test fun disabledWeatherCannotBePicked() {
        val state = start()
        assertEquals(state, state.reduceDemo(DemoCommand.Pick("weather_now")))
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
