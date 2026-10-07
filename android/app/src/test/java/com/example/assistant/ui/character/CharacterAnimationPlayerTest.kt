package com.example.assistant.ui.character

import com.example.assistant.domain.CharacterState
import com.example.assistant.domain.Emotion
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class CharacterAnimationPlayerTest {

    // =========================================================================
    // 1. Mapping Tests
    // =========================================================================

    @Test
    fun testAnimationSpecForIdleWithAnyEmotion() {
        for (emotion in Emotion.values()) {
            val spec = animationSpecFor(CharacterState.IDLE, emotion)
            assertEquals(
                "IDLE with emotion $emotion must resolve to idle",
                CharacterFrameCatalog.idle,
                spec,
            )
        }
    }

    @Test
    fun testAnimationSpecForThinkingWithAnyEmotion() {
        for (emotion in Emotion.values()) {
            val spec = animationSpecFor(CharacterState.THINKING, emotion)
            assertEquals(
                "THINKING with emotion $emotion must resolve to thinking",
                CharacterFrameCatalog.thinking,
                spec,
            )
        }
    }

    @Test
    fun testAnimationSpecForTalkingWithEmotions() {
        assertEquals(
            "TALKING + NEUTRAL must resolve to talk",
            CharacterFrameCatalog.talk,
            animationSpecFor(CharacterState.TALKING, Emotion.NEUTRAL),
        )
        assertEquals(
            "TALKING + HAPPY must resolve to happy",
            CharacterFrameCatalog.happy,
            animationSpecFor(CharacterState.TALKING, Emotion.HAPPY),
        )
        assertEquals(
            "TALKING + SAD must resolve to sad",
            CharacterFrameCatalog.sad,
            animationSpecFor(CharacterState.TALKING, Emotion.SAD),
        )
        assertEquals(
            "TALKING + SURPRISED must resolve to surprised",
            CharacterFrameCatalog.surprised,
            animationSpecFor(CharacterState.TALKING, Emotion.SURPRISED),
        )
    }

    // =========================================================================
    // 2. Frame-Index Calculation Tests
    // =========================================================================

    @Test
    fun testFrameIndexZeroAtElapsedZeroAndNegative() {
        for (spec in CharacterFrameCatalog.allSpecs) {
            assertEquals("Index must be 0 at elapsed 0", 0, frameIndexForElapsed(0L, spec))
            assertEquals("Index must be 0 at elapsed -1", 0, frameIndexForElapsed(-1L, spec))
            assertEquals("Index must be 0 at elapsed -1000", 0, frameIndexForElapsed(-1000L, spec))
        }
    }

    @Test
    fun testFrameIndexBoundaryTransitions() {
        val spec = CharacterFrameCatalog.idle // fps=8, frameDuration=125ms
        val duration = spec.frameDurationMs

        assertEquals(0, frameIndexForElapsed(0L, spec))
        assertEquals(0, frameIndexForElapsed(duration - 1L, spec))
        assertEquals(1, frameIndexForElapsed(duration, spec))
        assertEquals(1, frameIndexForElapsed(2 * duration - 1L, spec))
        assertEquals(2, frameIndexForElapsed(2 * duration, spec))
    }

    @Test
    fun testLoopingWrapsToZeroAndRemainsInBounds() {
        val loopSpecs = listOf(
            CharacterFrameCatalog.idle,
            CharacterFrameCatalog.thinking,
            CharacterFrameCatalog.talk,
        )

        for (spec in loopSpecs) {
            val totalCycleMs = spec.frames.size * spec.frameDurationMs

            // Exact cycle completion wraps to index 0
            assertEquals(
                "${spec.actionName} must wrap to 0 at cycle completion",
                0,
                frameIndexForElapsed(totalCycleMs, spec),
            )
            assertEquals(
                "${spec.actionName} must wrap to 0 at 3 cycles",
                0,
                frameIndexForElapsed(totalCycleMs * 3, spec),
            )

            // Step through multiple cycles and ensure no index falls out of bounds
            for (step in 0..200) {
                val elapsed = step * 31L
                val idx = frameIndexForElapsed(elapsed, spec)
                assertTrue(
                    "Index $idx out of bounds for ${spec.actionName} (size: ${spec.frames.size})",
                    idx in spec.frames.indices,
                )
            }
        }
    }

    @Test
    fun testOneShotReachesFinalIndexAndStaysThere() {
        val oneShotSpecs = listOf(
            CharacterFrameCatalog.happy,
            CharacterFrameCatalog.sad,
            CharacterFrameCatalog.surprised,
        )

        for (spec in oneShotSpecs) {
            val lastIdx = spec.frames.size - 1
            val totalDuration = spec.totalDurationMs

            // At total duration, must be on last index
            assertEquals(
                "${spec.actionName} must reach last index at total duration",
                lastIdx,
                frameIndexForElapsed(totalDuration, spec),
            )

            // Far past duration, must clamp to last index
            assertEquals(
                "${spec.actionName} must remain on last index after completion",
                lastIdx,
                frameIndexForElapsed(totalDuration + 5000L, spec),
            )
            assertEquals(
                "${spec.actionName} must remain on last index on very large elapsed",
                lastIdx,
                frameIndexForElapsed(1_000_000_000L, spec),
            )
        }
    }

    @Test
    fun testEmptyFramesSafeContract() {
        val emptyLoopSpec = CharacterAnimationSpec(
            actionName = "empty_loop",
            frames = intArrayOf(),
            fps = 16,
            mode = PlaybackMode.LOOP,
        )
        val emptyOneShotSpec = CharacterAnimationSpec(
            actionName = "empty_oneshot",
            frames = intArrayOf(),
            fps = 16,
            mode = PlaybackMode.ONE_SHOT,
        )

        assertEquals(0, frameIndexForElapsed(0L, emptyLoopSpec))
        assertEquals(0, frameIndexForElapsed(500L, emptyLoopSpec))
        assertEquals(0, frameIndexForElapsed(0L, emptyOneShotSpec))
        assertEquals(0, frameIndexForElapsed(500L, emptyOneShotSpec))
        assertFalse(isAnimationFinished(500L, emptyLoopSpec))
        assertFalse(isAnimationFinished(500L, emptyOneShotSpec))
    }

    // =========================================================================
    // 3. Completion Contract Tests
    // =========================================================================

    @Test
    fun testLoopingNeverCompletes() {
        val loopSpecs = listOf(
            CharacterFrameCatalog.idle,
            CharacterFrameCatalog.thinking,
            CharacterFrameCatalog.talk,
        )

        for (spec in loopSpecs) {
            assertFalse(isAnimationFinished(0L, spec))
            assertFalse(isAnimationFinished(spec.totalDurationMs - 1L, spec))
            assertFalse(isAnimationFinished(spec.totalDurationMs, spec))
            assertFalse(isAnimationFinished(spec.totalDurationMs * 10, spec))
        }
    }

    @Test
    fun testOneShotCompletionTiming() {
        val oneShotSpecs = listOf(
            CharacterFrameCatalog.happy,
            CharacterFrameCatalog.sad,
            CharacterFrameCatalog.surprised,
        )

        for (spec in oneShotSpecs) {
            assertFalse(
                "${spec.actionName} must not complete at elapsed 0",
                isAnimationFinished(0L, spec),
            )
            assertFalse(
                "${spec.actionName} must not complete at negative elapsed",
                isAnimationFinished(-500L, spec),
            )
            assertFalse(
                "${spec.actionName} must not complete before total duration",
                isAnimationFinished(spec.totalDurationMs - 1L, spec),
            )
            assertTrue(
                "${spec.actionName} must complete exactly at total duration",
                isAnimationFinished(spec.totalDurationMs, spec),
            )
            assertTrue(
                "${spec.actionName} must remain complete after total duration",
                isAnimationFinished(spec.totalDurationMs + 1000L, spec),
            )
        }
    }
}
