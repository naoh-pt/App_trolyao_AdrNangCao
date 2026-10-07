package com.example.assistant.ui.chat

import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.consumeWindowInsets
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.ime
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.automirrored.filled.Send
import androidx.compose.material.icons.filled.Add
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilledIconButton
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.example.assistant.ui.components.CharacterAvatar
import com.example.assistant.ui.components.CuteBackground

private val UserShape = RoundedCornerShape(20.dp, 20.dp, 4.dp, 20.dp)
private val BotShape = RoundedCornerShape(20.dp, 20.dp, 20.dp, 4.dp)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ChatScreen(vm: ChatViewModel, onBack: () -> Unit, onHistory: () -> Unit) {
    val ui by vm.ui.collectAsStateWithLifecycle()
    val messages by vm.messages.collectAsStateWithLifecycle()
    val listState = rememberLazyListState()
    val imeVisible = WindowInsets.ime.getBottom(LocalDensity.current) > 0
    val pending = ui.pending
    val error = ui.error

    val itemCount = messages.size +
        (if (pending != null) 1 else 0) +
        (if (ui.sending) 1 else 0) +
        (if (error != null) 1 else 0)
    LaunchedEffect(itemCount) {
        if (itemCount > 0) listState.animateScrollToItem(itemCount - 1)
    }

    CuteBackground {
        Scaffold(
            containerColor = Color.Transparent,
            topBar = {
                TopAppBar(
                    colors = TopAppBarDefaults.topAppBarColors(containerColor = Color.Transparent),
                    title = { Text("Trò chuyện 💬") },
                    navigationIcon = {
                        IconButton(onClick = onBack) {
                            Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Quay lại")
                        }
                    },
                    actions = {
                        IconButton(onClick = vm::newChat, enabled = !ui.sending) {
                            Icon(Icons.Filled.Add, contentDescription = "Chat mới")
                        }
                        TextButton(onClick = onHistory) { Text("Lịch sử") }
                    },
                )
            },
        ) { padding ->
            Column(
                Modifier
                    .fillMaxSize()
                    .padding(padding)
                    .consumeWindowInsets(padding)
                    .imePadding(),
            ) {
                // Thu nhỏ nhân vật khi bàn phím mở để ô nhập luôn thấy được.
                CharacterAvatar(
                    state = ui.characterState,
                    emotion = ui.emotion,
                    modifier = Modifier.fillMaxWidth().height(if (imeVisible) 80.dp else 210.dp),
                    onOneShotFinished = vm::onCharacterAnimationFinished,
                )

                if (!ui.online) {
                    Surface(
                        color = MaterialTheme.colorScheme.errorContainer,
                        shape = RoundedCornerShape(20.dp),
                        modifier = Modifier.fillMaxWidth().padding(horizontal = 12.dp, vertical = 4.dp),
                    ) {
                        Row(
                            Modifier.padding(start = 16.dp, end = 4.dp),
                            verticalAlignment = Alignment.CenterVertically,
                        ) {
                            Text(
                                "Đang offline — chỉ xem được lịch sử đã lưu.",
                                modifier = Modifier.weight(1f),
                                style = MaterialTheme.typography.bodySmall,
                            )
                            TextButton(onClick = vm::refresh) { Text("Thử lại") }
                        }
                    }
                }

                LazyColumn(
                    state = listState,
                    modifier = Modifier.weight(1f).fillMaxWidth(),
                    contentPadding = PaddingValues(12.dp),
                    verticalArrangement = Arrangement.spacedBy(8.dp),
                ) {
                    items(messages, key = { it.id }) { m ->
                        MessageBubble(text = m.text, isUser = m.role == "user")
                    }
                    if (pending != null) {
                        item(key = "pending") { MessageBubble(text = pending, isUser = true, dimmed = true) }
                    }
                    if (ui.sending) {
                        item(key = "thinking") { TypingBubble() }
                    }
                    if (error != null) {
                        item(key = "error") {
                            Column {
                                Text(
                                    error,
                                    color = MaterialTheme.colorScheme.error,
                                    style = MaterialTheme.typography.bodySmall,
                                )
                                if (pending != null) {
                                    Row {
                                        TextButton(onClick = vm::send, enabled = ui.online) { Text("Thử lại") }
                                        TextButton(onClick = vm::editPending) { Text("Sửa tin nhắn") }
                                    }
                                }
                            }
                        }
                    }
                }

                val canSend = ui.online && !ui.sending && (pending != null || ui.input.isNotBlank())
                Row(
                    Modifier.fillMaxWidth().padding(horizontal = 12.dp, vertical = 8.dp),
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                ) {
                    OutlinedTextField(
                        value = ui.input,
                        onValueChange = vm::onInputChange,
                        modifier = Modifier.weight(1f),
                        placeholder = { Text("Nhắn gì đó cho mình nhé~") },
                        maxLines = 4,
                        shape = RoundedCornerShape(28.dp),
                        enabled = pending == null && ui.online,
                        colors = OutlinedTextFieldDefaults.colors(
                            focusedContainerColor = Color.White,
                            unfocusedContainerColor = Color.White,
                            disabledContainerColor = Color(0xFFF1F1F4),
                        ),
                    )
                    FilledIconButton(onClick = vm::send, enabled = canSend, shape = CircleShape) {
                        Icon(Icons.AutoMirrored.Filled.Send, contentDescription = "Gửi")
                    }
                }
            }
        }
    }
}

@Composable
private fun MessageBubble(text: String, isUser: Boolean, dimmed: Boolean = false) {
    Row(
        Modifier.fillMaxWidth(),
        horizontalArrangement = if (isUser) Arrangement.End else Arrangement.Start,
    ) {
        Surface(
            shape = if (isUser) UserShape else BotShape,
            color = if (isUser) MaterialTheme.colorScheme.primary else Color.White,
            contentColor = if (isUser) MaterialTheme.colorScheme.onPrimary else MaterialTheme.colorScheme.onSurface,
            shadowElevation = if (isUser) 0.dp else 2.dp,
            modifier = Modifier.widthIn(max = 300.dp).alpha(if (dimmed) 0.6f else 1f),
        ) {
            Text(text, modifier = Modifier.padding(horizontal = 14.dp, vertical = 10.dp))
        }
    }
}

/** Ba chấm nhấp nháy khi trợ lý đang "suy nghĩ". */
@Composable
private fun TypingBubble() {
    val t = rememberInfiniteTransition(label = "dots")
    val a1 by t.animateFloat(0.25f, 1f, infiniteRepeatable(tween(500), RepeatMode.Reverse), label = "a1")
    val a2 by t.animateFloat(0.25f, 1f, infiniteRepeatable(tween(650), RepeatMode.Reverse), label = "a2")
    val a3 by t.animateFloat(0.25f, 1f, infiniteRepeatable(tween(800), RepeatMode.Reverse), label = "a3")
    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        Surface(shape = BotShape, color = Color.White, shadowElevation = 2.dp) {
            Row(
                Modifier.padding(horizontal = 16.dp, vertical = 12.dp),
                horizontalArrangement = Arrangement.spacedBy(4.dp),
            ) {
                listOf(a1, a2, a3).forEach { a ->
                    Text("●", color = MaterialTheme.colorScheme.secondary, fontSize = 12.sp, modifier = Modifier.alpha(a))
                }
            }
        }
        Text("Đang suy nghĩ~", style = MaterialTheme.typography.bodySmall)
    }
}
