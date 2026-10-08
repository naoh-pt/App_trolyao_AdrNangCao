package com.example.assistant.domain

import androidx.compose.runtime.compositionLocalOf
import java.util.Locale

/**
 * Immutable domain model representing Text-to-Speech settings:
 * - [enabled]: Whether spoken answers are active.
 * - [speechRate]: Speech rate multiplier (0.5x .. 2.0x, step 0.1, default 1.0x).
 * - [pitch]: Voice pitch multiplier (0.5x .. 2.0x, step 0.1, default 1.0x).
 *
 * Independent of Android Context, Compose UI, and TextToSpeech engine.
 */
data class SpeechSettings(
    val enabled: Boolean = DEFAULT_ENABLED,
    val speechRate: Float = DEFAULT_RATE,
    val pitch: Float = DEFAULT_PITCH,
) {
    /**
     * Returns a copy with [enabled] updated.
     */
    fun withEnabled(newEnabled: Boolean): SpeechSettings =
        copy(enabled = newEnabled)

    /**
     * Returns a copy with [speechRate] updated, clamped and normalized to 1 decimal place.
     */
    fun withSpeechRate(newRate: Float): SpeechSettings =
        copy(speechRate = normalize(newRate, MIN_RATE, MAX_RATE))

    /**
     * Returns a copy with [pitch] updated, clamped and normalized to 1 decimal place.
     */
    fun withPitch(newPitch: Float): SpeechSettings =
        copy(pitch = normalize(newPitch, MIN_PITCH, MAX_PITCH))

    /**
     * Adjusts [speechRate] by [delta] (e.g. +0.1 or -0.1), clamped and normalized.
     */
    fun withStepRate(delta: Float): SpeechSettings =
        withSpeechRate(speechRate + delta)

    /**
     * Adjusts [pitch] by [delta] (e.g. +0.1 or -0.1), clamped and normalized.
     */
    fun withStepPitch(delta: Float): SpeechSettings =
        withPitch(pitch + delta)

    /**
     * Resets rate and pitch to defaults (1.0x) while preserving [enabled].
     */
    fun resetVoiceDefaults(): SpeechSettings =
        copy(speechRate = DEFAULT_RATE, pitch = DEFAULT_PITCH)

    fun canDecreaseRate(): Boolean = speechRate > MIN_RATE + EPSILON
    fun canIncreaseRate(): Boolean = speechRate < MAX_RATE - EPSILON
    fun canDecreasePitch(): Boolean = pitch > MIN_PITCH + EPSILON
    fun canIncreasePitch(): Boolean = pitch < MAX_PITCH - EPSILON

    companion object {
        const val DEFAULT_ENABLED: Boolean = true
        const val DEFAULT_RATE: Float = 1.0f
        const val DEFAULT_PITCH: Float = 1.0f

        const val MIN_RATE: Float = 0.5f
        const val MAX_RATE: Float = 2.0f

        const val MIN_PITCH: Float = 0.5f
        const val MAX_PITCH: Float = 2.0f

        const val STEP: Float = 0.1f
        private const val EPSILON: Float = 0.001f

        val DEFAULT = SpeechSettings(
            enabled = DEFAULT_ENABLED,
            speechRate = DEFAULT_RATE,
            pitch = DEFAULT_PITCH,
        )

        /**
         * Clamps [value] to [[min]..[max]] and rounds to 1 decimal place to prevent floating-point drift.
         */
        fun normalize(value: Float, min: Float = MIN_RATE, max: Float = MAX_RATE): Float {
            val clamped = value.coerceIn(min, max)
            return Math.round(clamped * 10f) / 10f
        }

        /**
         * Formats float multiplier as "1.0x", "1.5x", etc.
         */
        fun formatMultiplier(value: Float): String {
            return String.format(Locale.US, "%.1fx", normalize(value))
        }
    }
}

/**
 * CompositionLocal providing [SpeechSettings] across the entire Compose hierarchy.
 * Defaults to [SpeechSettings.DEFAULT] when no provider is present (e.g. tests or previews).
 */
val LocalSpeechSettings = compositionLocalOf { SpeechSettings.DEFAULT }
