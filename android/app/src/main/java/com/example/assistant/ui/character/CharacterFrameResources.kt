package com.example.assistant.ui.character

import androidx.annotation.DrawableRes
import com.example.assistant.R

/**
 * Playback mode for character frame animation.
 */
enum class PlaybackMode {
    LOOP,
    ONE_SHOT,
}

/**
 * Lightweight metadata specification for character frame animation actions.
 * Contains only compile-time integer drawable resource IDs, timing, and playback mode.
 * No reflection, dynamic resource lookup, or bitmap decoding.
 */
data class CharacterAnimationSpec(
    val actionName: String,
    @DrawableRes val frames: IntArray,
    val fps: Int,
    val mode: PlaybackMode,
) {
    val frameDurationMs: Long get() = (1000L / fps)
    val totalDurationMs: Long get() = frames.size * frameDurationMs
    val isLooping: Boolean get() = mode == PlaybackMode.LOOP

    override fun equals(other: Any?): Boolean {
        if (this === other) return true
        if (javaClass != other?.javaClass) return false

        other as CharacterAnimationSpec

        if (actionName != other.actionName) return false
        if (!frames.contentEquals(other.frames)) return false
        if (fps != other.fps) return false
        if (mode != other.mode) return false

        return true
    }

    override fun hashCode(): Int {
        var result = actionName.hashCode()
        result = 31 * result + frames.contentHashCode()
        result = 31 * result + fps
        result = 31 * result + mode.hashCode()
        return result
    }
}

/**
 * Direct compile-time resource arrays for character frame animations.
 * Numeric ordering is strictly preserved.
 * Errant frame happy_0016 is excluded.
 */
val idleFrames = intArrayOf(
    R.drawable.character_idle_0001,
    R.drawable.character_idle_0002,
    R.drawable.character_idle_0003,
    R.drawable.character_idle_0004,
    R.drawable.character_idle_0005,
    R.drawable.character_idle_0006,
    R.drawable.character_idle_0007,
    R.drawable.character_idle_0008,
    R.drawable.character_idle_0009,
    R.drawable.character_idle_0010,
    R.drawable.character_idle_0011,
    R.drawable.character_idle_0012,
    R.drawable.character_idle_0013,
    R.drawable.character_idle_0014,
    R.drawable.character_idle_0015,
    R.drawable.character_idle_0016,
    R.drawable.character_idle_0017,
    R.drawable.character_idle_0018,
    R.drawable.character_idle_0019,
    R.drawable.character_idle_0020,
    R.drawable.character_idle_0021,
    R.drawable.character_idle_0022,
    R.drawable.character_idle_0023,
    R.drawable.character_idle_0024,
    R.drawable.character_idle_0025,
    R.drawable.character_idle_0026,
    R.drawable.character_idle_0027,
    R.drawable.character_idle_0028,
    R.drawable.character_idle_0029,
    R.drawable.character_idle_0030,
    R.drawable.character_idle_0031,
    R.drawable.character_idle_0032,
)

val thinkingFrames = intArrayOf(
    R.drawable.character_thinking_0001,
    R.drawable.character_thinking_0002,
    R.drawable.character_thinking_0003,
    R.drawable.character_thinking_0004,
    R.drawable.character_thinking_0005,
    R.drawable.character_thinking_0006,
    R.drawable.character_thinking_0007,
    R.drawable.character_thinking_0008,
    R.drawable.character_thinking_0009,
    R.drawable.character_thinking_0010,
    R.drawable.character_thinking_0011,
    R.drawable.character_thinking_0012,
    R.drawable.character_thinking_0013,
    R.drawable.character_thinking_0014,
    R.drawable.character_thinking_0015,
    R.drawable.character_thinking_0016,
    R.drawable.character_thinking_0017,
    R.drawable.character_thinking_0018,
    R.drawable.character_thinking_0019,
    R.drawable.character_thinking_0020,
    R.drawable.character_thinking_0021,
    R.drawable.character_thinking_0022,
    R.drawable.character_thinking_0023,
    R.drawable.character_thinking_0024,
    R.drawable.character_thinking_0025,
    R.drawable.character_thinking_0026,
    R.drawable.character_thinking_0027,
    R.drawable.character_thinking_0028,
    R.drawable.character_thinking_0029,
    R.drawable.character_thinking_0030,
)

val talkFrames = intArrayOf(
    R.drawable.character_talk_0001,
    R.drawable.character_talk_0002,
    R.drawable.character_talk_0003,
    R.drawable.character_talk_0004,
    R.drawable.character_talk_0005,
    R.drawable.character_talk_0006,
    R.drawable.character_talk_0007,
    R.drawable.character_talk_0008,
    R.drawable.character_talk_0009,
    R.drawable.character_talk_0010,
    R.drawable.character_talk_0011,
    R.drawable.character_talk_0012,
    R.drawable.character_talk_0013,
    R.drawable.character_talk_0014,
    R.drawable.character_talk_0015,
    R.drawable.character_talk_0016,
    R.drawable.character_talk_0017,
    R.drawable.character_talk_0018,
    R.drawable.character_talk_0019,
)

val happyFrames = intArrayOf(
    R.drawable.character_happy_0001,
    R.drawable.character_happy_0002,
    R.drawable.character_happy_0003,
    R.drawable.character_happy_0004,
    R.drawable.character_happy_0005,
    R.drawable.character_happy_0006,
    R.drawable.character_happy_0007,
    R.drawable.character_happy_0008,
    R.drawable.character_happy_0009,
    R.drawable.character_happy_0010,
    R.drawable.character_happy_0011,
    R.drawable.character_happy_0012,
    R.drawable.character_happy_0013,
    R.drawable.character_happy_0014,
    R.drawable.character_happy_0015,
)

val sadFrames = intArrayOf(
    R.drawable.character_sad_0001,
    R.drawable.character_sad_0002,
    R.drawable.character_sad_0003,
    R.drawable.character_sad_0004,
    R.drawable.character_sad_0005,
    R.drawable.character_sad_0006,
    R.drawable.character_sad_0007,
    R.drawable.character_sad_0008,
    R.drawable.character_sad_0009,
    R.drawable.character_sad_0010,
    R.drawable.character_sad_0011,
    R.drawable.character_sad_0012,
    R.drawable.character_sad_0013,
    R.drawable.character_sad_0014,
    R.drawable.character_sad_0015,
    R.drawable.character_sad_0016,
    R.drawable.character_sad_0017,
    R.drawable.character_sad_0018,
    R.drawable.character_sad_0019,
    R.drawable.character_sad_0020,
    R.drawable.character_sad_0021,
)

val surprisedFrames = intArrayOf(
    R.drawable.character_surprised_0001,
    R.drawable.character_surprised_0002,
    R.drawable.character_surprised_0003,
    R.drawable.character_surprised_0004,
    R.drawable.character_surprised_0005,
    R.drawable.character_surprised_0006,
    R.drawable.character_surprised_0007,
    R.drawable.character_surprised_0008,
    R.drawable.character_surprised_0009,
    R.drawable.character_surprised_0010,
    R.drawable.character_surprised_0011,
    R.drawable.character_surprised_0012,
    R.drawable.character_surprised_0013,
    R.drawable.character_surprised_0014,
    R.drawable.character_surprised_0015,
    R.drawable.character_surprised_0016,
    R.drawable.character_surprised_0017,
    R.drawable.character_surprised_0018,
    R.drawable.character_surprised_0019,
    R.drawable.character_surprised_0020,
    R.drawable.character_surprised_0021,
    R.drawable.character_surprised_0022,
    R.drawable.character_surprised_0023,
)

/**
 * Catalog of all character animation specifications.
 */
object CharacterFrameCatalog {
    val idle = CharacterAnimationSpec(
        actionName = "idle",
        frames = idleFrames,
        fps = 8,
        mode = PlaybackMode.LOOP,
    )

    val thinking = CharacterAnimationSpec(
        actionName = "thinking",
        frames = thinkingFrames,
        fps = 8,
        mode = PlaybackMode.LOOP,
    )

    val talk = CharacterAnimationSpec(
        actionName = "talk",
        frames = talkFrames,
        fps = 10,
        mode = PlaybackMode.LOOP,
    )

    val happy = CharacterAnimationSpec(
        actionName = "happy",
        frames = happyFrames,
        fps = 10,
        mode = PlaybackMode.ONE_SHOT,
    )

    val sad = CharacterAnimationSpec(
        actionName = "sad",
        frames = sadFrames,
        fps = 8,
        mode = PlaybackMode.ONE_SHOT,
    )

    val surprised = CharacterAnimationSpec(
        actionName = "surprised",
        frames = surprisedFrames,
        fps = 10,
        mode = PlaybackMode.ONE_SHOT,
    )

    val allSpecs = listOf(idle, thinking, talk, happy, sad, surprised)

    val totalFrameCount: Int = allSpecs.sumOf { it.frames.size }
}
