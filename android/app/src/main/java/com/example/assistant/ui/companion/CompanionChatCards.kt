package com.example.assistant.ui.companion

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp

@OptIn(ExperimentalLayoutApi::class)
@Composable
fun CompanionChatCards(state: CompanionChatState, enabled: Boolean, onMood: (MoodChoice) -> Unit, onDismiss: () -> Unit, onSupport: (SupportChoice) -> Unit) {
    if (state.moodVisible) OutlinedCard(Modifier.fillMaxWidth()) {
        Column(Modifier.padding(8.dp)) {
            Text("Hôm nay bạn cảm thấy thế nào?")
            FlowRow(horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                MoodChoice.entries.forEach { choice -> TextButton(onClick = { onMood(choice) }, enabled = enabled) { Text(choice.label) } }
                TextButton(onClick = onDismiss) { Text("Để sau") }
            }
        }
    }
    if (state.supportMessageId != null) FlowRow(horizontalArrangement = Arrangement.spacedBy(4.dp)) {
        SupportChoice.entries.forEach { choice -> OutlinedButton(onClick = { onSupport(choice) }, enabled = enabled) { Text(choice.label) } }
    }
}
