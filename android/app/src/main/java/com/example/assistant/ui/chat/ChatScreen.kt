package com.example.assistant.ui.chat

import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.consumeWindowInsets
import androidx.compose.foundation.layout.fillMaxHeight
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
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import android.content.ActivityNotFoundException
import android.content.Intent
import android.speech.RecognizerIntent
import android.widget.Toast
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.example.assistant.R
import androidx.compose.foundation.layout.Spacer
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.ElevatedButton
import androidx.compose.ui.text.font.FontWeight
import com.example.assistant.data.remote.AssistantActionDto
import com.example.assistant.domain.LocalAnimationFpsSettings
import com.example.assistant.domain.ChatDisplaySettings
import com.example.assistant.domain.LocalChatDisplaySettings
import com.example.assistant.domain.LocalSpeechSettings
import com.example.assistant.domain.SpeechSettings
import com.example.assistant.speech.LocalTtsEnabled
import com.example.assistant.speech.TtsProgressListener
import com.example.assistant.speech.rememberVietnameseTts
import com.example.assistant.ui.components.CharacterAvatar
import com.example.assistant.ui.components.CuteBackground

private val UserShape = RoundedCornerShape(20.dp, 20.dp, 4.dp, 20.dp)
private val BotShape = RoundedCornerShape(20.dp, 20.dp, 20.dp, 4.dp)
private val ChatPanelShape = RoundedCornerShape(topStart = 28.dp, topEnd = 28.dp)

/** Fixed character display height for phone layout (preserving full-body aspect ratio). */
private val CharacterDisplayHeight = 360.dp

/** Fractional height of the foreground chat panel when keyboard is closed (~50-55%). */
private const val ChatPanelClosedFraction = 0.53f

/** Fractional height of the foreground chat panel when keyboard is open (1.25x closed height = 66.25%). */
private const val ChatPanelKeyboardFraction = ChatPanelClosedFraction * 1.25f

/** Soft anime-style frosted vertical gradient (light blue/white, 60% -> 82% -> 95% opacity). */
private val FrostedPanelGradient = Brush.verticalGradient(
    0.0f to Color(0xFFEAF3FC).copy(alpha = 0.60f),
    0.40f to Color(0xFFF2F7FD).copy(alpha = 0.82f),
    1.0f to Color(0xFFF9FBFE).copy(alpha = 0.95f),
)

@Composable
fun ChatScreen(
    vm: ChatViewModel,
    onBack: () -> Unit,
    onHistory: () -> Unit,
    ttsEnabled: Boolean,
) = ChatScreen(
    vm = vm,
    onBack = onBack,
    onHistory = onHistory,
    speechSettings = LocalSpeechSettings.current.copy(enabled = ttsEnabled),
    displaySettings = LocalChatDisplaySettings.current,
)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ChatScreen(
    vm: ChatViewModel,
    onBack: () -> Unit,
    onHistory: () -> Unit,
    speechSettings: SpeechSettings = LocalSpeechSettings.current,
    displaySettings: ChatDisplaySettings = LocalChatDisplaySettings.current,
) {
    val ui by vm.ui.collectAsStateWithLifecycle()
    val messages by vm.messages.collectAsStateWithLifecycle()
    val listState = rememberLazyListState()
    val imeVisible = WindowInsets.ime.getBottom(LocalDensity.current) > 0
    val panelFraction = if (imeVisible) ChatPanelKeyboardFraction else ChatPanelClosedFraction
    val pending = ui.pending
    val error = ui.error

    val ttsHelper = rememberVietnameseTts()
    val context = LocalContext.current

    val voiceLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.StartActivityForResult(),
    ) { result ->
        val recognizedText = extractSpeechRecognitionResult(result.resultCode, result.data)
        vm.onVoiceInputResult(recognizedText)
    }

    val canVoiceInput = ui.online && !ui.sending && pending == null
    val onLaunchVoiceInput: () -> Unit = {
        if (canVoiceInput) {
            val intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
                putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
                putExtra(RecognizerIntent.EXTRA_LANGUAGE, "vi-VN")
                putExtra(RecognizerIntent.EXTRA_PROMPT, "Mời bạn nói câu hỏi")
            }
            try {
                voiceLauncher.launch(intent)
            } catch (e: ActivityNotFoundException) {
                Toast.makeText(context, "Thiết bị chưa hỗ trợ nhập bằng giọng nói.", Toast.LENGTH_SHORT).show()
            } catch (e: Exception) {
                Toast.makeText(context, "Không thể khởi động nhận dạng giọng nói: ${e.message}", Toast.LENGTH_SHORT).show()
            }
        }
    }

    DisposableEffect(ttsHelper, vm) {
        ttsHelper.listener = object : TtsProgressListener {
            override fun onStart(utteranceId: String) {
                vm.onSpeechStarted(utteranceId)
            }

            override fun onDone(utteranceId: String) {
                vm.onSpeechCompleted(utteranceId)
            }

            override fun onError(utteranceId: String, errorCode: Int?) {
                vm.onSpeechError(utteranceId)
            }

            override fun onStop(utteranceId: String, interrupted: Boolean) {
                vm.onSpeechStopped(utteranceId)
            }
        }
        onDispose {
            ttsHelper.listener = null
            ttsHelper.stop()
            vm.onScreenDisposed()
        }
    }

    LaunchedEffect(speechSettings.enabled) {
        vm.setTtsEnabled(speechSettings.enabled)
        if (!speechSettings.enabled) {
            ttsHelper.stop()
        }
    }

    LaunchedEffect(vm, speechSettings) {
        vm.speechEvents.collect { event ->
            if (speechSettings.enabled && event.text.isNotBlank()) {
                ttsHelper.speak(
                    text = event.text,
                    rate = speechSettings.speechRate,
                    pitch = speechSettings.pitch,
                    utteranceId = event.utteranceId,
                )
            } else {
                vm.onSpeechNotStarted(event.utteranceId)
            }
        }
    }

    LaunchedEffect(vm) {
        vm.stopSpeechEvents.collect {
            ttsHelper.stop()
        }
    }

    val fpsSettings = LocalAnimationFpsSettings.current
    LaunchedEffect(fpsSettings) {
        vm.setFpsSettings(fpsSettings)
    }

    val onActionClick: (AssistantActionDto) -> Unit = { actionDto ->
        if (vm.canClickAction()) {
            launchActionSafely(
                context = context,
                dto = actionDto,
                onError = { errorMsg ->
                    Toast.makeText(context, errorMsg, Toast.LENGTH_SHORT).show()
                },
            )
        }
    }

    val itemCount = messages.size +
        (if (pending != null) 1 else 0) +
        (if (ui.sending) 1 else 0) +
        (if (error != null) 1 else 0)
    LaunchedEffect(itemCount, imeVisible) {
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
            Box(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(padding)
                    .consumeWindowInsets(padding),
            ) {
                // Character background layer (stable size, independent of message count)
                CharacterAvatar(
                    state = ui.characterState,
                    emotion = ui.emotion,
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(CharacterDisplayHeight)
                        .align(Alignment.TopCenter),
                    onOneShotFinished = vm::onCharacterAnimationFinished,
                )

                // Foreground chat panel (soft frosted gradient container, dynamic height based on IME)
                Surface(
                    modifier = Modifier
                        .fillMaxWidth()
                        .fillMaxHeight(panelFraction)
                        .align(Alignment.BottomCenter)
                        .imePadding(),
                    shape = ChatPanelShape,
                    color = Color.Transparent,
                    border = BorderStroke(1.dp, Color.White.copy(alpha = 0.75f)),
                    shadowElevation = 0.dp,
                ) {
                    Box(
                        modifier = Modifier
                            .fillMaxSize()
                            .background(FrostedPanelGradient),
                    ) {
                        Column(
                            modifier = Modifier.fillMaxSize(),
                        ) {
                            if (!ui.online) {
                                Surface(
                                    color = MaterialTheme.colorScheme.errorContainer,
                                    shape = RoundedCornerShape(20.dp),
                                    modifier = Modifier
                                        .fillMaxWidth()
                                        .padding(horizontal = 12.dp, vertical = 4.dp),
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
                                modifier = Modifier
                                    .weight(1f)
                                    .fillMaxWidth(),
                                contentPadding = PaddingValues(12.dp),
                                verticalArrangement = Arrangement.spacedBy(8.dp),
                            ) {
                                items(messages, key = { it.id }) { m ->
                                    val action = ui.activeActions[m.id]
                                    MessageBubble(
                                        text = m.text,
                                        isUser = m.role == "user",
                                        fontSizeSp = displaySettings.fontSizeSp,
                                        lineHeightSp = displaySettings.lineHeightSp,
                                        action = action,
                                        onActionClick = onActionClick,
                                    )
                                }
                                if (pending != null) {
                                    item(key = "pending") {
                                        MessageBubble(
                                            text = pending,
                                            isUser = true,
                                            dimmed = true,
                                            fontSizeSp = displaySettings.fontSizeSp,
                                            lineHeightSp = displaySettings.lineHeightSp,
                                        )
                                    }
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
                                Modifier
                                    .fillMaxWidth()
                                    .padding(horizontal = 12.dp, vertical = 8.dp),
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
                                IconButton(
                                    onClick = onLaunchVoiceInput,
                                    enabled = canVoiceInput,
                                ) {
                                    Icon(
                                        painter = painterResource(R.drawable.ic_mic),
                                        contentDescription = "Nhập bằng giọng nói",
                                        tint = if (canVoiceInput) MaterialTheme.colorScheme.primary else Color.Gray.copy(alpha = 0.5f),
                                    )
                                }
                                FilledIconButton(onClick = vm::send, enabled = canSend, shape = CircleShape) {
                                    Icon(Icons.AutoMirrored.Filled.Send, contentDescription = "Gửi")
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun MessageBubble(
    text: String,
    isUser: Boolean,
    dimmed: Boolean = false,
    fontSizeSp: Int = ChatDisplaySettings.DEFAULT_FONT_SIZE_SP,
    lineHeightSp: Int = fontSizeSp + ChatDisplaySettings.LINE_HEIGHT_OFFSET_SP,
    action: AssistantActionDto? = null,
    onActionClick: ((AssistantActionDto) -> Unit)? = null,
) {
    Column(
        modifier = Modifier.fillMaxWidth(),
        horizontalAlignment = if (isUser) Alignment.End else Alignment.Start,
    ) {
        Surface(
            shape = if (isUser) UserShape else BotShape,
            color = if (isUser) MaterialTheme.colorScheme.primary else Color.White,
            contentColor = if (isUser) MaterialTheme.colorScheme.onPrimary else MaterialTheme.colorScheme.onSurface,
            shadowElevation = if (isUser) 0.dp else 2.dp,
            modifier = Modifier.widthIn(max = 300.dp).alpha(if (dimmed) 0.6f else 1f),
        ) {
            Text(
                text = text,
                fontSize = fontSizeSp.sp,
                lineHeight = lineHeightSp.sp,
                modifier = Modifier.padding(horizontal = 12.dp, vertical = 8.dp),
            )
        }

        if (!isUser && action != null && onActionClick != null) {
            Spacer(Modifier.height(6.dp))
            ActionCardButton(
                action = action,
                onClick = { onActionClick(action) },
            )
        }
    }
}

@Composable
private fun ActionCardButton(
    action: AssistantActionDto,
    onClick: () -> Unit,
) {
    val iconEmoji = when (action.type) {
        AssistantActionTypes.SET_TIMER -> "⏰"
        AssistantActionTypes.CREATE_CALENDAR_EVENT -> "📅"
        AssistantActionTypes.MAP_SEARCH -> "📍"
        else -> "✨"
    }
    val label = actionButtonLabel(action)

    ElevatedButton(
        onClick = onClick,
        shape = RoundedCornerShape(16.dp),
        colors = ButtonDefaults.elevatedButtonColors(
            containerColor = Color.White,
            contentColor = MaterialTheme.colorScheme.primary,
        ),
        elevation = ButtonDefaults.elevatedButtonElevation(defaultElevation = 2.dp),
        contentPadding = PaddingValues(horizontal = 14.dp, vertical = 8.dp),
    ) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(6.dp),
        ) {
            Text(iconEmoji, fontSize = 16.sp)
            Text(
                text = label,
                style = MaterialTheme.typography.labelLarge,
                fontWeight = FontWeight.SemiBold,
                color = MaterialTheme.colorScheme.primary,
            )
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
