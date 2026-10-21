package com.example.assistant.domain

import androidx.compose.runtime.compositionLocalOf

/**
 * Immutable domain model representing chat message display settings.
 *
 * Single source of truth for:
 * - Message font size (12sp .. 20sp, default 14sp).
 * - Matching line height calculation (fontSizeSp + 4).
 *
 * Independent of Android Context and TextToSpeech engine.
 */
data class ChatDisplaySettings(
    val fontSizeSp: Int = DEFAULT_FONT_SIZE_SP,
    val typewriterEnabled: Boolean = true,
) {
    val lineHeightSp: Int
        get() = fontSizeSp + LINE_HEIGHT_OFFSET_SP

    fun withFontSize(size: Int): ChatDisplaySettings =
        copy(fontSizeSp = clampFontSize(size))

    fun withStep(delta: Int): ChatDisplaySettings =
        withFontSize(fontSizeSp + delta)

    fun resetDefaults(): ChatDisplaySettings =
        copy(fontSizeSp = DEFAULT_FONT_SIZE_SP)

    fun canDecrease(): Boolean = fontSizeSp > MIN_FONT_SIZE_SP
    fun canIncrease(): Boolean = fontSizeSp < MAX_FONT_SIZE_SP

    companion object {
        const val MIN_FONT_SIZE_SP = 12
        const val MAX_FONT_SIZE_SP = 20
        const val DEFAULT_FONT_SIZE_SP = 14
        const val STEP_FONT_SIZE_SP = 1
        const val LINE_HEIGHT_OFFSET_SP = 4

        val DEFAULT = ChatDisplaySettings()

        fun clampFontSize(size: Int): Int =
            size.coerceIn(MIN_FONT_SIZE_SP, MAX_FONT_SIZE_SP)

        fun calculateLineHeight(fontSize: Int): Int =
            clampFontSize(fontSize) + LINE_HEIGHT_OFFSET_SP
    }
}

/**
 * CompositionLocal providing [ChatDisplaySettings] across the Compose hierarchy.
 * Defaults to [ChatDisplaySettings.DEFAULT].
 */
val LocalChatDisplaySettings = compositionLocalOf { ChatDisplaySettings.DEFAULT }
