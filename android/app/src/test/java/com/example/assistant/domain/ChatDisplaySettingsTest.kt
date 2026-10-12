package com.example.assistant.domain

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class ChatDisplaySettingsTest {

    @Test
    fun testDefaultsAndLineHeightCalculation() {
        val defaultSettings = ChatDisplaySettings.DEFAULT
        assertEquals(14, defaultSettings.fontSizeSp)
        assertEquals(18, defaultSettings.lineHeightSp)
        assertEquals(16, ChatDisplaySettings.calculateLineHeight(12))
        assertEquals(24, ChatDisplaySettings.calculateLineHeight(20))
    }

    @Test
    fun testClampingLowerAndUpperBounds() {
        val belowMin = ChatDisplaySettings.DEFAULT.withFontSize(8)
        assertEquals(12, belowMin.fontSizeSp)
        assertEquals(16, belowMin.lineHeightSp)

        val aboveMax = ChatDisplaySettings.DEFAULT.withFontSize(25)
        assertEquals(20, aboveMax.fontSizeSp)
        assertEquals(24, aboveMax.lineHeightSp)
    }

    @Test
    fun testStepBehaviorAndBoundaries() {
        val steppedUp = ChatDisplaySettings.DEFAULT.withStep(1)
        assertEquals(15, steppedUp.fontSizeSp)
        assertEquals(19, steppedUp.lineHeightSp)

        val steppedDown = ChatDisplaySettings.DEFAULT.withStep(-1)
        assertEquals(13, steppedDown.fontSizeSp)
        assertEquals(17, steppedDown.lineHeightSp)

        val atMin = ChatDisplaySettings(fontSizeSp = 12)
        assertFalse(atMin.canDecrease())
        assertTrue(atMin.canIncrease())
        assertEquals(12, atMin.withStep(-1).fontSizeSp)

        val atMax = ChatDisplaySettings(fontSizeSp = 20)
        assertTrue(atMax.canDecrease())
        assertFalse(atMax.canIncrease())
        assertEquals(20, atMax.withStep(1).fontSizeSp)
    }

    @Test
    fun testResetDefaults() {
        val custom = ChatDisplaySettings(fontSizeSp = 19)
        val reset = custom.resetDefaults()
        assertEquals(14, reset.fontSizeSp)
        assertEquals(18, reset.lineHeightSp)
    }

    @Test
    fun testFontSizeChangeDoesNotAffectSpeechSettings() {
        val custom = ChatDisplaySettings(fontSizeSp = 18)
        assertEquals(18, custom.fontSizeSp)

        // SpeechSettings.DEFAULT is completely untouched
        assertTrue(SpeechSettings.DEFAULT.enabled)
        assertEquals(1.0f, SpeechSettings.DEFAULT.speechRate, 0.001f)
        assertEquals(1.0f, SpeechSettings.DEFAULT.pitch, 0.001f)

        // AnimationFpsSettings.DEFAULT is untouched
        assertEquals(5, AnimationFpsSettings.DEFAULT.idle)
    }
}
