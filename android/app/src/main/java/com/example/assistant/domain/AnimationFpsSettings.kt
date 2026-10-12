package com.example.assistant.domain

import androidx.compose.runtime.compositionLocalOf
import com.example.assistant.ui.character.CharacterAnimationSpec

/**
 * Immutable domain model representing animation FPS settings for all six character actions.
 *
 * Serves as the single source of truth for:
 * - Default FPS values.
 * - Allowed FPS bounds (4..20).
 * - Action names and pure transformation/clamping logic.
 */
data class AnimationFpsSettings(
    val idle: Int = DEFAULT_IDLE_FPS,
    val thinking: Int = DEFAULT_THINKING_FPS,
    val talk: Int = DEFAULT_TALK_FPS,
    val happy: Int = DEFAULT_HAPPY_FPS,
    val sad: Int = DEFAULT_SAD_FPS,
    val surprised: Int = DEFAULT_SURPRISED_FPS,
) {
    /**
     * Resolves the configured FPS for a given action name.
     */
    fun fpsFor(actionName: String): Int = when (actionName) {
        ACTION_IDLE -> idle
        ACTION_THINKING -> thinking
        ACTION_TALK -> talk
        ACTION_HAPPY -> happy
        ACTION_SAD -> sad
        ACTION_SURPRISED -> surprised
        else -> idle
    }

    /**
     * Returns an immutable copy with the specified action updated to [newFps] (clamped).
     */
    fun withFps(actionName: String, newFps: Int): AnimationFpsSettings {
        val clamped = clampFps(newFps)
        return when (actionName) {
            ACTION_IDLE -> copy(idle = clamped)
            ACTION_THINKING -> copy(thinking = clamped)
            ACTION_TALK -> copy(talk = clamped)
            ACTION_HAPPY -> copy(happy = clamped)
            ACTION_SAD -> copy(sad = clamped)
            ACTION_SURPRISED -> copy(surprised = clamped)
            else -> this
        }
    }

    /**
     * Returns an immutable copy with the specified action adjusted by [delta] (clamped).
     */
    fun withStep(actionName: String, delta: Int): AnimationFpsSettings {
        return withFps(actionName, fpsFor(actionName) + delta)
    }

    /**
     * Applies this FPS setting to a base [CharacterAnimationSpec], returning a new spec
     * with the effective FPS. Frames, actionName, and playbackMode are strictly preserved.
     */
    fun applyOverride(baseSpec: CharacterAnimationSpec): CharacterAnimationSpec {
        val effectiveFps = fpsFor(baseSpec.actionName)
        return if (baseSpec.fps == effectiveFps) {
            baseSpec
        } else {
            baseSpec.copy(fps = effectiveFps)
        }
    }

    companion object {
        const val MIN_FPS = 4
        const val MAX_FPS = 20

        const val DEFAULT_IDLE_FPS = 5
        const val DEFAULT_THINKING_FPS = 8
        const val DEFAULT_TALK_FPS = 10
        const val DEFAULT_HAPPY_FPS = 10
        const val DEFAULT_SAD_FPS = 8
        const val DEFAULT_SURPRISED_FPS = 10

        const val ACTION_IDLE = "idle"
        const val ACTION_THINKING = "thinking"
        const val ACTION_TALK = "talk"
        const val ACTION_HAPPY = "happy"
        const val ACTION_SAD = "sad"
        const val ACTION_SURPRISED = "surprised"

        val ALL_ACTIONS: List<String> = listOf(
            ACTION_IDLE,
            ACTION_THINKING,
            ACTION_TALK,
            ACTION_HAPPY,
            ACTION_SAD,
            ACTION_SURPRISED,
        )

        val DEFAULT = AnimationFpsSettings(
            idle = DEFAULT_IDLE_FPS,
            thinking = DEFAULT_THINKING_FPS,
            talk = DEFAULT_TALK_FPS,
            happy = DEFAULT_HAPPY_FPS,
            sad = DEFAULT_SAD_FPS,
            surprised = DEFAULT_SURPRISED_FPS,
        )

        fun clampFps(fps: Int): Int = fps.coerceIn(MIN_FPS, MAX_FPS)
    }
}

/**
 * CompositionLocal providing [AnimationFpsSettings] across the entire Compose hierarchy.
 * Defaults to [AnimationFpsSettings.DEFAULT] when no provider is present (e.g. tests or previews).
 */
val LocalAnimationFpsSettings = compositionLocalOf { AnimationFpsSettings.DEFAULT }
