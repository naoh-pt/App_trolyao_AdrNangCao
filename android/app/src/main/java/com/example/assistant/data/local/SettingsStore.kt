package com.example.assistant.data.local

import android.content.Context
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.intPreferencesKey
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import com.example.assistant.domain.AnimationFpsSettings
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.map
import okhttp3.HttpUrl.Companion.toHttpUrlOrNull
import java.util.UUID

private val Context.dataStore by preferencesDataStore(name = "settings")

class SettingsStore(private val context: Context) {
    private val clientIdKey = stringPreferencesKey("client_id")
    private val baseUrlKey = stringPreferencesKey("base_url")

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
