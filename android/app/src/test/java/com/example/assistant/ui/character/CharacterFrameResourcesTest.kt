package com.example.assistant.ui.character

import com.example.assistant.R
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class CharacterFrameResourcesTest {

    @Test
    fun testActionResourceCounts() {
        assertEquals("Idle must have 32 frames", 32, idleFrames.size)
        assertEquals("Thinking must have 30 frames", 30, thinkingFrames.size)
        assertEquals("Talk must have 19 frames", 19, talkFrames.size)
        assertEquals("Happy must have 15 frames", 15, happyFrames.size)
        assertEquals("Sad must have 21 frames", 21, sadFrames.size)
        assertEquals("Surprised must have 23 frames", 23, surprisedFrames.size)

        assertEquals("Total frame count must be 140", 140, CharacterFrameCatalog.totalFrameCount)
    }

    @Test
    fun testAllArraysNonEmptyAndDistinct() {
        val allArrays = listOf(
            "idle" to idleFrames,
            "thinking" to thinkingFrames,
            "talk" to talkFrames,
            "happy" to happyFrames,
            "sad" to sadFrames,
            "surprised" to surprisedFrames,
        )

        for ((name, arr) in allArrays) {
            assertTrue("$name array must not be empty", arr.isNotEmpty())
            assertTrue("$name frame resource IDs must all be non-zero", arr.all { it != 0 })
            assertEquals("$name frames must have distinct resource IDs", arr.size, arr.distinct().size)
        }
    }

    @Test
    fun testPlaybackModes() {
        assertTrue("idle must loop", CharacterFrameCatalog.idle.isLooping)
        assertEquals(PlaybackMode.LOOP, CharacterFrameCatalog.idle.mode)

        assertTrue("thinking must loop", CharacterFrameCatalog.thinking.isLooping)
        assertEquals(PlaybackMode.LOOP, CharacterFrameCatalog.thinking.mode)

        assertTrue("talk must loop", CharacterFrameCatalog.talk.isLooping)
        assertEquals(PlaybackMode.LOOP, CharacterFrameCatalog.talk.mode)

        assertFalse("happy must be one-shot", CharacterFrameCatalog.happy.isLooping)
        assertEquals(PlaybackMode.ONE_SHOT, CharacterFrameCatalog.happy.mode)

        assertFalse("sad must be one-shot", CharacterFrameCatalog.sad.isLooping)
        assertEquals(PlaybackMode.ONE_SHOT, CharacterFrameCatalog.sad.mode)

        assertFalse("surprised must be one-shot", CharacterFrameCatalog.surprised.isLooping)
        assertEquals(PlaybackMode.ONE_SHOT, CharacterFrameCatalog.surprised.mode)
    }

    @Test
    fun testFpsAndDurationSpecifications() {
        assertEquals(5, CharacterFrameCatalog.idle.fps)
        assertEquals(200L, CharacterFrameCatalog.idle.frameDurationMs)

        assertEquals(8, CharacterFrameCatalog.thinking.fps)
        assertEquals(125L, CharacterFrameCatalog.thinking.frameDurationMs)

        assertEquals(10, CharacterFrameCatalog.talk.fps)
        assertEquals(100L, CharacterFrameCatalog.talk.frameDurationMs)

        assertEquals(10, CharacterFrameCatalog.happy.fps)
        assertEquals(100L, CharacterFrameCatalog.happy.frameDurationMs)

        assertEquals(8, CharacterFrameCatalog.sad.fps)
        assertEquals(125L, CharacterFrameCatalog.sad.frameDurationMs)

        assertEquals(10, CharacterFrameCatalog.surprised.fps)
        assertEquals(100L, CharacterFrameCatalog.surprised.frameDurationMs)
    }

    @Test
    fun testFrameOrderingBoundaryChecks() {
        // Idle boundary
        assertEquals(R.drawable.character_idle_0001, idleFrames[0])
        assertEquals(R.drawable.character_idle_0032, idleFrames[31])

        // Thinking boundary
        assertEquals(R.drawable.character_thinking_0001, thinkingFrames[0])
        assertEquals(R.drawable.character_thinking_0030, thinkingFrames[29])

        // Talk boundary
        assertEquals(R.drawable.character_talk_0001, talkFrames[0])
        assertEquals(R.drawable.character_talk_0019, talkFrames[18])

        // Happy boundary
        assertEquals(R.drawable.character_happy_0001, happyFrames[0])
        assertEquals(R.drawable.character_happy_0015, happyFrames[14])

        // Sad boundary
        assertEquals(R.drawable.character_sad_0001, sadFrames[0])
        assertEquals(R.drawable.character_sad_0021, sadFrames[20])

        // Surprised boundary
        assertEquals(R.drawable.character_surprised_0001, surprisedFrames[0])
        assertEquals(R.drawable.character_surprised_0023, surprisedFrames[22])
    }

    @Test
    fun testHappy0016IsNotReferenced() {
        // Collect all frames from all catalog specs
        val allCatalogFrames = CharacterFrameCatalog.allSpecs.flatMap { it.frames.toList() }.toSet()

        // Verify happyFrames contains exactly 15 items and ends on 0015
        assertEquals(15, happyFrames.size)
        assertEquals(R.drawable.character_happy_0015, happyFrames.last())

        // Verify total distinct count across entire catalog is exactly 140
        assertEquals(140, allCatalogFrames.size)
    }
}
