package com.example.assistant.ui.memory

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import androidx.lifecycle.viewmodel.initializer
import androidx.lifecycle.viewmodel.viewModelFactory
import com.example.assistant.assistantApp
import com.example.assistant.data.remote.MemoryDto
import com.example.assistant.data.repo.MemoryGateway
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class MemoryUiState(
    val loading: Boolean = false,
    val items: List<MemoryDto> = emptyList(),
    val error: String? = null,
    val confirmClear: Boolean = false,
)

class MemoryViewModel(private val gateway: MemoryGateway) : ViewModel() {
    private val _ui = MutableStateFlow(MemoryUiState())
    val ui = _ui.asStateFlow()

    init { refresh() }

    fun refresh() {
        if (_ui.value.loading) return
        _ui.update { it.copy(loading = true, error = null) }
        viewModelScope.launch { load() }
    }

    private suspend fun load() {
        gateway.listMemories().fold(
            onSuccess = { items -> _ui.update { it.copy(loading = false, items = items, error = null) } },
            onFailure = { _ui.update { it.copy(loading = false, error = "Chưa tải được trí nhớ. Bạn thử lại nhé.") } },
        )
    }

    fun requestClear() {
        if (!_ui.value.loading && _ui.value.items.isNotEmpty()) _ui.update { it.copy(confirmClear = true) }
    }
    fun cancelClear() { _ui.update { it.copy(confirmClear = false) } }

    fun confirmClear() {
        if (!_ui.value.confirmClear || _ui.value.loading) return
        remove(_ui.value.items.map { it.id })
    }

    fun delete(id: String) {
        if (_ui.value.items.any { it.id == id } && !_ui.value.loading) remove(listOf(id))
    }

    private fun remove(ids: List<String>) {
        _ui.update { it.copy(loading = true, confirmClear = false, error = null) }
        viewModelScope.launch {
            var failed = false
            for (id in ids) {
                if (gateway.deleteMemory(id).isFailure) { failed = true; break }
            }
            load()
            if (failed) _ui.update { it.copy(error = "Chưa xóa được thông tin. Bạn tải lại và thử nhé.") }
        }
    }

    companion object {
        val Factory = viewModelFactory {
            initializer { MemoryViewModel(assistantApp().container.repository) }
        }
    }
}
