package com.example.assistant.domain

import androidx.datastore.preferences.core.PreferenceDataStoreFactory
import androidx.datastore.preferences.core.booleanPreferencesKey
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.emptyPreferences
import androidx.datastore.preferences.core.intPreferencesKey
import com.example.assistant.data.local.TypewriterPreference
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancelAndJoin
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.runBlocking
import org.junit.Assert.*
import org.junit.Rule
import org.junit.Test
import org.junit.rules.TemporaryFolder

class TypewriterSettingsTest {
    @get:Rule val temporaryFolder = TemporaryFolder()

    @Test fun defaultAndLegacyMissingKeyAreEnabled() {
        assertTrue(ChatDisplaySettings.DEFAULT.typewriterEnabled)
        assertTrue(TypewriterPreference.read(emptyPreferences()))
    }

    @Test fun persistedToggleSurvivesDatastoreRecreationAndPreservesOtherSettings() = runBlocking {
        val file = temporaryFolder.newFolder().resolve("settings.preferences_pb")
        val font = intPreferencesKey("message_font_size_sp")
        val fps = intPreferencesKey("fps_talk")
        val tts = booleanPreferencesKey("tts_enabled")
        val job = SupervisorJob()
        val store = PreferenceDataStoreFactory.create(scope = CoroutineScope(Dispatchers.IO + job)) { file }
        store.edit { prefs ->
            prefs[font] = 19
            prefs[fps] = 15
            prefs[tts] = false
            TypewriterPreference.write(prefs, false)
        }
        assertFalse(TypewriterPreference.read(store.data.first()))
        job.cancelAndJoin()
        val nextJob = SupervisorJob()
        try {
            val restored = PreferenceDataStoreFactory.create(scope = CoroutineScope(Dispatchers.IO + nextJob)) { file }
            val prefs = restored.data.first()
            assertFalse(TypewriterPreference.read(prefs))
            assertEquals(19, prefs[font])
            assertEquals(15, prefs[fps])
            assertEquals(false, prefs[tts])
            restored.edit { TypewriterPreference.write(it, true) }
            assertTrue(TypewriterPreference.read(restored.data.first()))
        } finally { nextJob.cancelAndJoin() }
    }

    @Test fun fontControlsPreserveTypewriterToggle() {
        val display = ChatDisplaySettings(fontSizeSp = 18, typewriterEnabled = false)
        assertFalse(display.withStep(1).typewriterEnabled)
        assertFalse(display.resetDefaults().typewriterEnabled)
        assertEquals(18, display.copy(typewriterEnabled = true).fontSizeSp)
    }
}
