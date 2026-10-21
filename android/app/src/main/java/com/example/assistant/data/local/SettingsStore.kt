package com.example.assistant.data.local

import android.content.Context
import androidx.datastore.preferences.core.booleanPreferencesKey
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.MutablePreferences
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.floatPreferencesKey
import androidx.datastore.preferences.core.intPreferencesKey
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import com.example.assistant.domain.AnimationFpsSettings
import com.example.assistant.domain.ChatDisplaySettings
import com.example.assistant.domain.SpeechSettings
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.map
import okhttp3.HttpUrl.Companion.toHttpUrlOrNull
import java.util.UUID

private val Context.dataStore by preferencesDataStore(name = "settings")

/** Shared by DataStore and JVM persistence tests, including installations without this key. */
internal object TypewriterPreference {
    private val key = booleanPreferencesKey("typewriter_enabled")
    fun read(preferences: Preferences): Boolean = preferences[key] ?: true
    fun write(preferences: MutablePreferences, enabled: Boolean) { preferences[key] = enabled }
}

class SettingsStore(private val context: Context) {
    private val clientIdKey = stringPreferencesKey("client_id")
    private val baseUrlKey = stringPreferencesKey("base_url")

    private val ttsEnabledKey = booleanPreferencesKey("tts_enabled")
    private val speechRateKey = floatPreferencesKey("speech_rate")
    private val speechPitchKey = floatPreferencesKey("speech_pitch")

    private val messageFontSizeKey = intPreferencesKey("message_font_size_sp")

    private val idleFpsKey = intPreferencesKey("fps_idle")
    private val thinkingFpsKey = intPreferencesKey("fps_thinking")
    private val talkFpsKey = intPreferencesKey("fps_talk")
    private val happyFpsKey = intPreferencesKey("fps_happy")
    private val sadFpsKey = intPreferencesKey("fps_sad")
    private val surprisedFpsKey = intPreferencesKey("fps_surprised")

    private fun keyForAction(actionName: String) = when (actionName) {
        AnimationFpsSettings.ACTION_IDLE -> idleFpsKey
        AnimationFpsSettings.ACTION_THINKING -> thinkingFpsKey
        AnimationFpsSettings.ACTION_TALK -> talkFpsKey
        AnimationFpsSettings.ACTION_HAPPY -> happyFpsKey
        AnimationFpsSettings.ACTION_SAD -> sadFpsKey
        AnimationFpsSettings.ACTION_SURPRISED -> surprisedFpsKey
        else -> null
    }

    @Volatile
    private var cachedClientId: String? = null

    val baseUrl: Flow<String> = context.dataStore.data.map { prefs ->
        val saved = prefs[baseUrlKey]
        if (saved != null) {
            normalize(saved) ?: DEFAULT_BASE_URL
        } else {
            DEFAULT_BASE_URL
        }
    }

    suspend fun setBaseUrl(url: String) {
        val normalized = normalize(url) ?: return
        context.dataStore.edit { it[baseUrlKey] = normalized }
    }

    val speechSettings: Flow<SpeechSettings> = context.dataStore.data.map { prefs ->
        SpeechSettings(
            enabled = prefs[ttsEnabledKey] ?: SpeechSettings.DEFAULT_ENABLED,
            speechRate = SpeechSettings.normalize(prefs[speechRateKey] ?: SpeechSettings.DEFAULT_RATE),
            pitch = SpeechSettings.normalize(prefs[speechPitchKey] ?: SpeechSettings.DEFAULT_PITCH),
        )
    }

    val ttsEnabled: Flow<Boolean> = speechSettings.map { it.enabled }

    suspend fun setTtsEnabled(enabled: Boolean) {
        context.dataStore.edit { it[ttsEnabledKey] = enabled }
    }

    suspend fun setSpeechRate(rate: Float) {
        val normalized = SpeechSettings.normalize(rate)
        context.dataStore.edit { it[speechRateKey] = normalized }
    }

    suspend fun setPitch(pitch: Float) {
        val normalized = SpeechSettings.normalize(pitch)
        context.dataStore.edit { it[speechPitchKey] = normalized }
    }

    suspend fun adjustSpeechRate(delta: Float) {
        context.dataStore.edit { prefs ->
            val current = prefs[speechRateKey] ?: SpeechSettings.DEFAULT_RATE
            prefs[speechRateKey] = SpeechSettings.normalize(current + delta)
        }
    }

    suspend fun adjustPitch(delta: Float) {
        context.dataStore.edit { prefs ->
            val current = prefs[speechPitchKey] ?: SpeechSettings.DEFAULT_PITCH
            prefs[speechPitchKey] = SpeechSettings.normalize(current + delta)
        }
    }

    suspend fun resetSpeechVoiceDefaults() {
        context.dataStore.edit { prefs ->
            prefs[speechRateKey] = SpeechSettings.DEFAULT_RATE
            prefs[speechPitchKey] = SpeechSettings.DEFAULT_PITCH
        }
    }

    val chatDisplaySettings: Flow<ChatDisplaySettings> = context.dataStore.data.map { prefs ->
        ChatDisplaySettings(
            fontSizeSp = ChatDisplaySettings.clampFontSize(
                prefs[messageFontSizeKey] ?: ChatDisplaySettings.DEFAULT_FONT_SIZE_SP
            ),
            typewriterEnabled = TypewriterPreference.read(prefs),
        )
    }

    suspend fun setTypewriterEnabled(enabled: Boolean) {
        context.dataStore.edit { TypewriterPreference.write(it, enabled) }
    }

    suspend fun setMessageFontSize(fontSizeSp: Int) {
        val clamped = ChatDisplaySettings.clampFontSize(fontSizeSp)
        context.dataStore.edit { it[messageFontSizeKey] = clamped }
    }

    suspend fun adjustMessageFontSize(delta: Int) {
        context.dataStore.edit { prefs ->
            val current = prefs[messageFontSizeKey] ?: ChatDisplaySettings.DEFAULT_FONT_SIZE_SP
            prefs[messageFontSizeKey] = ChatDisplaySettings.clampFontSize(current + delta)
        }
    }

    suspend fun resetMessageFontSize() {
        context.dataStore.edit { prefs ->
            prefs[messageFontSizeKey] = ChatDisplaySettings.DEFAULT_FONT_SIZE_SP
        }
    }

    val animationFpsSettings: Flow<AnimationFpsSettings> = context.dataStore.data.map { prefs ->
        AnimationFpsSettings(
            idle = AnimationFpsSettings.clampFps(prefs[idleFpsKey] ?: AnimationFpsSettings.DEFAULT_IDLE_FPS),
            thinking = AnimationFpsSettings.clampFps(prefs[thinkingFpsKey] ?: AnimationFpsSettings.DEFAULT_THINKING_FPS),
            talk = AnimationFpsSettings.clampFps(prefs[talkFpsKey] ?: AnimationFpsSettings.DEFAULT_TALK_FPS),
            happy = AnimationFpsSettings.clampFps(prefs[happyFpsKey] ?: AnimationFpsSettings.DEFAULT_HAPPY_FPS),
            sad = AnimationFpsSettings.clampFps(prefs[sadFpsKey] ?: AnimationFpsSettings.DEFAULT_SAD_FPS),
            surprised = AnimationFpsSettings.clampFps(prefs[surprisedFpsKey] ?: AnimationFpsSettings.DEFAULT_SURPRISED_FPS),
        )
    }

    suspend fun adjustFps(actionName: String, delta: Int) {
        val key = keyForAction(actionName) ?: return
        val defaultFps = AnimationFpsSettings.DEFAULT.fpsFor(actionName)
        context.dataStore.edit { prefs ->
            val current = prefs[key] ?: defaultFps
            val updated = AnimationFpsSettings.clampFps(current + delta)
            prefs[key] = updated
        }
    }

    suspend fun setFps(actionName: String, fps: Int) {
        val key = keyForAction(actionName) ?: return
        context.dataStore.edit { prefs ->
            prefs[key] = AnimationFpsSettings.clampFps(fps)
        }
    }

    suspend fun resetFpsToDefaults() {
        context.dataStore.edit { prefs ->
            prefs[idleFpsKey] = AnimationFpsSettings.DEFAULT_IDLE_FPS
            prefs[thinkingFpsKey] = AnimationFpsSettings.DEFAULT_THINKING_FPS
            prefs[talkFpsKey] = AnimationFpsSettings.DEFAULT_TALK_FPS
            prefs[happyFpsKey] = AnimationFpsSettings.DEFAULT_HAPPY_FPS
            prefs[sadFpsKey] = AnimationFpsSettings.DEFAULT_SAD_FPS
            prefs[surprisedFpsKey] = AnimationFpsSettings.DEFAULT_SURPRISED_FPS
        }
    }

    /** UUID tạo một lần duy nhất cho mỗi bản cài đặt, gửi qua header X-Client-Id. */
    suspend fun clientId(): String {
        cachedClientId?.let { return it }
        var result = ""
        context.dataStore.edit { prefs ->
            val existing = prefs[clientIdKey]
            result = existing ?: UUID.randomUUID().toString().also { prefs[clientIdKey] = it }
        }
        cachedClientId = result
        return result
    }

    companion object {
        const val DEFAULT_BASE_URL = "http://10.0.2.2:8000/" // emulator -> laptop
        const val DEFAULT_TTS_ENABLED = true

        /**
         * Trả về Retrofit base URL chuẩn hóa ending in '/' hoặc null nếu không hợp lệ.
         * Quy tắc:
         * 1. Trim whitespace.
         * 2. Thêm http:// nếu thiếu scheme.
         * 3. Xóa trailing slashes.
         * 4. Xóa 1 đoạn trailing /api/v1 (case-sensitive) nếu có.
         * 5. Trả về URL kết thúc bằng đúng 1 '/'.
         * 6. Từ chối URL rỗng hoặc không hợp lệ.
         */
        fun normalize(raw: String): String? {
            var s = raw.trim()
            if (s.isEmpty()) return null
            if (!s.startsWith("http://") && !s.startsWith("https://")) {
                s = "http://$s"
            }
            s = s.trimEnd('/')
            if (s.endsWith("/api/v1")) {
                s = s.substring(0, s.length - "/api/v1".length).trimEnd('/')
            }
            val url = "$s/"
            val parsed = url.toHttpUrlOrNull() ?: return null
            if (parsed.host.isEmpty()) return null
            return url
        }
    }
}
