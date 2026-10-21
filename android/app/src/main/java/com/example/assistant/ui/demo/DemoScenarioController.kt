package com.example.assistant.ui.demo

import com.example.assistant.ui.chat.ChatUiState

data class DemoProgress(val scenarioId: String, val index: Int = 0, val completed: Boolean = false) {
    val scenario: DemoScenario? get() = DemoQuestionCatalog.scenario(scenarioId)
    val question: DemoQuestion? get() = scenario?.questionIds?.getOrNull(index)?.let(DemoQuestionCatalog::question)
}

data class DemoSelection(val questionId: String, val progress: DemoProgress?, val originalDraft: String)

data class DemoState(
    val sheetOpen: Boolean = false,
    val progress: DemoProgress? = null,
    val expanded: Boolean = false,
    val pendingSelection: DemoSelection? = null,
)

sealed interface DemoCommand {
    data object Open : DemoCommand
    data object Close : DemoCommand
    data class Pick(val questionId: String) : DemoCommand
    data class Start(val scenarioId: String) : DemoCommand
    data object Next : DemoCommand
    data object Previous : DemoCommand
    data object Complete : DemoCommand
    data object Stop : DemoCommand
    data object ToggleExpanded : DemoCommand
    data object ConfirmReplacement : DemoCommand
    data object CancelReplacement : DemoCommand
}

/** No repository, send, speech, animation or coroutine dependency: selection changes draft/UI only. */
fun ChatUiState.reduceDemo(command: DemoCommand): ChatUiState {
    val canFill = !sending && pending == null

    fun fill(selection: DemoSelection, confirmed: Boolean = false): ChatUiState {
        val question = DemoQuestionCatalog.question(selection.questionId) ?: return this
        if (!canFill || !question.enabled || !question.category.enabled) return this
        if (input.isNotBlank() && input != question.prompt && !confirmed) {
            return copy(demo = demo.copy(pendingSelection = selection.copy(originalDraft = input)))
        }
        return copy(input = question.prompt, demo = demo.copy(
            sheetOpen = false, progress = selection.progress, pendingSelection = null,
        ))
    }

    fun selectProgress(progress: DemoProgress): ChatUiState {
        val question = progress.question ?: return this
        return fill(DemoSelection(question.id, progress, input))
    }

    return when (command) {
        DemoCommand.Open -> copy(demo = demo.copy(sheetOpen = true))
        DemoCommand.Close -> copy(demo = demo.copy(sheetOpen = false, pendingSelection = null))
        is DemoCommand.Pick -> fill(DemoSelection(command.questionId, null, input))
        is DemoCommand.Start -> {
            val scenario = DemoQuestionCatalog.scenario(command.scenarioId)
            if (scenario == null || scenario.questionIds.isEmpty() || scenario.questionIds.any {
                DemoQuestionCatalog.question(it)?.let { q -> q.enabled && q.category.enabled } != true
            }) this else selectProgress(DemoProgress(scenario.id))
        }
        DemoCommand.Next, DemoCommand.Previous -> {
            val progress = demo.progress
            val count = progress?.scenario?.questionIds?.size ?: 0
            val nextIndex = (progress?.index ?: 0) + if (command == DemoCommand.Next) 1 else -1
            if (progress == null || nextIndex !in 0 until count) this
            else selectProgress(progress.copy(index = nextIndex, completed = false))
        }
        DemoCommand.Complete -> {
            val progress = demo.progress
            if (progress != null && progress.index == (progress.scenario?.questionIds?.lastIndex ?: -1)) {
                copy(demo = demo.copy(progress = progress.copy(completed = true)))
            } else this
        }
        DemoCommand.Stop -> copy(demo = demo.copy(progress = null, expanded = false, pendingSelection = null))
        DemoCommand.ToggleExpanded -> copy(demo = demo.copy(expanded = !demo.expanded))
        DemoCommand.CancelReplacement -> copy(demo = demo.copy(pendingSelection = null))
        DemoCommand.ConfirmReplacement -> {
            val selection = demo.pendingSelection
            if (selection == null || !canFill) this
            // If another input source changed the draft, require review of the new draft too.
            else if (input != selection.originalDraft) copy(demo = demo.copy(pendingSelection = selection.copy(originalDraft = input)))
            else fill(selection, confirmed = true)
        }
    }
}
