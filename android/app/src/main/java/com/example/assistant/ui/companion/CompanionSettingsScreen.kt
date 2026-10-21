package com.example.assistant.ui.companion

import androidx.activity.compose.BackHandler
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.contentDescription
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.example.assistant.domain.*

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun CompanionSettingsScreen(vm: CompanionViewModel, onBack: () -> Unit) {
    val ui by vm.ui.collectAsStateWithLifecycle()
    var discard by rememberSaveable { mutableStateOf(false) }
    val leave = { if (!ui.saving) { if (ui.dirty) discard = true else onBack() } }
    BackHandler(ui.dirty || ui.saving) { leave() }
    val draft = ui.draft
    val enabled = !ui.loading && !ui.saving
    val canEdit = enabled && ui.loaded
    Scaffold(topBar = {
        TopAppBar(title = { Text("Cá nhân hóa Anna") }, navigationIcon = {
            IconButton(onClick = leave, enabled = !ui.saving) { Icon(Icons.AutoMirrored.Filled.ArrowBack, "Quay lại") }
        })
    }) { padding ->
        LazyColumn(Modifier.fillMaxSize().padding(padding).padding(horizontal = 16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp), contentPadding = PaddingValues(vertical = 16.dp)) {
            if (ui.loading || ui.saving) item { LinearProgressIndicator(Modifier.fillMaxWidth()) }
            item {
                OutlinedTextField(value = draft.preferredName.orEmpty(), onValueChange = { vm.edit(draft.copy(preferredName = it)) },
                    label = { Text("Tên Anna gọi bạn") }, singleLine = true, enabled = canEdit,
                    textStyle = MaterialTheme.typography.bodyLarge.copy(fontSize = LocalChatDisplaySettings.current.fontSizeSp.sp),
                    isError = !validPreferredName(draft.preferredName), modifier = Modifier.fillMaxWidth(),
                    supportingText = { Text("Tùy chọn · tối đa 30 ký tự · Anna sẽ dùng tên một cách tự nhiên, vừa phải.") })
            }
            item { PreferenceSelector("Cách xưng hô", draft.addressStyle, AddressStyle.entries, { it.label }, canEdit) { vm.edit(draft.copy(addressStyle = it)) } }
            item { PreferenceSelector("Mức độ hài hước", draft.humorLevel, HumorLevel.entries, { it.label }, canEdit) { vm.edit(draft.copy(humorLevel = it)) } }
            item { PreferenceSelector("Độ dài phản hồi", draft.responseLength, ResponseLength.entries, { it.label }, canEdit) { vm.edit(draft.copy(responseLength = it)) } }
            item { PreferenceSelector("Cách đồng hành", draft.supportStyle, SupportStyle.entries, { it.label }, canEdit) { vm.edit(draft.copy(supportStyle = it)) } }
            item {
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                    Text("Hỏi thăm cảm xúc mỗi ngày", modifier = Modifier.weight(1f))
                    Switch(checked = draft.moodCheckInEnabled, onCheckedChange = { vm.edit(draft.copy(moodCheckInEnabled = it)) }, enabled = canEdit,
                        modifier = Modifier.semantics { contentDescription = "Hỏi thăm cảm xúc mỗi ngày" })
                }
            }
            item { Text("Chỉ hỏi khi vào cuộc trò chuyện. Không thông báo nền và không lưu lịch sử tâm trạng.") }
            ui.error?.let { error -> item {
                Text(error, color = MaterialTheme.colorScheme.error)
                TextButton(onClick = vm::refresh, enabled = enabled) { Text("Tải lại") }
            } }
            if (ui.success) item { Text("Đã lưu thay đổi.") }
            item { Button(onClick = vm::save, enabled = canEdit && draft.valid(), modifier = Modifier.fillMaxWidth()) { Text(if (ui.saving) "Đang lưu…" else "Lưu thay đổi") } }
        }
    }
    if (discard) AlertDialog(onDismissRequest = { discard = false }, title = { Text("Rời khi chưa lưu?") },
        text = { Text("Thay đổi chưa lưu sẽ được bỏ qua.") },
        confirmButton = { TextButton(onClick = { discard = false; onBack() }) { Text("Bỏ thay đổi") } },
        dismissButton = { TextButton(onClick = { discard = false }) { Text("Tiếp tục chỉnh sửa") } })
}

@Composable
private fun <T> PreferenceSelector(label: String, selected: T, options: List<T>, text: (T) -> String, enabled: Boolean, onSelect: (T) -> Unit) {
    var open by remember { mutableStateOf(false) }
    Column {
        Text(label)
        Box {
            OutlinedButton(onClick = { open = true }, enabled = enabled, modifier = Modifier.fillMaxWidth().semantics { contentDescription = "$label: ${text(selected)}" }) { Text(text(selected), fontSize = LocalChatDisplaySettings.current.fontSizeSp.sp) }
            DropdownMenu(expanded = open, onDismissRequest = { open = false }) {
                options.forEach { item -> DropdownMenuItem(text = { Text(text(item)) }, onClick = { open = false; onSelect(item) }) }
            }
        }
    }
}
