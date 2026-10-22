package com.example.assistant.ui.companion

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import androidx.lifecycle.viewmodel.initializer
import androidx.lifecycle.viewmodel.viewModelFactory
import com.example.assistant.assistantApp
import com.example.assistant.data.repo.CompanionGateway
import com.example.assistant.domain.CompanionPreferences
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import kotlinx.coroutines.CancellationException

data class CompanionSettingsState(
    val loading: Boolean = false, val saving: Boolean = false, val loaded: Boolean = false,
    val saved: CompanionPreferences = CompanionPreferences(), val draft: CompanionPreferences = CompanionPreferences(),
    val error: String? = null, val success: Boolean = false,
) { val dirty: Boolean get() = saved != draft }

class CompanionViewModel(private val gateway: CompanionGateway) : ViewModel() {
    private val _ui = MutableStateFlow(CompanionSettingsState())
    val ui = _ui.asStateFlow()
    private var owner: String? = null
    init { refresh() }

    private suspend fun safeOwner(): String? = try { gateway.ownerId() }
        catch (cancelled: CancellationException) { throw cancelled }
        catch (_: Exception) { null }

    fun edit(preferences: CompanionPreferences) {
        if (_ui.value.loaded && !_ui.value.loading && !_ui.value.saving) _ui.update { it.copy(draft = preferences, success = false, error = null) }
    }

    fun refresh() {
        if (_ui.value.loading || _ui.value.saving) return
        _ui.update { it.copy(loading = true, error = null, success = false) }
        viewModelScope.launch {
            val id = safeOwner()
            if (id == null) { _ui.update { it.copy(loading = false, error = "Chưa tải được cá nhân hóa. Bạn thử lại nhé.") }; return@launch }
            if (owner != null && owner != id) _ui.value = CompanionSettingsState(loading = true)
            owner = id
            val result = gateway.getCompanion(id)
            if (safeOwner() != id) { owner = null; _ui.value = CompanionSettingsState(error = "Phiên người dùng đã thay đổi. Bạn tải lại nhé."); return@launch }
            result.fold(
                onSuccess = { prefs -> _ui.update { it.copy(loading = false, loaded = true, saved = prefs, draft = if (it.dirty) it.draft else prefs) } },
                onFailure = { _ui.update { it.copy(loading = false, error = "Chưa tải được cá nhân hóa. Bạn thử lại nhé.") } },
            )
        }
    }

    fun save() {
        val state = _ui.value
        val id = owner ?: return
        if (!state.loaded || state.loading || state.saving || !state.draft.valid()) return
        _ui.update { it.copy(saving = true, success = false, error = null) }
        viewModelScope.launch {
            if (safeOwner() != id) {
                owner = null
                _ui.value = CompanionSettingsState(error = "Phiên người dùng đã thay đổi. Bạn tải lại cài đặt nhé.")
                return@launch
            }
            val result = gateway.saveCompanion(id, state.draft.copy(preferredName = state.draft.preferredName?.trim()?.ifEmpty { null }))
            if (safeOwner() != id) { owner = null; _ui.value = CompanionSettingsState(error = "Phiên người dùng đã thay đổi. Bạn tải lại nhé."); return@launch }
            result.fold(
                onSuccess = { prefs -> _ui.update { it.copy(saving = false, saved = prefs, draft = prefs, success = true) } },
                onFailure = { _ui.update { it.copy(saving = false, error = "Chưa lưu được thay đổi. Bản chỉnh sửa vẫn được giữ lại.") } },
            )
        }
    }

    companion object {
        val Factory = viewModelFactory { initializer { CompanionViewModel(assistantApp().container.repository) } }
    }
}
