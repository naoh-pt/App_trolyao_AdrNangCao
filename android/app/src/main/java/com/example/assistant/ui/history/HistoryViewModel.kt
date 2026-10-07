package com.example.assistant.ui.history

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import androidx.lifecycle.viewmodel.initializer
import androidx.lifecycle.viewmodel.viewModelFactory
import com.example.assistant.assistantApp
import com.example.assistant.data.local.ConversationEntity
import com.example.assistant.data.repo.ChatRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class HistoryUiState(
    val loading: Boolean = false,
    val online: Boolean = true,
    val error: String? = null,
)

class HistoryViewModel(private val repo: ChatRepository) : ViewModel() {
    val conversations: StateFlow<List<ConversationEntity>> = repo.observeConversations()
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    private val _ui = MutableStateFlow(HistoryUiState())
    val ui: StateFlow<HistoryUiState> = _ui.asStateFlow()

    init {
        refresh()
    }

    fun refresh() {
        viewModelScope.launch {
            _ui.update { it.copy(loading = true) }
            try {
                repo.refreshConversations()
                    .onSuccess { _ui.update { s -> s.copy(online = true, error = null) } }
                    .onFailure { e -> _ui.update { s -> s.copy(online = false, error = e.message) } }
            } finally {
                _ui.update { it.copy(loading = false) }
            }
        }
    }

    fun delete(id: String) {
        if (!_ui.value.online) return
        viewModelScope.launch {
            repo.deleteConversation(id)
                .onFailure { e -> _ui.update { s -> s.copy(error = e.message) } }
        }
    }

    companion object {
        val Factory = viewModelFactory {
            initializer { HistoryViewModel(assistantApp().container.repository) }
        }
    }
}
