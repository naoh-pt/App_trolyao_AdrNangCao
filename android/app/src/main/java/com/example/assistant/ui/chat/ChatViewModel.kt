package com.example.assistant.ui.chat

import android.app.Activity
import android.content.Intent
import android.speech.RecognizerIntent
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import androidx.lifecycle.viewmodel.initializer
import androidx.lifecycle.viewmodel.viewModelFactory
import com.example.assistant.assistantApp
import com.example.assistant.data.local.MessageEntity
import com.example.assistant.data.local.SettingsStore
import com.example.assistant.data.remote.AssistantActionDto
import com.example.assistant.data.repo.ChatRepository
import com.example.assistant.domain.AnimationFpsSettings
import com.example.assistant.domain.CharacterState
import com.example.assistant.domain.Emotion
import com.example.assistant.ui.demo.DemoCommand
import com.example.assistant.ui.demo.DemoState
import com.example.assistant.ui.demo.reduceDemo
import com.example.assistant.ui.memory.ConversationEntryCheckIn
import com.example.assistant.ui.companion.*
import com.example.assistant.ui.character.animationSpecFor
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

/** Default safety margin added to full animation sequence duration (in milliseconds). */
const val DEFAULT_EMOTION_WATCHDOG_SAFETY_MARGIN_MS = 400L

/**
 * Pure calculation of watchdog recovery timeout for a character emotion.
 * Derives timeout from total animation duration (frames * frameDurationMs) plus safety margin (300-500ms).
 * Returns 0L for NEUTRAL as neutral transitions directly to IDLE without animation watchdog.
 */
fun calculateEmotionWatchdogDurationMs(
    emotion: Emotion,
    fpsSettings: AnimationFpsSettings = AnimationFpsSettings.DEFAULT,
    safetyMarginMs: Long = DEFAULT_EMOTION_WATCHDOG_SAFETY_MARGIN_MS,
): Long {
    if (emotion == Emotion.NEUTRAL) return 0L
    val baseSpec = animationSpecFor(CharacterState.TALKING, emotion)
    val effectiveSpec = fpsSettings.applyOverride(baseSpec)
    return effectiveSpec.totalDurationMs + safetyMarginMs
}

data class SpeechEvent(
    val utteranceId: String,
    val text: String,
)

data class ChatUiState(
    val characterState: CharacterState = CharacterState.IDLE,
    val emotion: Emotion = Emotion.NEUTRAL,
    val input: String = "",
    val demo: DemoState = DemoState(),
    val companion: CompanionChatState = CompanionChatState(),
    val reveal: ReplyReveal? = null,
    val playbackToken: String? = null,
    val speechActive: Boolean = false,
    /** Only this incoming row is hidden until the send result starts its presentation. */
    val incomingAssistantId: String? = null,
    /** Tin đang gửi / gửi lỗi (bản nháp giữ nguyên + cùng request_id để thử lại). */
    val pending: String? = null,
    val sending: Boolean = false,
    val error: String? = null,
    /** false khi lần đồng bộ gần nhất với server thất bại -> chỉ xem cache, không gửi/tạo. */
    val online: Boolean = true,
    /** Map of assistant message ID to proposed assistant action. */
    val activeActions: Map<String, AssistantActionDto> = emptyMap(),
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

/**
 * Pure parsing of speech recognition results.
 * Returns the first trimmed, non-blank match if [resultCode] is [Activity.RESULT_OK], otherwise null.
 */
fun extractSpeechRecognitionText(resultCode: Int, results: List<String>?): String? {
    if (resultCode != Activity.RESULT_OK) return null
    val best = results?.firstOrNull()?.trim()
    return if (!best.isNullOrBlank()) best else null
}

/**
 * Pure state reducer determining updated text input from speech recognition.
 * If [recognizedText] is non-blank, returns it trimmed; otherwise preserves [currentText].
 */
fun reduceVoiceInput(currentText: String, recognizedText: String?): String =
    if (!recognizedText.isNullOrBlank()) {
        recognizedText.trim()
    } else {
        currentText
    }

/**
 * Extracts recognized speech text from Android speech recognizer activity result.
 */
fun extractSpeechRecognitionResult(resultCode: Int, data: Intent?): String? {
    if (resultCode != Activity.RESULT_OK || data == null) return null
    val results = data.getStringArrayListExtra(RecognizerIntent.EXTRA_RESULTS)
    return extractSpeechRecognitionText(resultCode, results)
}

/** One coordinator joins text and speech completion before the existing emotion player. */
enum class ReplyPhase { Idle, Thinking, RevealingOrSpeaking, FinalEmotion }

class SpeechAnimationCoordinator(
    initialState: CharacterState = CharacterState.IDLE,
    initialEmotion: Emotion = Emotion.NEUTRAL,
) {
    var characterState = initialState
        private set
    var emotion = initialEmotion
        private set
    var phase = ReplyPhase.Idle
        private set
    var token: String? = null
        private set
    var activeUtteranceId: String? = null
        private set
    var pendingResponseEmotion = Emotion.NEUTRAL
        private set
    private var revealing = false

    fun onUserSendMessage() {
        onReset()
        phase = ReplyPhase.Thinking
        characterState = CharacterState.THINKING
    }

    fun onReplyReceived(
        utteranceId: String,
        responseEmotion: Emotion,
        ttsEnabled: Boolean,
        revealActive: Boolean = false,
    ) {
        token = utteranceId
        pendingResponseEmotion = responseEmotion
        activeUtteranceId = utteranceId.takeIf { ttsEnabled }
        revealing = revealActive
        phase = ReplyPhase.RevealingOrSpeaking
        settle()
    }

    private fun settle() {
        if (revealing || activeUtteranceId != null) {
            phase = ReplyPhase.RevealingOrSpeaking
            characterState = CharacterState.TALKING
            emotion = Emotion.NEUTRAL
        } else if (pendingResponseEmotion != Emotion.NEUTRAL) {
            phase = ReplyPhase.FinalEmotion
            characterState = CharacterState.TALKING
            emotion = pendingResponseEmotion
        } else {
            phase = ReplyPhase.Idle
            characterState = CharacterState.IDLE
            emotion = Emotion.NEUTRAL
        }
    }

    fun onRevealCompleted(replyToken: String): Boolean {
        if (replyToken != token || !revealing) return false
        revealing = false
        settle()
        return true
    }

    fun onSpeechStarted(utteranceId: String): Boolean = utteranceId == activeUtteranceId

    fun onSpeechCompleted(utteranceId: String): Boolean {
        if (utteranceId != activeUtteranceId) return false
        activeUtteranceId = null
        settle()
        return true
    }

    fun onSpeechError(utteranceId: String): Boolean = onSpeechCompleted(utteranceId)
    fun onSpeechStopped(utteranceId: String): Boolean = onSpeechCompleted(utteranceId)

    fun onEmotionDisplayFinished(replyToken: String? = token) {
        if (replyToken != token || phase != ReplyPhase.FinalEmotion) return
        phase = ReplyPhase.Idle
        characterState = CharacterState.IDLE
        emotion = Emotion.NEUTRAL
    }

    fun onReset() {
        token = null
        activeUtteranceId = null
        revealing = false
        pendingResponseEmotion = Emotion.NEUTRAL
        phase = ReplyPhase.Idle
        characterState = CharacterState.IDLE
        emotion = Emotion.NEUTRAL
    }
}

class ChatViewModel(
    private val repo: ChatRepository,
    initialConversationId: String?,
) : ViewModel() {

    val coordinator = SpeechAnimationCoordinator()
    var isTtsEnabled: Boolean = SettingsStore.DEFAULT_TTS_ENABLED
        private set

    var fpsSettings: AnimationFpsSettings = AnimationFpsSettings.DEFAULT
        private set

    fun setFpsSettings(settings: AnimationFpsSettings) {
        fpsSettings = settings
    }

    private var lastActionClickTimeMs = 0L

    /** Guard against rapid duplicate taps on assistant action buttons. */
    fun canClickAction(): Boolean {
        val now = System.currentTimeMillis()
        return if (now - lastActionClickTimeMs > 1000L) {
            lastActionClickTimeMs = now
            true
        } else {
            false
        }
    }

    private val conversationId = MutableStateFlow(initialConversationId)
    private val _ui = MutableStateFlow(ChatUiState())
    val ui: StateFlow<ChatUiState> = _ui.asStateFlow()

    @OptIn(ExperimentalCoroutinesApi::class)
    val messages: StateFlow<List<MessageEntity>> = conversationId
        .flatMapLatest { id -> if (id == null) flowOf(emptyList()) else repo.observeMessages(id) }
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    private val _speechEvents = MutableSharedFlow<SpeechEvent>(replay = 0, extraBufferCapacity = 1)
    /** One-time speech commands for new replies and explicit replay; never for history loading. */
    val speechEvents: SharedFlow<SpeechEvent> = _speechEvents.asSharedFlow()

    private val _stopSpeechEvents = MutableSharedFlow<Unit>(replay = 0, extraBufferCapacity = 1)
    /** Signal to immediately stop any active speech playback in UI layer. */
    val stopSpeechEvents: SharedFlow<Unit> = _stopSpeechEvents.asSharedFlow()

    private var requestId: String? = null
    private var talkJob: Job? = null
    private var screenActive = false
    private var typewriterEnabled = true
    private val entryCheckIn = ConversationEntryCheckIn(viewModelScope, repo::checkIn, repo::cacheCheckIn, ::prepareMoodCheckIn)
    private val revealController = ReplyRevealController()

    fun setTypewriterEnabled(enabled: Boolean) {
        typewriterEnabled = enabled
        if (!enabled) skipReveal(_ui.value.reveal?.messageId ?: return)
    }

    fun onScreenStarted() {
        screenActive = true
        if (_ui.value.sending) coordinator.onUserSendMessage()
        syncPlayback()
    }

    private fun syncPlayback() {
        _ui.update { it.copy(characterState = coordinator.characterState,
            emotion = coordinator.emotion, playbackToken = coordinator.token,
            speechActive = coordinator.activeUtteranceId != null) }
    }

    fun advanceReveal(token: String) {
        if (!screenActive) return
        val next = revealController.advance(token) ?: return
        _ui.update { it.copy(reveal = next) }
        if (next.complete && coordinator.onRevealCompleted(token)) {
            syncPlayback()
            scheduleEmotionWatchdog()
        }
    }

    fun skipReveal(messageId: String) {
        val reveal = revealController.skip(messageId) ?: return
        _ui.update { it.copy(reveal = reveal) }
        if (coordinator.onRevealCompleted(reveal.token)) {
            syncPlayback()
            scheduleEmotionWatchdog()
        }
    }

    fun stopReading() {
        val id = coordinator.activeUtteranceId ?: return
        _stopSpeechEvents.tryEmit(Unit)
        onSpeechStopped(id)
    }

    fun replay(message: MessageEntity) {
        if (!screenActive || _ui.value.sending || message.role != "assistant" || message.text.isBlank()) return
        skipReveal(message.id)
        talkJob?.cancel()
        _stopSpeechEvents.tryEmit(Unit)
        val token = UUID.randomUUID().toString()
        coordinator.onReplyReceived(token, Emotion.from(message.emotion), ttsEnabled = true)
        syncPlayback()
        _speechEvents.tryEmit(SpeechEvent(token, message.text))
    }

    init {
        if (initialConversationId == null) refresh()
        // One real existing-conversation entry per ViewModel, retained across rotation.
        initialConversationId?.let { id ->
            viewModelScope.launch {
                // History loads first, preventing refresh from removing a new cached check-in.
                loadMessages(id)
                if (conversationId.value == id) entryCheckIn.enter(id)
            }
        }
    }

    fun setTtsEnabled(enabled: Boolean) {
        isTtsEnabled = enabled
        if (!enabled) stopReading()
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

    private suspend fun prepareMoodCheckIn(memoryDelivered: Boolean?) {
        if (memoryDelivered != false) return
        val id = conversationId.value ?: return
        val owner = repo.ownerId()
        val preferences = repo.getCompanion(owner).getOrNull() ?: return
        if (!moodEligible(true, preferences.moodCheckInEnabled, memoryDelivered, false)) return
        if (conversationId.value != id || _ui.value.sending || _ui.value.pending != null || _ui.value.companion.entryEngaged) return
        val claimed = repo.claimMoodDate(owner, moodDate())
        if (claimed && conversationId.value == id && !_ui.value.sending && _ui.value.pending == null && !_ui.value.companion.entryEngaged) {
            _ui.update { it.copy(companion = it.companion.copy(moodVisible = true, moodOwner = owner)) }
        }
    }

    fun dismissMood() { _ui.update { it.copy(companion = it.companion.copy(moodVisible = false)) } }
    fun chooseMood(choice: MoodChoice) = sendCompanion(choice, null)
    fun chooseSupport(choice: SupportChoice) = sendCompanion(null, choice)

    private fun sendCompanion(mood: MoodChoice?, support: SupportChoice?) {
        val current = _ui.value
        val selection = current.selectCompanion(mood, support)
        selection ?: return
        _ui.update { it.copy(companion = selection.first) }
        val id = conversationId.value
        viewModelScope.launch {
            val ownerMatches = mood == null || repo.ownerId() == current.companion.moodOwner
            if (conversationId.value != id || !ownerMatches) {
                _ui.update { it.copy(companion = it.companion.copy(selectionBusy = false)) }
                return@launch
            }
            val latest = _ui.value
            if (!latest.sending && latest.pending == null && latest.online) {
                val draft = latest.input
                onInputChange(selection.second)
                send()
                _ui.update { it.copy(input = draft, companion = it.companion.copy(selectionBusy = false)) }
            } else _ui.update { it.copy(companion = it.companion.copy(selectionBusy = false)) }
        }
    }

    fun onDemoCommand(command: DemoCommand) {
        _ui.update { it.reduceDemo(command) }
    }

    /**
     * Updates input text with recognized voice input result without sending automatically.
     * Preserves existing input if [recognizedText] is null or blank.
     */
    fun onVoiceInputResult(recognizedText: String?) {
        val updated = reduceVoiceInput(_ui.value.input, recognizedText)
        onInputChange(updated)
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
        revealController.startRequest(messages.value.map { it.id })
        _stopSpeechEvents.tryEmit(Unit)
        coordinator.onUserSendMessage()
        _ui.update {
            it.copy(
                pending = text,
                input = if (s.pending == null) "" else it.input,
                error = null,
                sending = true,
                companion = it.companion.userTurn(),
                reveal = null,
                playbackToken = null,
                speechActive = false,
                incomingAssistantId = null,
                characterState = coordinator.characterState,
                emotion = coordinator.emotion,
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
            repo.sendMessage(id, rid, text, beforeAssistantCached = { message ->
                if (messages.value.none { it.id == message.id }) {
                    _ui.update { it.copy(incomingAssistantId = message.id) }
                }
            }).fold(
                onSuccess = { reply ->
                    requestId = null
                    val botMsg = reply.message
                    val botAction = reply.action
                    val emotion = Emotion.from(botMsg.emotion)
                    val utteranceId = UUID.randomUUID().toString()
                    talkJob?.cancel()
                    talkJob = null

                    val isNew = revealController.receive(botMsg.id, utteranceId, botMsg.text,
                        typewriterEnabled, screenActive)
                    val reveal = revealController.current
                    val willSpeak = screenActive && isNew && isTtsEnabled && botMsg.text.isNotBlank()
                    if (screenActive && isNew) {
                        coordinator.onReplyReceived(utteranceId, emotion, willSpeak, reveal != null)
                    } else coordinator.onReset()
                    _ui.update {
                        val updatedActions = if (botAction != null) {
                            it.activeActions + (botMsg.id to botAction)
                        } else {
                            it.activeActions
                        }
                        it.copy(
                            pending = null,
                            sending = false,
                            reveal = reveal,
                            playbackToken = coordinator.token,
                            speechActive = willSpeak,
                            incomingAssistantId = null,
                            error = null,
                            characterState = coordinator.characterState,
                            emotion = coordinator.emotion,
                            activeActions = updatedActions,
                            companion = it.companion.copy(supportMessageId = if (isNew && botAction == null && emotionalSupportCue(text)) botMsg.id else null),
                        )
                    }

                    if (willSpeak) {
                        _speechEvents.emit(SpeechEvent(utteranceId, botMsg.text))
                    } else {
                        scheduleEmotionWatchdog()
                    }
                },
                onFailure = { fail(it) },
            )
        }
    }

    private fun scheduleEmotionWatchdog() {
        talkJob?.cancel()
        talkJob = null
        val currentEmotion = coordinator.emotion
        if (coordinator.characterState == CharacterState.TALKING && currentEmotion != Emotion.NEUTRAL) {
            val watchdogMs = calculateEmotionWatchdogDurationMs(currentEmotion, fpsSettings)
            val token = coordinator.token
            talkJob = viewModelScope.launch {
                delay(watchdogMs)
                if (token != coordinator.token || coordinator.phase != ReplyPhase.FinalEmotion) return@launch
                // Watchdog recovery only triggers if normal animation completion callback was missed
                coordinator.onEmotionDisplayFinished()
                _ui.update { current ->
                    if (current.characterState == CharacterState.TALKING) {
                        current.copy(
                            characterState = coordinator.characterState,
                            emotion = coordinator.emotion,
                        )
                    } else {
                        current
                    }
                }
            }
        }
    }

    fun onSpeechStarted(utteranceId: String) {
        if (coordinator.onSpeechStarted(utteranceId)) {
            talkJob?.cancel()
            talkJob = null
            syncPlayback()
        }
    }

    fun onSpeechCompleted(utteranceId: String) {
        if (coordinator.onSpeechCompleted(utteranceId)) {
            talkJob?.cancel()
            talkJob = null
            syncPlayback()
            scheduleEmotionWatchdog()
        }
    }

    fun onSpeechError(utteranceId: String) {
        if (coordinator.onSpeechError(utteranceId)) {
            talkJob?.cancel()
            talkJob = null
            syncPlayback()
            scheduleEmotionWatchdog()
        }
    }

    fun onSpeechStopped(utteranceId: String) {
        if (coordinator.onSpeechStopped(utteranceId)) {
            talkJob?.cancel()
            talkJob = null
            syncPlayback()
            scheduleEmotionWatchdog()
        }
    }

    fun onSpeechNotStarted(utteranceId: String) {
        if (coordinator.activeUtteranceId == utteranceId) {
            onSpeechError(utteranceId)
        }
    }

    fun onScreenDisposed() {
        screenActive = false
        revealController.cancel()
        talkJob?.cancel()
        talkJob = null
        coordinator.onReset()
        _stopSpeechEvents.tryEmit(Unit)
        _ui.update { it.copy(characterState = CharacterState.IDLE, emotion = Emotion.NEUTRAL,
            reveal = null, speechActive = false, playbackToken = null) }
    }

    /**
     * Callback invoked when a one-shot emotional animation finishes playback.
     * Transitions character back to IDLE + NEUTRAL only if currently in an emotional TALKING state.
     */
    fun onCharacterAnimationFinished(token: String? = coordinator.token) {
        if (token != coordinator.token || coordinator.phase != ReplyPhase.FinalEmotion) return
        val s = _ui.value
        if (!canHandleAnimationFinished(s.characterState, s.emotion)) {
            return
        }
        talkJob?.cancel()
        talkJob = null
        coordinator.onEmotionDisplayFinished()
        _ui.update { it.reduceAnimationFinished() }
    }

    private fun fail(e: Throwable?) {
        revealController.cancel()
        talkJob?.cancel()
        talkJob = null
        coordinator.onReset()
        _stopSpeechEvents.tryEmit(Unit)
        _ui.update {
            it.copy(
                sending = false,
                reveal = null,
                speechActive = false,
                playbackToken = null,
                incomingAssistantId = null,
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
        entryCheckIn.leave()
        revealController.cancel()
        talkJob?.cancel()
        talkJob = null
        requestId = null
        conversationId.value = null
        coordinator.onReset()
        _stopSpeechEvents.tryEmit(Unit)
        _ui.value = ChatUiState()
        refresh()
    }

    companion object {
        fun factory(conversationId: String?) = viewModelFactory {
            initializer { ChatViewModel(assistantApp().container.repository, conversationId) }
        }
    }
}
