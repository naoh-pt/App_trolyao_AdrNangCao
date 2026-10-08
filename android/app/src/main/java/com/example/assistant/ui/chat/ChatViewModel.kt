package com.example.assistant.ui.chat

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import androidx.lifecycle.viewmodel.initializer
import androidx.lifecycle.viewmodel.viewModelFactory
import com.example.assistant.assistantApp
import com.example.assistant.data.local.MessageEntity
import com.example.assistant.data.repo.ChatRepository
import com.example.assistant.domain.CharacterState
import com.example.assistant.domain.Emotion
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asSharedFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.flatMapLatest
import kotlinx.coroutines.flow.flowOf
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import java.util.UUID

private const val MAX_LEN = 2000
private const val TALKING_MS = 2000L

data class ChatUiState(
    val characterState: CharacterState = CharacterState.IDLE,
    val emotion: Emotion = Emotion.NEUTRAL,
    val input: String = "",
    /** Tin đang gửi / gửi lỗi (bản nháp giữ nguyên + cùng request_id để thử lại). */
    val pending: String? = null,
    val sending: Boolean = false,
    val error: String? = null,
    /** false khi lần đồng bộ gần nhất với server thất bại -> chỉ xem cache, không gửi/tạo. */
    val online: Boolean = true,
)

/**
 * Pure transition logic determining whether an animation completion callback should transition
 * state from TALKING to IDLE.
 *
 * Only active emotional one-shot states (TALKING with HAPPY, SAD, or SURPRISED) are handled.
 * Returns false if the state is not TALKING or if the emotion is NEUTRAL.
 */
fun canHandleAnimationFinished(state: CharacterState, emotion: Emotion): Boolean =
    state == CharacterState.TALKING && emotion != Emotion.NEUTRAL

/**
 * Pure state reducer transitioning from an emotional one-shot TALKING state back to IDLE + NEUTRAL.
 * If the current state does not qualify, returns the state unchanged.
 */
fun ChatUiState.reduceAnimationFinished(): ChatUiState =
    if (canHandleAnimationFinished(characterState, emotion)) {
        copy(characterState = CharacterState.IDLE, emotion = Emotion.NEUTRAL)
    } else {
        this
    }

class ChatViewModel(
    private val repo: ChatRepository,
    initialConversationId: String?,
) : ViewModel() {

    private val conversationId = MutableStateFlow(initialConversationId)
    private val _ui = MutableStateFlow(ChatUiState())
    val ui: StateFlow<ChatUiState> = _ui.asStateFlow()

    @OptIn(ExperimentalCoroutinesApi::class)
    val messages: StateFlow<List<MessageEntity>> = conversationId
        .flatMapLatest { id -> if (id == null) flowOf(emptyList()) else repo.observeMessages(id) }
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    private val _speechEvents = MutableSharedFlow<String>(replay = 0, extraBufferCapacity = 1)
    /** One-time speech events emitted strictly when a new assistant response is received. */
    val speechEvents: SharedFlow<String> = _speechEvents.asSharedFlow()

    private var requestId: String? = null
    private var talkJob: Job? = null

    init {
        refresh()
    }

    /** Tải lại từ server; nếu chưa có chat thì tạo mới. */
    fun refresh() {
        viewModelScope.launch {
            val id = conversationId.value
            if (id == null) createChat() else loadMessages(id)
        }
    }

    private suspend fun loadMessages(id: String) {
        repo.refreshMessages(id)
            .onSuccess { _ui.update { s -> s.copy(online = true, error = null) } }
            .onFailure { e ->
                val isNetworkErr = e is com.example.assistant.data.remote.ApiException && (e.httpCode == null || e.code == "NETWORK" || e.code == "BAD_URL")
                _ui.update { s -> s.copy(online = !isNetworkErr, error = if (!isNetworkErr) e.message else null) }
            }
    }

    private suspend fun createChat() {
        repo.createConversation()
            .onSuccess { c ->
                conversationId.value = c.id
                _ui.update { s -> s.copy(online = true, error = null) }
            }
            .onFailure { e ->
                val isNetworkErr = e is com.example.assistant.data.remote.ApiException && (e.httpCode == null || e.code == "NETWORK" || e.code == "BAD_URL")
                _ui.update { s -> s.copy(online = !isNetworkErr, error = e.message) }
            }
    }

    fun onInputChange(text: String) {
        _ui.update { s -> s.copy(input = text.take(MAX_LEN)) }
    }

    fun send() {
        val s = _ui.value
        if (s.sending || !s.online) return
        val text = s.pending ?: s.input.trim()
        if (text.isEmpty()) return
        // Gửi mới -> request_id mới; thử lại -> giữ nguyên request_id cũ.
        val rid = if (s.pending == null) UUID.randomUUID().toString().also { requestId = it } else requestId ?: UUID.randomUUID().toString().also { requestId = it }

        talkJob?.cancel()
        talkJob = null
        _ui.update {
            it.copy(
                pending = text,
                input = if (s.pending == null) "" else it.input,
                error = null,
                sending = true,
                characterState = CharacterState.THINKING,
                emotion = Emotion.NEUTRAL,
            )
        }

        viewModelScope.launch {
            var id = conversationId.value
            if (id == null) {
                val created = repo.createConversation()
                if (created.isFailure) {
                    fail(created.exceptionOrNull())
                    return@launch
                }
                id = created.getOrThrow().id
                conversationId.value = id
            }
            repo.sendMessage(id, rid, text).fold(
                onSuccess = { reply ->
                    requestId = null
                    val emotion = Emotion.from(reply.emotion)
                    talkJob?.cancel()
                    talkJob = null
                    _ui.update {
                        it.copy(
                            pending = null,
                            sending = false,
                            error = null,
                            characterState = CharacterState.TALKING,
                            emotion = emotion,
                        )
                    }
                    if (reply.text.isNotBlank()) {
                        _speechEvents.emit(reply.text)
                    }
                    if (emotion == Emotion.NEUTRAL) {
                        talkJob = viewModelScope.launch {
                            delay(TALKING_MS)
                            _ui.update { current ->
                                if (current.characterState == CharacterState.TALKING && current.emotion == Emotion.NEUTRAL) {
                                    current.copy(
                                        characterState = CharacterState.IDLE,
                                        emotion = Emotion.NEUTRAL,
                                    )
                                } else {
                                    current
                                }
                            }
                        }
                    }
                },
                onFailure = { fail(it) },
            )
        }
    }

    /**
     * Callback invoked when a one-shot emotional animation finishes playback.
     * Transitions character back to IDLE + NEUTRAL only if currently in an emotional TALKING state.
     */
    fun onCharacterAnimationFinished() {
        val s = _ui.value
        if (!canHandleAnimationFinished(s.characterState, s.emotion)) {
            return
        }
        talkJob?.cancel()
        talkJob = null
        _ui.update { it.reduceAnimationFinished() }
    }

    private fun fail(e: Throwable?) {
        talkJob?.cancel()
        talkJob = null
        _ui.update {
            it.copy(
                sending = false,
                characterState = CharacterState.IDLE,
                emotion = Emotion.NEUTRAL,
                error = e?.message ?: "Đã có lỗi xảy ra",
            )
        }
    }

    /** Bỏ gửi lại: đưa bản nháp về ô nhập để sửa. */
    fun editPending() {
        requestId = null
        _ui.update { s -> s.copy(input = s.pending ?: s.input, pending = null, error = null) }
    }

    fun newChat() {
        if (_ui.value.sending) return
        talkJob?.cancel()
        talkJob = null
        requestId = null
        conversationId.value = null
        _ui.value = ChatUiState()
        refresh()
    }

    companion object {
        fun factory(conversationId: String?) = viewModelFactory {
            initializer { ChatViewModel(assistantApp().container.repository, conversationId) }
        }
    }
}
