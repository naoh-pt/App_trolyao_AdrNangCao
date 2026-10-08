package com.example.assistant.speech

import android.content.Context
import android.speech.tts.TextToSpeech
import android.util.Log
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.State
import androidx.compose.runtime.compositionLocalOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.ui.platform.LocalContext
import com.example.assistant.data.local.SettingsStore
import java.util.Locale
import java.util.UUID

private const val TAG = "VietnameseTtsHelper"

enum class TtsState {
    INITIALIZING,
    READY,
    UNAVAILABLE,
}

/**
 * Reusable, lifecycle-safe helper managing Android's built-in [TextToSpeech] engine
 * configured for Vietnamese speech.
 *
 * Requirements:
 * - Uses applicationContext to prevent Activity/window leaks.
 * - Sets Locale("vi", "VN") only after initialization success.
 * - Handles LANG_MISSING_DATA and LANG_NOT_SUPPORTED safely without crashing.
 * - Queues speech in pendingText if speech is requested while initializing.
 * - Speaks with TextToSpeech.QUEUE_FLUSH to immediately interrupt preceding speech.
 * - Supports stop() and shutdown() lifecycle cleanup.
 */
class VietnameseTtsHelper(context: Context) {
    private val appContext: Context = context.applicationContext
    private var tts: TextToSpeech? = null

    private val _state = mutableStateOf(TtsState.INITIALIZING)
    val state: State<TtsState> = _state

    private val _errorMessage = mutableStateOf<String?>(null)
    val errorMessage: State<String?> = _errorMessage

    private var pendingText: String? = null
    private var isDisposed = false

    val isReady: Boolean
        get() = _state.value == TtsState.READY

    init {
        try {
            tts = TextToSpeech(appContext) { status ->
                if (isDisposed) return@TextToSpeech
                if (status == TextToSpeech.SUCCESS) {
                    onTtsInitialized()
                } else {
                    Log.w(TAG, "TextToSpeech init failed with status: $status")
                    _state.value = TtsState.UNAVAILABLE
                    _errorMessage.value = "Không thể khởi tạo công cụ giọng nói."
                    pendingText = null
                }
            }
        } catch (e: Exception) {
            Log.e(TAG, "Exception initializing TextToSpeech", e)
            _state.value = TtsState.UNAVAILABLE
            _errorMessage.value = "Lỗi khởi tạo giọng nói: ${e.message}"
            pendingText = null
        }
    }

    private fun onTtsInitialized() {
        val engine = tts ?: return
        try {
            val vietnamese = Locale("vi", "VN")
            val langResult = engine.setLanguage(vietnamese)
            when (langResult) {
                TextToSpeech.LANG_MISSING_DATA, TextToSpeech.LANG_NOT_SUPPORTED -> {
                    Log.w(TAG, "Vietnamese language not supported or missing data: $langResult")
                    _state.value = TtsState.UNAVAILABLE
                    _errorMessage.value = "Chưa hỗ trợ giọng nói tiếng Việt trên thiết bị này."
                    pendingText = null
                }
                else -> {
                    _state.value = TtsState.READY
                    _errorMessage.value = null
                    val queued = pendingText
                    pendingText = null
                    if (!queued.isNullOrBlank()) {
                        speakInternal(queued)
                    }
                }
            }
        } catch (e: Exception) {
            Log.e(TAG, "Exception setting Vietnamese language", e)
            _state.value = TtsState.UNAVAILABLE
            _errorMessage.value = "Lỗi thiết lập tiếng Việt: ${e.message}"
            pendingText = null
        }
    }

    /**
     * Speaks the provided text in Vietnamese using QUEUE_FLUSH.
     * If TTS is still initializing, queues the text to be spoken upon completion.
     */
    fun speak(text: String) {
        if (isDisposed || text.isBlank()) return
        when (_state.value) {
            TtsState.INITIALIZING -> {
                pendingText = text
            }
            TtsState.READY -> {
                speakInternal(text)
            }
            TtsState.UNAVAILABLE -> {
                Log.d(TAG, "Cannot speak because TTS is unavailable: ${_errorMessage.value}")
            }
        }
    }

    private fun speakInternal(text: String) {
        val engine = tts ?: return
        val utteranceId = UUID.randomUUID().toString()
        try {
            engine.speak(text, TextToSpeech.QUEUE_FLUSH, null, utteranceId)
        } catch (e: Exception) {
            Log.e(TAG, "Exception speaking text", e)
        }
    }

    /**
     * Stops any speech currently in progress and clears pending queued text.
     */
    fun stop() {
        pendingText = null
        try {
            tts?.stop()
        } catch (e: Exception) {
            Log.e(TAG, "Exception stopping TTS", e)
        }
    }

    /**
     * Shuts down the TextToSpeech engine and releases native audio resources.
     */
    fun shutdown() {
        isDisposed = true
        pendingText = null
        try {
            tts?.stop()
            tts?.shutdown()
        } catch (e: Exception) {
            Log.e(TAG, "Exception shutting down TTS", e)
        } finally {
            tts = null
        }
    }
}

/**
 * Creates and remembers a lifecycle-managed [VietnameseTtsHelper] instance.
 * Automatically shuts down when leaving composition.
 */
@Composable
fun rememberVietnameseTts(): VietnameseTtsHelper {
    val context = LocalContext.current.applicationContext
    val helper = remember { VietnameseTtsHelper(context) }
    DisposableEffect(helper) {
        onDispose {
            helper.shutdown()
        }
    }
    return helper
}

/**
 * CompositionLocal providing global TTS enabled state across screens.
 */
val LocalTtsEnabled = compositionLocalOf { SettingsStore.DEFAULT_TTS_ENABLED }
