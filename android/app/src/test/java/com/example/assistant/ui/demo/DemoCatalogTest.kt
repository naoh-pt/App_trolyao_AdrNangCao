package com.example.assistant.ui.demo

import org.junit.Assert.*
import org.junit.Test

class DemoCatalogTest {
    private val questions = DemoQuestionCatalog.questions
    private val scenarios = DemoQuestionCatalog.scenarios

    @Test fun questionIdsUnique() = assertEquals(questions.size, questions.map { it.id }.toSet().size)
    @Test fun scenarioIdsUnique() = assertEquals(scenarios.size, scenarios.map { it.id }.toSet().size)
    @Test fun referencesExistAndAreEnabled() {
        scenarios.flatMap { it.questionIds }.forEach { id ->
            val question = DemoQuestionCatalog.question(id)
            assertNotNull(id, question)
            assertTrue(question!!.enabled && question.category.enabled)
        }
    }
    @Test fun orderIsStable() {
        assertEquals(listOf("chat_greeting", "time_now", "utility_timer", "utility_map_kma"), scenarios[0].questionIds)
        assertEquals(listOf("chat_greeting", "chat_help", "time_now", "study_tuition", "emotion_sad", "utility_timer", "utility_calendar", "utility_map_kma", "weather_now", "memory_name", "memory_list", "emotion_disappointed"), scenarios[1].questionIds)
        assertEquals(listOf("chat_greeting", "time_now", "time_weekday", "utility_timer", "utility_calendar", "utility_map_lake"), scenarios[2].questionIds)
    }
    @Test fun weatherEnabledWithoutAiOrRag() {
        val weather = questions.filter { it.category == DemoCategory.Weather }
        assertEquals(4, weather.size)
        assertTrue(weather.all { it.enabled && it.requiresBackend && it.requiresInternet && !it.requiresAi && !it.requiresRag })
        assertTrue(DemoCategory.Weather.enabled)
    }
    @Test fun quotaFreeStillNeedsBackend() {
        val local = scenarios.single { it.id == "no_quota" }.questionIds.map { DemoQuestionCatalog.question(it)!! }
        assertTrue(local.all { !it.requiresAi && !it.requiresRag && it.requiresBackend })
        assertTrue(local.none { it.category == DemoCategory.Weather })
        assertEquals("Không cần quota AI; backend vẫn phải chạy", scenarios.last().description)
    }
    @Test fun tuitionNeedsRag() = assertTrue(DemoQuestionCatalog.question("study_tuition")!!.requiresRag)
    @Test fun originalCategoriesAndQuestionsRemain() {
        assertEquals(7, DemoCategory.entries.size)
        assertEquals(listOf(4, 4, 4, 6, 5, 4, 5), DemoCategory.entries.map { category -> questions.count { it.category == category } })
        assertEquals("weather_now", scenarios.single { it.id == "full" }.questionIds[8])
    }
    @Test fun enabledEntriesHaveText() = assertTrue(questions.filter { it.enabled }.all { it.title.isNotBlank() && it.prompt.isNotBlank() })
    @Test fun unicodeAndPunctuationPreserved() {
        assertEquals("Tìm trên bản đồ Hồ Gươm.", DemoQuestionCatalog.question("utility_map_lake")!!.prompt)
        assertEquals("Hôm nay mình hơi buồn và mất động lực học.", DemoQuestionCatalog.question("emotion_sad")!!.prompt)
        assertEquals("Tạo lịch họp nhóm lúc 7 giờ tối thứ 2 tuần sau", DemoQuestionCatalog.question("utility_weekday")!!.prompt)
        assertEquals(32, questions.size)
        assertFalse(questions.any { '\uFFFD' in it.prompt || "http" in it.prompt })
    }
}
