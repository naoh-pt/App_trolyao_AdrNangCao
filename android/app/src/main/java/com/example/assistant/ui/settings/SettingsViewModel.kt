package com.example.assistant.ui.settings

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import androidx.lifecycle.viewmodel.initializer
import androidx.lifecycle.viewmodel.viewModelFactory
import com.example.assistant.assistantApp
import com.example.assistant.data.local.SettingsStore
import com.example.assistant.data.repo.ChatRepository
import com.example.assistant.domain.AnimationFpsSettings
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class SettingsUiState(
    val url: String = "",
    val status: String? = null,
    val statusOk: Boolean = false,
    val busy: Boolean = false,
    val fpsSettings: AnimationFpsSettings = AnimationFpsSettings.DEFAULT,
    val selectedPreviewAction: String = AnimationFpsSettings.ACTION_IDLE,
    val replayKey: Long = 0L,
)

class SettingsViewModel(
    private val settings: SettingsStore,
    private val repo: ChatRepository,
) : ViewModel() {
    private val _ui = MutableStateFlow(SettingsUiState())
    val ui: StateFlow<SettingsUiState> = _ui.asStateFlow()

    init {
        viewModelScope.launch {
            val saved = settings.baseUrl.first()
            _ui.update { s -> if (s.url.isEmpty()) s.copy(url = saved) else s }
        }
        viewModelScope.launch {
            settings.animationFpsSettings.collect { fps ->
                _ui.update { s -> s.copy(fpsSettings = fps) }
            }
        }
    }

    fun selectPreviewAction(actionName: String) {
        if (AnimationFpsSettings.ALL_ACTIONS.contains(actionName)) {
            _ui.update { it.copy(selectedPreviewAction = actionName, replayKey = it.replayKey + 1) }
        }
    }

    fun replayPreview() {
        _ui.update { it.copy(replayKey = it.replayKey + 1) }
    }

    fun decreaseFps(actionName: String) {
        val current = _ui.value.fpsSettings.fpsFor(actionName)
        if (current <= AnimationFpsSettings.MIN_FPS) return
        viewModelScope.launch {
            settings.adjustFps(actionName, -1)
        }
    }

    fun increaseFps(actionName: String) {
        val current = _ui.value.fpsSettings.fpsFor(actionName)
        if (current >= AnimationFpsSettings.MAX_FPS) return
        viewModelScope.launch {
            settings.adjustFps(actionName, 1)
        }
    }

    fun restoreDefaultFps() {
        viewModelScope.launch {
            settings.resetFpsToDefaults()
        }
    }

    fun onUrlChange(text: String) {
        _ui.update { it.copy(url = text, status = null) }
    }

    fun test() {
        val url = SettingsStore.normalize(_ui.value.url)
        if (url == null) {
            _ui.update { it.copy(status = "Địa chỉ backend không hợp lệ. Vui lòng kiểm tra lại (ví dụ: http://192.168.1.10:8000).", statusOk = false) }
            return
        }
        viewModelScope.launch {
            _ui.update { it.copy(busy = true, status = null) }
            try {
                repo.checkHealth(url)
                    .onSuccess { _ui.update { s -> s.copy(status = "Kết nối thành công! Server hoạt động bình thường.", statusOk = true) } }
                    .onFailure { e -> _ui.update { s -> s.copy(status = e.message ?: "Không thể kết nối", statusOk = false) } }
            } finally {
                _ui.update { it.copy(busy = false) }
            }
        }
    }

    fun save() {
        val url = SettingsStore.normalize(_ui.value.url)
        if (url == null) {
            _ui.update { it.copy(status = "Địa chỉ backend không hợp lệ. Vui lòng kiểm tra lại (ví dụ: http://192.168.1.10:8000).", statusOk = false) }
            return
        }
        viewModelScope.launch {
            settings.setBaseUrl(url)
            _ui.update { it.copy(url = url, status = "Đã lưu địa chỉ backend thành công", statusOk = true) }
        }
    }

    companion object {
        val Factory = viewModelFactory {
            initializer {
                val c = assistantApp().container
                SettingsViewModel(c.settings, c.repository)
            }
        }
    }
}
