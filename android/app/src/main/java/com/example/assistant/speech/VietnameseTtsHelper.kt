package com.example.assistant.speech

import android.content.Context
import android.speech.tts.TextToSpeech
import android.speech.tts.UtteranceProgressListener
import android.util.Log
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.State
import androidx.compose.runtime.compositionLocalOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.ui.platform.LocalContext
import com.example.assistant.data.local.SettingsStore
import com.example.assistant.domain.SpeechSettings
import java.util.Locale
import java.util.UUID

private const val TAG = "VietnameseTtsHelper"

enum class TtsState {
    INITIALIZING,
    READY,
    UNAVAILABLE,
}

/**
 * Lifecycle and progress callbacks for speech utterances.
 */
interface TtsProgressListener {
    fun onStart(utteranceId: String) {}
    fun onDone(utteranceId: String) {}
    fun onError(utteranceId: String, errorCode: Int? = null) {}
    fun onStop(utteranceId: String, interrupted: Boolean = false) {}
}

private data class PendingSpeech(
    val text: String,
    val rate: Float,
    val pitch: Float,
    val utteranceId: String,
)

/**
 * Reusable, lifecycle-safe helper managing Android's built-in [TextToSpeech] engine
 * configured for Vietnamese speech.
 *
 * Requirements:
 * - Uses applicationContext to prevent Activity/window leaks.
 * - Sets Locale("vi", "VN") only after initialization success.
 * - Handles LANG_MISSING_DATA and LANG_NOT_SUPPORTED safely without crashing.
 * - Queues speech in pendingSpeech (text, rate, pitch, utteranceId) if speech is requested while initializing.
 * - Sets speech rate and pitch before speaking.
 * - Speaks with TextToSpeech.QUEUE_FLUSH to immediately interrupt preceding speech.
 * - Supports stop() and shutdown() lifecycle cleanup.
 * - Tracks utterance lifecycle via [TtsProgressListener].
 */
class VietnameseTtsHelper(context: Context) {
    private val appContext: Context = context.applicationContext
    private var tts: TextToSpeech? = null

    var listener: TtsProgressListener? = null

    private val _state = mutableStateOf(TtsState.INITIALIZING)
    val state: State<TtsState> = _state

    private val _errorMessage = mutableStateOf<String?>(null)
    val errorMessage: State<String?> = _errorMessage

    private var pendingSpeech: PendingSpeech? = null
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
                    val queued = pendingSpeech
                    pendingSpeech = null
                    if (queued != null) {
                        listener?.onError(queued.utteranceId)
                    }
                }
            }
        } catch (e: Exception) {
            Log.e(TAG, "Exception initializing TextToSpeech", e)
            _state.value = TtsState.UNAVAILABLE
            _errorMessage.value = "Lỗi khởi tạo giọng nói: ${e.message}"
            val queued = pendingSpeech
            pendingSpeech = null
            if (queued != null) {
                listener?.onError(queued.utteranceId)
            }
        }
    }

    private fun onTtsInitialized() {
        val engine = tts ?: return
        try {
            engine.setOnUtteranceProgressListener(object : UtteranceProgressListener() {
                override fun onStart(utteranceId: String?) {
                    if (utteranceId != null) {
                        listener?.onStart(utteranceId)
                    }
                }

                override fun onDone(utteranceId: String?) {
                    if (utteranceId != null) {
                        listener?.onDone(utteranceId)
                    }
                }

                @Deprecated("Deprecated in Java")
                override fun onError(utteranceId: String?) {
                    if (utteranceId != null) {
                        listener?.onError(utteranceId)
                    }
                }

                override fun onError(utteranceId: String?, errorCode: Int) {
                    if (utteranceId != null) {
                        listener?.onError(utteranceId, errorCode)
                    }
                }

                override fun onStop(utteranceId: String?, interrupted: Boolean) {
                    if (utteranceId != null) {
                        listener?.onStop(utteranceId, interrupted)
                    }
                }
            })

            val vietnamese = Locale("vi", "VN")
            val langResult = engine.setLanguage(vietnamese)
            when (langResult) {
                TextToSpeech.LANG_MISSING_DATA, TextToSpeech.LANG_NOT_SUPPORTED -> {
                    Log.w(TAG, "Vietnamese language not supported or missing data: $langResult")
                    _state.value = TtsState.UNAVAILABLE
                    _errorMessage.value = "Chưa hỗ trợ giọng nói tiếng Việt trên thiết bị này."
                    val queued = pendingSpeech
                    pendingSpeech = null
                    if (queued != null) {
                        listener?.onError(queued.utteranceId)
                    }
                }
                else -> {
                    _state.value = TtsState.READY
                    _errorMessage.value = null
                    val queued = pendingSpeech
                    pendingSpeech = null
                    if (queued != null && queued.text.isNotBlank()) {
                        speakInternal(queued.text, queued.rate, queued.pitch, queued.utteranceId)
                    }
                }
            }
        } catch (e: Exception) {
            Log.e(TAG, "Exception setting Vietnamese language", e)
            _state.value = TtsState.UNAVAILABLE
            _errorMessage.value = "Lỗi thiết lập tiếng Việt: ${e.message}"
            val queued = pendingSpeech
            pendingSpeech = null
            if (queued != null) {
                listener?.onError(queued.utteranceId)
            }
        }
    }

    /**
     * Speaks the provided text in Vietnamese using QUEUE_FLUSH, configured with [rate] and [pitch].
     * If TTS is still initializing, queues the request with its parameters to be spoken upon completion.
     */
    fun speak(
        text: String,
        rate: Float = SpeechSettings.DEFAULT_RATE,
        pitch: Float = SpeechSettings.DEFAULT_PITCH,
        utteranceId: String = UUID.randomUUID().toString(),
    ) {
        if (isDisposed || text.isBlank()) return
        val normalizedRate = SpeechSettings.normalize(rate, SpeechSettings.MIN_RATE, SpeechSettings.MAX_RATE)
        val normalizedPitch = SpeechSettings.normalize(pitch, SpeechSettings.MIN_PITCH, SpeechSettings.MAX_PITCH)
        when (_state.value) {
            TtsState.INITIALIZING -> {
                pendingSpeech = PendingSpeech(text, normalizedRate, normalizedPitch, utteranceId)
            }
            TtsState.READY -> {
                speakInternal(text, normalizedRate, normalizedPitch, utteranceId)
            }
            TtsState.UNAVAILABLE -> {
                Log.d(TAG, "Cannot speak because TTS is unavailable: ${_errorMessage.value}")
                listener?.onError(utteranceId)
            }
        }
    }

    /**
     * Convenience overload accepting [SpeechSettings].
     */
    fun speak(
        text: String,
        settings: SpeechSettings,
        utteranceId: String = UUID.randomUUID().toString(),
    ) {
        speak(text, settings.speechRate, settings.pitch, utteranceId)
    }

    private fun speakInternal(text: String, rate: Float, pitch: Float, utteranceId: String) {
        val engine = tts ?: run {
            listener?.onError(utteranceId)
            return
        }
        try {
            val rateResult = engine.setSpeechRate(rate)
            if (rateResult == TextToSpeech.ERROR) {
                Log.w(TAG, "Failed to set speech rate: $rate")
            }
            val pitchResult = engine.setPitch(pitch)
            if (pitchResult == TextToSpeech.ERROR) {
                Log.w(TAG, "Failed to set pitch: $pitch")
            }
            val speakResult = engine.speak(text, TextToSpeech.QUEUE_FLUSH, null, utteranceId)
            if (speakResult == TextToSpeech.ERROR) {
                Log.w(TAG, "Failed to speak text: $text")
                _errorMessage.value = "Lỗi khi phát âm thanh."
                listener?.onError(utteranceId)
            }
        } catch (e: Exception) {
            Log.e(TAG, "Exception speaking text", e)
            _errorMessage.value = "Lỗi khi phát giọng nói: ${e.message}"
            listener?.onError(utteranceId)
        }
    }

    /**
     * Stops any speech currently in progress and clears pending queued speech.
     */
    fun stop() {
        pendingSpeech = null
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
        pendingSpeech = null
        listener = null
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
