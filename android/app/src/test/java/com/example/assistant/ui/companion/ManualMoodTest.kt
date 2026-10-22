package com.example.assistant.ui.companion

import androidx.datastore.preferences.core.mutablePreferencesOf
import com.example.assistant.data.local.MoodShownPreference
import com.example.assistant.ui.chat.ChatUiState
import com.example.assistant.domain.CharacterState
import org.junit.Assert.*
import org.junit.Test

class ManualMoodTest {
    private fun ready() = ChatUiState(online = true, input = "Bản nháp của mình")

    @Test fun opensAfterDailyCardConsumedAndDismissalSendsNothing() {
        val prefs = mutablePreferencesOf()
        assertTrue(MoodShownPreference.claim(prefs, "owner", "2026-10-22"))
        val original = ready().copy(companion = CompanionChatState(moodVisible = false, entryEngaged = true))
        val opened = original.openManualMood()
        assertTrue(opened.companion.manualMoodVisible)
        assertEquals(original.input, opened.input)
        assertFalse(opened.sending)
        assertEquals(CharacterState.IDLE, opened.characterState)
        assertNull(opened.reveal)
        assertFalse(opened.speechActive)
        assertEquals(original, opened.dismissManualMood())
        assertFalse(MoodShownPreference.claim(prefs, "owner", "2026-10-22"))
        assertTrue(opened.dismissManualMood().openManualMood().companion.manualMoodVisible)
    }

    @Test fun exactMappingsSharedAndDoubleTapRejected() {
        val exact = listOf("Hôm nay mình cảm thấy rất vui.", "Hôm nay mình cảm thấy khá ổn.",
            "Hôm nay mình cảm thấy bình thường.", "Hôm nay mình cảm thấy hơi buồn.",
            "Hôm nay mình đang cảm thấy căng thẳng.")
        MoodChoice.entries.forEachIndexed { index, choice ->
            val opened = ready().openManualMood()
            val selected = opened.selectCompanion(choice, null)!!
            assertEquals(exact[index], selected.second)
            assertFalse(selected.first.manualMoodVisible)
            assertTrue(selected.first.selectionBusy)
            assertNull(opened.copy(companion = selected.first).selectCompanion(choice, null))
            assertEquals("Bản nháp của mình", opened.input)
            // The pure selection produces one normal-send command, no message or side effect.
            assertFalse(opened.sending)
            assertNull(opened.pending)
        }
    }

    @Test fun busyAndOfflineCannotOpenOrSelect() {
        val states = listOf(ready().copy(online = false), ready().copy(sending = true),
            ready().copy(pending = "Retry"), ready().copy(companion = CompanionChatState(selectionBusy = true)))
        states.forEach {
            assertEquals(it, it.openManualMood())
            assertNull(it.copy(companion = it.companion.copy(manualMoodVisible = true)).selectCompanion(MoodChoice.JOY, null))
        }
    }

    @Test fun stateRecreationDoesNotOpenOrSendAgainAndNewChatWorks() {
        val opened = ready().openManualMood()
        assertEquals(opened, opened.copy().openManualMood())
        assertNotNull(opened.selectCompanion(MoodChoice.NORMAL, null))
        assertEquals(opened.companion, opened.copy().companion)
        assertFalse(opened.companion.userTurn().manualMoodVisible)
        assertFalse(ready().companion.manualMoodVisible)
    }

    @Test fun automaticEligibilityMemoryPriorityAndDateMarkerUnchanged() {
        val prefs = mutablePreferencesOf()
        ready().openManualMood().dismissManualMood()
        assertTrue(MoodShownPreference.claim(prefs, "one", "2026-10-22"))
        ready().openManualMood().selectCompanion(MoodChoice.SAD, null)
        assertFalse(MoodShownPreference.claim(prefs, "one", "2026-10-22"))
        assertTrue(MoodShownPreference.claim(prefs, "one", "2026-10-23"))
        assertTrue(MoodShownPreference.claim(prefs, "two", "2026-10-22"))
        assertFalse(moodEligible(true, true, true, false))
        assertFalse(moodEligible(false, true, false, false))
        assertFalse(moodEligible(true, false, false, false))
        assertFalse(moodEligible(true, true, false, true))
        assertTrue(moodEligible(true, true, false, false))
    }
}
