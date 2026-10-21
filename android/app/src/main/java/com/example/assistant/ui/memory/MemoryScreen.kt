package com.example.assistant.ui.memory

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MemoryScreen(vm: MemoryViewModel, onBack: () -> Unit) {
    val ui by vm.ui.collectAsStateWithLifecycle()
    Scaffold(topBar = {
        TopAppBar(title = { Text("Trí nhớ của Anna") }, navigationIcon = {
            IconButton(onClick = onBack) { Icon(Icons.AutoMirrored.Filled.ArrowBack, "Quay lại") }
        })
    }) { padding ->
        LazyColumn(Modifier.fillMaxSize().padding(padding).padding(horizontal = 16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp), contentPadding = PaddingValues(vertical = 12.dp)) {
            item { Text("Chỉ lưu khi bạn yêu cầu. Nhắc một lần khi vào cuộc trò chuyện; không nhắc khi ứng dụng đóng.") }
            if (ui.loading) item { LinearProgressIndicator(Modifier.fillMaxWidth()) }
            ui.error?.let { error -> item {
                Text(error, color = MaterialTheme.colorScheme.error)
                TextButton(onClick = vm::refresh, enabled = !ui.loading) { Text("Thử lại") }
            } }
            if (!ui.loading && ui.items.isEmpty() && ui.error == null) item {
                Text("Anna chưa lưu điều gì về bạn. Hãy nhắn “Anna hãy nhớ: ...” trong cuộc trò chuyện.")
            }
            items(ui.items, key = { it.id }) { memory ->
                OutlinedCard(Modifier.fillMaxWidth()) {
                    Column(Modifier.padding(12.dp)) {
                        Text(memory.content, style = MaterialTheme.typography.bodyLarge)
                        Text(if (memory.active) "Đang hoạt động" else "Đã lưu trữ (quá hạn)")
                        Text(when (memory.kind) {
                            "profile" -> "Hồ sơ"
                            "preference" -> "Sở thích"
                            "event" -> "Sự kiện"
                            else -> "Thông tin chung"
                        })
                        memory.eventDate?.let { Text("Ngày sự kiện: $it") }
                        memory.remindOn?.let { Text("Bắt đầu nhắc: $it") }
                        Text(if (memory.remindedAt != null) "Đã nhắc" else if (memory.remindOn != null) "Chưa nhắc" else "Không đặt lời nhắc")
                        TextButton(onClick = { vm.delete(memory.id) }, enabled = !ui.loading) { Text("Xóa thông tin") }
                    }
                }
            }
            if (ui.items.isNotEmpty()) item {
                OutlinedButton(onClick = vm::requestClear, enabled = !ui.loading) { Text("Xóa tất cả trí nhớ") }
            }
        }
    }
    if (ui.confirmClear) AlertDialog(
        onDismissRequest = vm::cancelClear,
        title = { Text("Xóa tất cả trí nhớ?") },
        text = { Text("Chỉ xóa những thông tin đã lưu, giữ nguyên lịch sử trò chuyện.") },
        confirmButton = { TextButton(onClick = vm::confirmClear) { Text("Xóa tất cả") } },
        dismissButton = { TextButton(onClick = vm::cancelClear) { Text("Hủy") } },
    )
}
