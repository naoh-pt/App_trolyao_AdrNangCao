package com.example.assistant.ui.demo

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun DemoQuestionSheet(canSelect: Boolean, fontSize: Int, onCommand: (DemoCommand) -> Unit) {
    var tab by rememberSaveable { mutableIntStateOf(0) }
    var categoryName by rememberSaveable { mutableStateOf<String?>(null) }
    var scenarioId by rememberSaveable { mutableStateOf<String?>(null) }
    val category = DemoCategory.entries.firstOrNull { it.name == categoryName }
    val scenario = DemoQuestionCatalog.scenario(scenarioId.orEmpty())
    ModalBottomSheet(
        onDismissRequest = { onCommand(DemoCommand.Close) },
        sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true),
    ) {
        Column(Modifier.fillMaxHeight(.85f).padding(horizontal = 16.dp)) {
            Text("Câu hỏi và kịch bản demo", style = MaterialTheme.typography.titleLarge)
            if (category != null || scenario != null) {
                TextButton(onClick = { categoryName = null; scenarioId = null }) { Text("Quay lại") }
                Text(category?.title ?: scenario!!.title, style = MaterialTheme.typography.titleMedium)
                if (scenario != null) {
                    Text(scenario.description)
                    Button(onClick = { onCommand(DemoCommand.Start(scenario.id)) }, enabled = canSelect) {
                        Text("Bắt đầu kịch bản · ${scenario.questionIds.size} bước")
                    }
                }
                val questions = if (scenario != null) scenario.questionIds.mapNotNull(DemoQuestionCatalog::question)
                    else DemoQuestionCatalog.questions.filter { it.category == category }
                LazyColumn(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    items(questions, key = { it.id }) { question ->
                        OutlinedCard(
                            onClick = { onCommand(DemoCommand.Pick(question.id)) },
                            enabled = canSelect && question.enabled && question.category.enabled,
                            modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp),
                        ) {
                            Column(Modifier.padding(12.dp)) {
                                Text(question.prompt, fontSize = fontSize.sp, maxLines = 2, overflow = TextOverflow.Ellipsis)
                                Text(question.badges(), style = MaterialTheme.typography.labelSmall)
                            }
                        }
                    }
                }
            } else {
                TabRow(selectedTabIndex = tab) {
                    listOf("Kịch bản", "Theo nhóm").forEachIndexed { index, title ->
                        Tab(selected = tab == index, onClick = { tab = index }, text = { Text(title) })
                    }
                }
                LazyColumn(verticalArrangement = Arrangement.spacedBy(8.dp), contentPadding = PaddingValues(vertical = 12.dp)) {
                    if (tab == 0) {
                        items(DemoQuestionCatalog.scenarios.chunked(2)) { row ->
                            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                                row.forEach { item ->
                                    OutlinedCard(onClick = { scenarioId = item.id }, modifier = Modifier.weight(1f)) {
                                        Column(Modifier.padding(12.dp)) {
                                            Text(item.title, fontSize = fontSize.sp)
                                            Text(item.description, style = MaterialTheme.typography.bodySmall)
                                            Text("${item.questionIds.size} bước", style = MaterialTheme.typography.labelMedium)
                                        }
                                    }
                                }
                                if (row.size == 1) Spacer(Modifier.weight(1f))
                            }
                        }
                    } else {
                        items(DemoCategory.entries.chunked(2)) { row ->
                            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                                row.forEach { item ->
                                    OutlinedCard(onClick = { categoryName = item.name }, enabled = item.enabled,
                                        modifier = Modifier.weight(1f).heightIn(min = 72.dp)) {
                                        Column(Modifier.padding(12.dp)) {
                                            Text(item.title, fontSize = fontSize.sp)
                                            if (!item.enabled) Text("Sắp có ở Stage 14B", style = MaterialTheme.typography.labelSmall)
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}

private fun DemoQuestion.badges(): String = buildList {
    if (!enabled) add("Sắp có ở Stage 14B")
    if (requiresRag) add("Cần nạp tài liệu RAG")
    if (requiresAi) add("Có AI")
    if (requiresInternet) add("Cần Internet")
    if (requiresBackend) add("Cần backend")
}.joinToString(" · ")

@Composable
fun DemoScenarioControl(state: DemoState, canSelect: Boolean, onCommand: (DemoCommand) -> Unit) {
    val progress = state.progress ?: return
    val scenario = progress.scenario ?: return
    Column(Modifier.fillMaxWidth().padding(horizontal = 12.dp)) {
        TextButton(onClick = { onCommand(DemoCommand.ToggleExpanded) }, modifier = Modifier.fillMaxWidth()) {
            Text("${scenario.title} · ${progress.index + 1}/${scenario.questionIds.size}\n" +
                if (progress.completed) "Đã hoàn thành kịch bản" else progress.question?.prompt.orEmpty(),
                maxLines = 2, overflow = TextOverflow.Ellipsis)
        }
        if (state.expanded) {
            // Wrapping is limited to the expanded guide; the chat input row stays on one line.
            Column {
                Row {
                    TextButton(onClick = { onCommand(DemoCommand.Previous) }, enabled = canSelect && progress.index > 0) { Text("Câu trước") }
                    if (progress.index < scenario.questionIds.lastIndex) {
                        TextButton(onClick = { onCommand(DemoCommand.Next) }, enabled = canSelect) { Text("Câu tiếp theo") }
                    } else {
                        TextButton(onClick = { onCommand(DemoCommand.Complete) }, enabled = !progress.completed) { Text("Hoàn thành kịch bản") }
                    }
                }
                TextButton(onClick = { onCommand(DemoCommand.Stop) }) { Text("Dừng kịch bản") }
            }
        }
    }
}

@Composable
fun DemoReplacementDialog(selection: DemoSelection, onCommand: (DemoCommand) -> Unit) {
    AlertDialog(
        onDismissRequest = { onCommand(DemoCommand.CancelReplacement) },
        title = { Text("Thay bản nháp bằng câu hỏi demo?") },
        text = {
            LazyColumn {
                item { Text("Bản nháp hiện tại:\n${selection.originalDraft}") }
                item { Text("Câu hỏi mới:\n${DemoQuestionCatalog.question(selection.questionId)?.prompt.orEmpty()}") }
            }
        },
        confirmButton = { TextButton(onClick = { onCommand(DemoCommand.ConfirmReplacement) }) { Text("Thay bản nháp") } },
        dismissButton = { TextButton(onClick = { onCommand(DemoCommand.CancelReplacement) }) { Text("Giữ bản nháp") } },
    )
}
