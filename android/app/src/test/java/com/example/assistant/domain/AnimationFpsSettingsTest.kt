package com.example.assistant.domain

import com.example.assistant.ui.character.CharacterAnimationSpec
import com.example.assistant.ui.character.CharacterFrameCatalog
import com.example.assistant.ui.character.PlaybackMode
import com.example.assistant.ui.character.frameIndexForElapsed
import com.example.assistant.ui.character.isAnimationFinished
import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertSame
import org.junit.Assert.assertTrue
import org.junit.Test

class AnimationFpsSettingsTest {

    // =========================================================================
    // 1. Default Values and Static Catalog Sync
    // =========================================================================

    @Test
    fun testDefaultValuesAreExact() {
        val defaults = AnimationFpsSettings.DEFAULT
        assertEquals("Default idle FPS must be 5", 5, defaults.idle)
        assertEquals("Default thinking FPS must be 8", 8, defaults.thinking)
        assertEquals("Default talk FPS must be 10", 10, defaults.talk)
        assertEquals("Default happy FPS must be 10", 10, defaults.happy)
        assertEquals("Default sad FPS must be 8", 8, defaults.sad)
        assertEquals("Default surprised FPS must be 10", 10, defaults.surprised)
    }

    @Test
    fun testStaticCatalogMatchesAnimationFpsSettingsDefaults() {
        assertEquals(AnimationFpsSettings.DEFAULT_IDLE_FPS, CharacterFrameCatalog.idle.fps)
        assertEquals(AnimationFpsSettings.DEFAULT_THINKING_FPS, CharacterFrameCatalog.thinking.fps)
        assertEquals(AnimationFpsSettings.DEFAULT_TALK_FPS, CharacterFrameCatalog.talk.fps)
        assertEquals(AnimationFpsSettings.DEFAULT_HAPPY_FPS, CharacterFrameCatalog.happy.fps)
        assertEquals(AnimationFpsSettings.DEFAULT_SAD_FPS, CharacterFrameCatalog.sad.fps)
        assertEquals(AnimationFpsSettings.DEFAULT_SURPRISED_FPS, CharacterFrameCatalog.surprised.fps)
    }

    // =========================================================================
    // 2. Bounds and Clamping Logic
    // =========================================================================

    @Test
    fun testMinAndMaxBounds() {
        assertEquals("Minimum allowed FPS must be 4", 4, AnimationFpsSettings.MIN_FPS)
        assertEquals("Maximum allowed FPS must be 20", 20, AnimationFpsSettings.MAX_FPS)
    }

    @Test
    fun testClampingBelowMinimum() {
        assertEquals(4, AnimationFpsSettings.clampFps(3))
        assertEquals(4, AnimationFpsSettings.clampFps(0))
        assertEquals(4, AnimationFpsSettings.clampFps(-10))
        assertEquals(4, AnimationFpsSettings.clampFps(Int.MIN_VALUE))
    }

    @Test
    fun testClampingAboveMaximum() {
        assertEquals(20, AnimationFpsSettings.clampFps(21))
        assertEquals(20, AnimationFpsSettings.clampFps(60))
        assertEquals(20, AnimationFpsSettings.clampFps(120))
        assertEquals(20, AnimationFpsSettings.clampFps(Int.MAX_VALUE))
    }

    @Test
    fun testValuesWithinRangeRemainUnchanged() {
        for (fps in 4..20) {
            assertEquals(fps, AnimationFpsSettings.clampFps(fps))
        }
    }

    // =========================================================================
    // 3. Action Name Lookup and Resolution
    // =========================================================================

    @Test
    fun testFpsForResolvesAllSixActions() {
        val custom = AnimationFpsSettings(
            idle = 6,
            thinking = 9,
            talk = 12,
            happy = 15,
            sad = 7,
            surprised = 18,
        )

        assertEquals(6, custom.fpsFor("idle"))
        assertEquals(9, custom.fpsFor("thinking"))
        assertEquals(12, custom.fpsFor("talk"))
        assertEquals(15, custom.fpsFor("happy"))
        assertEquals(7, custom.fpsFor("sad"))
        assertEquals(18, custom.fpsFor("surprised"))
    }

    @Test
    fun testFpsForUnknownActionReturnsClampedDefault() {
        val defaults = AnimationFpsSettings.DEFAULT
        assertEquals(5, defaults.fpsFor("unknown_action"))
    }

    // =========================================================================
    // 4. Immutable Updates and Isolation
    // =========================================================================

    @Test
    fun testIncreasingOneActionDoesNotChangeOthers() {
        val initial = AnimationFpsSettings.DEFAULT
        val updated = initial.withStep("idle", 1)

        assertEquals(6, updated.idle)
        assertEquals(initial.thinking, updated.thinking)
        assertEquals(initial.talk, updated.talk)
        assertEquals(initial.happy, updated.happy)
        assertEquals(initial.sad, updated.sad)
        assertEquals(initial.surprised, updated.surprised)
    }

    @Test
    fun testDecreasingOneActionDoesNotChangeOthers() {
        val initial = AnimationFpsSettings.DEFAULT
        val updated = initial.withStep("thinking", -1)

        assertEquals(initial.idle, updated.idle)
        assertEquals(7, updated.thinking)
        assertEquals(initial.talk, updated.talk)
        assertEquals(initial.happy, updated.happy)
        assertEquals(initial.sad, updated.sad)
        assertEquals(initial.surprised, updated.surprised)
    }

    @Test
    fun testWithFpsClampsBoundaryViolations() {
        val initial = AnimationFpsSettings.DEFAULT
        val clampedLow = initial.withFps("idle", 1)
        assertEquals(4, clampedLow.idle)

        val clampedHigh = initial.withFps("talk", 50)
        assertEquals(20, clampedHigh.talk)
    }

    @Test
    fun testResetReturnsAllSixDefaults() {
        val modified = AnimationFpsSettings(
            idle = 15,
            thinking = 18,
            talk = 6,
            happy = 4,
            sad = 20,
            surprised = 7,
        )

        // Reset produces AnimationFpsSettings.DEFAULT
        val reset = AnimationFpsSettings.DEFAULT
        assertEquals(5, reset.idle)
        assertEquals(8, reset.thinking)
        assertEquals(10, reset.talk)
        assertEquals(10, reset.happy)
        assertEquals(8, reset.sad)
        assertEquals(10, reset.surprised)
    }

    // =========================================================================
    // 5. Effective Spec Override and Runtime Playback Integration
    // =========================================================================

    @Test
    fun testApplyOverridePreservesFramesNameAndMode() {
        val baseSpec = CharacterFrameCatalog.happy
        val customSettings = AnimationFpsSettings.DEFAULT.withFps("happy", 15)

        val effectiveSpec = customSettings.applyOverride(baseSpec)

        assertEquals("happy", effectiveSpec.actionName)
        assertEquals(15, effectiveSpec.fps)
        assertEquals(PlaybackMode.ONE_SHOT, effectiveSpec.mode)
        assertArrayEquals(baseSpec.frames, effectiveSpec.frames)
    }

    @Test
    fun testApplyOverrideReturnsSameInstanceIfFpsMatches() {
        val baseSpec = CharacterFrameCatalog.idle // default 5 fps
        val defaultSettings = AnimationFpsSettings.DEFAULT

        val effectiveSpec = defaultSettings.applyOverride(baseSpec)
        assertSame("Should return same instance when FPS is identical", baseSpec, effectiveSpec)
    }

    @Test
    fun testOneShotDurationReflectsEffectiveFps() {
        val baseSpec = CharacterFrameCatalog.happy // 15 frames, default 10 FPS -> 1500ms
        assertEquals(100L, baseSpec.frameDurationMs)
        assertEquals(1500L, baseSpec.totalDurationMs)

        // Overridden to 5 FPS (frameDuration = 200ms) -> totalDuration = 15 * 200 = 3000ms
        val slowSettings = AnimationFpsSettings.DEFAULT.withFps("happy", 5)
        val slowSpec = slowSettings.applyOverride(baseSpec)

        assertEquals(5, slowSpec.fps)
        assertEquals(200L, slowSpec.frameDurationMs)
        assertEquals(3000L, slowSpec.totalDurationMs)

        // At 2000ms, default spec is finished but overridden slow spec is not
        assertTrue("Base spec finished at 2000ms", isAnimationFinished(2000L, baseSpec))
        assertFalse("Slow spec not finished at 2000ms", isAnimationFinished(2000L, slowSpec))

        // At 3000ms, slow spec is finished
        assertTrue("Slow spec finished at 3000ms", isAnimationFinished(3000L, slowSpec))

        // Frame index reflects the effective FPS
        assertEquals(10, frameIndexForElapsed(2000L, slowSpec)) // 2000ms / 200ms = 10
        assertEquals(14, frameIndexForElapsed(3000L, slowSpec)) // 14 (final frame)
    }

    @Test
    fun testCatalogSpecForAction() {
        assertEquals(CharacterFrameCatalog.idle, CharacterFrameCatalog.specForAction("idle"))
        assertEquals(CharacterFrameCatalog.thinking, CharacterFrameCatalog.specForAction("thinking"))
        assertEquals(CharacterFrameCatalog.talk, CharacterFrameCatalog.specForAction("talk"))
        assertEquals(CharacterFrameCatalog.happy, CharacterFrameCatalog.specForAction("happy"))
        assertEquals(CharacterFrameCatalog.sad, CharacterFrameCatalog.specForAction("sad"))
        assertEquals(CharacterFrameCatalog.surprised, CharacterFrameCatalog.specForAction("surprised"))
        assertEquals(CharacterFrameCatalog.idle, CharacterFrameCatalog.specForAction("unknown"))
    }
}
