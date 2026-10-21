package com.example.assistant.ui.settings

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.example.assistant.domain.AnimationFpsSettings
import com.example.assistant.domain.ChatDisplaySettings
import com.example.assistant.domain.SpeechSettings
import com.example.assistant.speech.VietnameseTtsHelper
import com.example.assistant.speech.rememberVietnameseTts
import com.example.assistant.ui.character.CharacterAnimationPlayer
import com.example.assistant.ui.character.CharacterFrameCatalog
import com.example.assistant.ui.components.CuteBackground

private data class AnimationActionItem(
    val actionName: String,
    val displayName: String,
)

private val AnimationActionItems = listOf(
    AnimationActionItem(AnimationFpsSettings.ACTION_IDLE, "Chờ"),
    AnimationActionItem(AnimationFpsSettings.ACTION_THINKING, "Suy nghĩ"),
    AnimationActionItem(AnimationFpsSettings.ACTION_TALK, "Nói"),
    AnimationActionItem(AnimationFpsSettings.ACTION_HAPPY, "Vui"),
    AnimationActionItem(AnimationFpsSettings.ACTION_SAD, "Buồn"),
    AnimationActionItem(AnimationFpsSettings.ACTION_SURPRISED, "Ngạc nhiên"),
)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SettingsScreen(vm: SettingsViewModel, onBack: () -> Unit, onMemory: () -> Unit = {}) {
    val ui by vm.ui.collectAsStateWithLifecycle()
    val ttsHelper = rememberVietnameseTts()
    CuteBackground {
        Scaffold(
            containerColor = Color.Transparent,
            topBar = {
                TopAppBar(
                    colors = TopAppBarDefaults.topAppBarColors(containerColor = Color.Transparent),
                    title = { Text("Cài đặt ⚙️") },
                    navigationIcon = {
                        IconButton(onClick = onBack) {
                            Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Quay lại")
                        }
                    },
                )
            },
        ) { padding ->
            LazyColumn(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(padding)
                    .padding(horizontal = 16.dp),
                verticalArrangement = Arrangement.spacedBy(16.dp),
                contentPadding = PaddingValues(vertical = 16.dp),
            ) {
                // Section 1: Backend Connection
                item {
                    OutlinedButton(onClick = onMemory, modifier = Modifier.fillMaxWidth()) { Text("Trí nhớ của Anna") }
                }
                item {
                    BackendSettingsSection(ui = ui, vm = vm)
                }

                // Section 2: Speech Settings (Text-to-Speech)
                item {
                    SpeechSettingsSection(ui = ui, vm = vm, ttsHelper = ttsHelper)
                }

                // Section 2.5: Chat Display Settings (Message Font Size)
                item {
                    Column {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.SpaceBetween,
                        ) {
                            Text("Hiệu ứng hiện chữ dần", modifier = Modifier.weight(1f))
                            Switch(
                                checked = ui.chatDisplaySettings.typewriterEnabled,
                                onCheckedChange = vm::setTypewriterEnabled,
                                modifier = Modifier.semantics { contentDescription = "Hiệu ứng hiện chữ dần" },
                            )
                        }
                        ChatDisplaySettingsSection(ui = ui, vm = vm)
                    }
                }

                // Section 3: Character Animation Settings & Preview
                item {
                    AnimationSettingsHeader()
                }

                item {
                    AnimationPreviewCard(ui = ui)
                }

                item {
                    AnimationControlsCard(ui = ui, vm = vm)
                }

                item {
                    AnimationActionButtons(vm = vm)
                }
            }
        }
    }
}

@Composable
private fun BackendSettingsSection(ui: SettingsUiState, vm: SettingsViewModel) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(20.dp),
        colors = CardDefaults.cardColors(containerColor = Color.White.copy(alpha = 0.85f)),
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Text(
                "Kết nối backend",
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.Bold,
                color = MaterialTheme.colorScheme.primary,
            )
            OutlinedTextField(
                value = ui.url,
                onValueChange = vm::onUrlChange,
                label = { Text("Địa chỉ backend") },
                singleLine = true,
                shape = RoundedCornerShape(28.dp),
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Uri),
                colors = OutlinedTextFieldDefaults.colors(
                    focusedContainerColor = Color.White,
                    unfocusedContainerColor = Color.White,
                ),
                modifier = Modifier.fillMaxWidth(),
            )
            Text(
                "Máy thật: http://<IP LAN của laptop>:8000 (ví dụ http://192.168.1.10:8000).\n" +
                    "Emulator: http://10.0.2.2:8000. Không dùng localhost.",
                style = MaterialTheme.typography.bodySmall,
            )
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedButton(onClick = vm::test, enabled = !ui.busy, shape = CircleShape) {
                    Text(if (ui.busy) "Đang kiểm tra…" else "Kiểm tra kết nối")
                }
                Button(onClick = vm::save, enabled = !ui.busy, shape = CircleShape) { Text("Lưu") }
            }
            ui.status?.let {
                Text(
                    it,
                    color = if (ui.statusOk) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.error,
                )
            }
        }
    }
}

@Composable
private fun SpeechSettingsSection(
    ui: SettingsUiState,
    vm: SettingsViewModel,
    ttsHelper: VietnameseTtsHelper,
) {
    val speech = ui.speechSettings
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(20.dp),
        colors = CardDefaults.cardColors(containerColor = Color.White.copy(alpha = 0.85f)),
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Text(
                "Giọng nói",
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.Bold,
                color = MaterialTheme.colorScheme.primary,
            )

            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.SpaceBetween,
            ) {
                Text(
                    "Đọc câu trả lời",
                    style = MaterialTheme.typography.bodyLarge,
                    fontWeight = FontWeight.Medium,
                )
                Switch(
                    checked = speech.enabled,
                    onCheckedChange = { isChecked ->
                        vm.setTtsEnabled(isChecked)
                        if (!isChecked) {
                            ttsHelper.stop()
                        }
                    },
                )
            }

            HorizontalDivider(
                color = Color.LightGray.copy(alpha = 0.3f),
                thickness = 0.5.dp,
            )

            VoiceControlRow(
                label = "Tốc độ đọc",
                displayValue = SpeechSettings.formatMultiplier(speech.speechRate),
                canDecrease = speech.canDecreaseRate(),
                canIncrease = speech.canIncreaseRate(),
                onDecrease = {
                    ttsHelper.stop()
                    vm.decreaseSpeechRate()
                },
                onIncrease = {
                    ttsHelper.stop()
                    vm.increaseSpeechRate()
                },
                decreaseContentDescription = "Giảm tốc độ đọc",
                increaseContentDescription = "Tăng tốc độ đọc",
            )

            HorizontalDivider(
                color = Color.LightGray.copy(alpha = 0.3f),
                thickness = 0.5.dp,
            )

            VoiceControlRow(
                label = "Cao độ giọng",
                displayValue = SpeechSettings.formatMultiplier(speech.pitch),
                canDecrease = speech.canDecreasePitch(),
                canIncrease = speech.canIncreasePitch(),
                onDecrease = {
                    ttsHelper.stop()
                    vm.decreasePitch()
                },
                onIncrease = {
                    ttsHelper.stop()
                    vm.increasePitch()
                },
                decreaseContentDescription = "Giảm cao độ giọng",
                increaseContentDescription = "Tăng cao độ giọng",
            )

            HorizontalDivider(
                color = Color.LightGray.copy(alpha = 0.3f),
                thickness = 0.5.dp,
            )

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                OutlinedButton(
                    onClick = {
                        ttsHelper.speak("Xin chào, mình là trợ lý ảo của bạn.", speech)
                    },
                    enabled = speech.enabled && ttsHelper.isReady,
                    shape = CircleShape,
                ) {
                    Text("Nghe thử")
                }

                OutlinedButton(
                    onClick = {
                        ttsHelper.stop()
                        vm.restoreVoiceDefaults()
                    },
                    shape = CircleShape,
                    modifier = Modifier.semantics {
                        contentDescription = "Khôi phục giọng mặc định"
                    },
                ) {
                    Text("Khôi phục giọng mặc định")
                }
            }

            ttsHelper.errorMessage.value?.let { errorMsg ->
                Text(
                    errorMsg,
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.error,
                )
            }
        }
    }
}

@Composable
private fun VoiceControlRow(
    label: String,
    displayValue: String,
    canDecrease: Boolean,
    canIncrease: Boolean,
    onDecrease: () -> Unit,
    onIncrease: () -> Unit,
    decreaseContentDescription: String,
    increaseContentDescription: String,
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 2.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Text(
            text = label,
            style = MaterialTheme.typography.bodyLarge,
            fontWeight = FontWeight.Medium,
            modifier = Modifier.weight(1f),
        )

        IconButton(
            onClick = onDecrease,
            enabled = canDecrease,
            modifier = Modifier
                .size(36.dp)
                .semantics { contentDescription = decreaseContentDescription },
        ) {
            Text(
                "−",
                fontSize = 20.sp,
                fontWeight = FontWeight.Bold,
                color = if (canDecrease) {
                    MaterialTheme.colorScheme.primary
                } else {
                    MaterialTheme.colorScheme.onSurface.copy(alpha = 0.38f)
                },
            )
        }

        Text(
            text = displayValue,
            style = MaterialTheme.typography.bodyMedium,
            fontWeight = FontWeight.SemiBold,
            textAlign = TextAlign.Center,
            modifier = Modifier.width(60.dp),
        )

        IconButton(
            onClick = onIncrease,
            enabled = canIncrease,
            modifier = Modifier
                .size(36.dp)
                .semantics { contentDescription = increaseContentDescription },
        ) {
            Text(
                "+",
                fontSize = 20.sp,
                fontWeight = FontWeight.Bold,
                color = if (canIncrease) {
                    MaterialTheme.colorScheme.primary
                } else {
                    MaterialTheme.colorScheme.onSurface.copy(alpha = 0.38f)
                },
            )
        }
    }
}

@Composable
private fun ChatDisplaySettingsSection(
    ui: SettingsUiState,
    vm: SettingsViewModel,
) {
    val display = ui.chatDisplaySettings
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(20.dp),
        colors = CardDefaults.cardColors(containerColor = Color.White.copy(alpha = 0.85f)),
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Text(
                "Hiển thị trò chuyện",
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.Bold,
                color = MaterialTheme.colorScheme.primary,
            )

            // Row: Cỡ chữ tin nhắn
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(vertical = 2.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Text(
                    text = "Cỡ chữ tin nhắn",
                    style = MaterialTheme.typography.bodyLarge,
                    fontWeight = FontWeight.Medium,
                    modifier = Modifier.weight(1f),
                )

                IconButton(
                    onClick = vm::decreaseMessageFontSize,
                    enabled = display.canDecrease(),
                    modifier = Modifier
                        .size(36.dp)
                        .semantics { contentDescription = "Giảm cỡ chữ tin nhắn" },
                ) {
                    Text(
                        "−",
                        fontSize = 20.sp,
                        fontWeight = FontWeight.Bold,
                        color = if (display.canDecrease()) {
                            MaterialTheme.colorScheme.primary
                        } else {
                            MaterialTheme.colorScheme.onSurface.copy(alpha = 0.38f)
                        },
                    )
                }

                Text(
                    text = "${display.fontSizeSp}sp",
                    style = MaterialTheme.typography.bodyMedium,
                    fontWeight = FontWeight.SemiBold,
                    textAlign = TextAlign.Center,
                    modifier = Modifier.width(60.dp),
                )

                IconButton(
                    onClick = vm::increaseMessageFontSize,
                    enabled = display.canIncrease(),
                    modifier = Modifier
                        .size(36.dp)
                        .semantics { contentDescription = "Tăng cỡ chữ tin nhắn" },
                ) {
                    Text(
                        "+",
                        fontSize = 20.sp,
                        fontWeight = FontWeight.Bold,
                        color = if (display.canIncrease()) {
                            MaterialTheme.colorScheme.primary
                        } else {
                            MaterialTheme.colorScheme.onSurface.copy(alpha = 0.38f)
                        },
                    )
                }
            }

            // Button: Khôi phục cỡ chữ
            OutlinedButton(
                onClick = vm::restoreMessageFontSize,
                shape = CircleShape,
                modifier = Modifier.semantics {
                    contentDescription = "Khôi phục cỡ chữ tin nhắn về mặc định"
                },
            ) {
                Text("Khôi phục cỡ chữ")
            }

            HorizontalDivider(
                color = Color.LightGray.copy(alpha = 0.3f),
                thickness = 0.5.dp,
            )

            // Lightweight preview
            Text(
                text = "Xem trước:",
                style = MaterialTheme.typography.labelMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )

            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(vertical = 4.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                // User bubble preview
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.End,
                ) {
                    Surface(
                        shape = RoundedCornerShape(16.dp, 16.dp, 4.dp, 16.dp),
                        color = MaterialTheme.colorScheme.primary,
                        contentColor = MaterialTheme.colorScheme.onPrimary,
                    ) {
                        Text(
                            text = "Xin chào!",
                            fontSize = display.fontSizeSp.sp,
                            lineHeight = display.lineHeightSp.sp,
                            modifier = Modifier.padding(horizontal = 12.dp, vertical = 6.dp),
                        )
                    }
                }

                // Assistant bubble preview
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.Start,
                ) {
                    Surface(
                        shape = RoundedCornerShape(16.dp, 16.dp, 16.dp, 4.dp),
                        color = Color.White,
                        contentColor = MaterialTheme.colorScheme.onSurface,
                        shadowElevation = 1.dp,
                    ) {
                        Text(
                            text = "Mình có thể giúp gì cho bạn?",
                            fontSize = display.fontSizeSp.sp,
                            lineHeight = display.lineHeightSp.sp,
                            modifier = Modifier.padding(horizontal = 12.dp, vertical = 6.dp),
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun AnimationSettingsHeader() {
    Text(
        "Chuyển động nhân vật",
        style = MaterialTheme.typography.titleLarge,
        fontWeight = FontWeight.Bold,
        color = MaterialTheme.colorScheme.primary,
        modifier = Modifier.padding(top = 8.dp),
    )
}

@Composable
private fun AnimationPreviewCard(ui: SettingsUiState) {
    val selectedActionName = ui.selectedPreviewAction
    val baseSpec = CharacterFrameCatalog.specForAction(selectedActionName)
    val effectiveSpec = ui.fpsSettings.applyOverride(baseSpec)
    val currentItem = AnimationActionItems.find { it.actionName == selectedActionName }
    val displayName = currentItem?.displayName ?: selectedActionName

    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(20.dp),
        colors = CardDefaults.cardColors(containerColor = Color.White.copy(alpha = 0.85f)),
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(14.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            Text(
                text = "Đang xem: $displayName (${effectiveSpec.fps} FPS)",
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.SemiBold,
                color = MaterialTheme.colorScheme.primary,
            )
            Spacer(Modifier.height(8.dp))
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .height(240.dp),
                contentAlignment = Alignment.BottomCenter,
            ) {
                CharacterAnimationPlayer(
                    spec = effectiveSpec,
                    modifier = Modifier.fillMaxSize(),
                    contentDescription = "Xem trước nhân vật: $displayName",
                    restartKey = ui.replayKey,
                    onOneShotFinished = {},
                )
            }
        }
    }
}

@Composable
private fun AnimationControlsCard(ui: SettingsUiState, vm: SettingsViewModel) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(20.dp),
        colors = CardDefaults.cardColors(containerColor = Color.White.copy(alpha = 0.85f)),
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(14.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            AnimationActionItems.forEachIndexed { index, item ->
                if (index > 0) {
                    HorizontalDivider(
                        color = Color.LightGray.copy(alpha = 0.3f),
                        thickness = 0.5.dp,
                    )
                }
                AnimationActionRow(
                    item = item,
                    currentFps = ui.fpsSettings.fpsFor(item.actionName),
                    isSelected = ui.selectedPreviewAction == item.actionName,
                    onDecrease = { vm.decreaseFps(item.actionName) },
                    onIncrease = { vm.increaseFps(item.actionName) },
                    onSelect = { vm.selectPreviewAction(item.actionName) },
                )
            }
        }
    }
}

@Composable
private fun AnimationActionRow(
    item: AnimationActionItem,
    currentFps: Int,
    isSelected: Boolean,
    onDecrease: () -> Unit,
    onIncrease: () -> Unit,
    onSelect: () -> Unit,
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 4.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Text(
            text = item.displayName,
            style = MaterialTheme.typography.bodyLarge,
            fontWeight = if (isSelected) FontWeight.Bold else FontWeight.Medium,
            color = if (isSelected) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.onSurface,
            modifier = Modifier.weight(1f),
        )

        IconButton(
            onClick = onDecrease,
            enabled = currentFps > AnimationFpsSettings.MIN_FPS,
            modifier = Modifier
                .size(36.dp)
                .semantics { contentDescription = "Giảm tốc độ cho ${item.displayName}" },
        ) {
            Text(
                "−",
                fontSize = 20.sp,
                fontWeight = FontWeight.Bold,
                color = if (currentFps > AnimationFpsSettings.MIN_FPS) {
                    MaterialTheme.colorScheme.primary
                } else {
                    MaterialTheme.colorScheme.onSurface.copy(alpha = 0.38f)
                },
            )
        }

        Text(
            text = "$currentFps FPS",
            style = MaterialTheme.typography.bodyMedium,
            fontWeight = FontWeight.SemiBold,
            textAlign = TextAlign.Center,
            modifier = Modifier.width(60.dp),
        )

        IconButton(
            onClick = onIncrease,
            enabled = currentFps < AnimationFpsSettings.MAX_FPS,
            modifier = Modifier
                .size(36.dp)
                .semantics { contentDescription = "Tăng tốc độ cho ${item.displayName}" },
        ) {
            Text(
                "+",
                fontSize = 20.sp,
                fontWeight = FontWeight.Bold,
                color = if (currentFps < AnimationFpsSettings.MAX_FPS) {
                    MaterialTheme.colorScheme.primary
                } else {
                    MaterialTheme.colorScheme.onSurface.copy(alpha = 0.38f)
                },
            )
        }

        Spacer(Modifier.width(8.dp))

        if (isSelected) {
            Button(
                onClick = onSelect,
                shape = RoundedCornerShape(18.dp),
                contentPadding = PaddingValues(horizontal = 12.dp, vertical = 2.dp),
                modifier = Modifier
                    .height(34.dp)
                    .semantics { contentDescription = "Đang xem trước ${item.displayName}" },
            ) {
                Text("Đang xem", fontSize = 12.sp)
            }
        } else {
            OutlinedButton(
                onClick = onSelect,
                shape = RoundedCornerShape(18.dp),
                contentPadding = PaddingValues(horizontal = 12.dp, vertical = 2.dp),
                modifier = Modifier
                    .height(34.dp)
                    .semantics { contentDescription = "Xem trước chuyển động ${item.displayName}" },
            ) {
                Text("Xem", fontSize = 12.sp)
            }
        }
    }
}

@Composable
private fun AnimationActionButtons(vm: SettingsViewModel) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(bottom = 16.dp),
        horizontalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        OutlinedButton(
            onClick = vm::replayPreview,
            shape = CircleShape,
            modifier = Modifier
                .weight(1f)
                .semantics { contentDescription = "Phát lại chuyển động đang chọn" },
        ) {
            Text("Phát lại")
        }
        OutlinedButton(
            onClick = vm::restoreDefaultFps,
            shape = CircleShape,
            modifier = Modifier
                .weight(1f)
                .semantics { contentDescription = "Khôi phục tốc độ chuyển động về mặc định" },
        ) {
            Text("Khôi phục mặc định")
        }
    }
}
