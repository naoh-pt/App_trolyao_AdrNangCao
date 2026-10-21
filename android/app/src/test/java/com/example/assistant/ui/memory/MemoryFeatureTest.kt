package com.example.assistant.ui.memory

import com.example.assistant.data.remote.*
import com.example.assistant.data.repo.MemoryGateway
import com.example.assistant.ui.chat.ChatUiState
import com.example.assistant.ui.demo.*
import com.google.gson.Gson
import kotlinx.coroutines.*
import kotlinx.coroutines.test.*
import org.junit.After
import org.junit.Before
import org.junit.Test
import org.junit.Assert.*

@OptIn(ExperimentalCoroutinesApi::class)
class MemoryFeatureTest {
    @Before fun prepare() { Dispatchers.setMain(StandardTestDispatcher()) }
    @After fun finish() { Dispatchers.resetMain() }

    private fun message(id: String = "message") = MessageDto(id, "assistant", "Anna nhắc nhẹ nè", "happy", "2026-10-21T04:00:00Z")
    private fun memory(id: String = "memory") = MemoryDto(id, "preference", "bạn thích học Android")

    private class FakeGateway : MemoryGateway {
        var items = listOf(MemoryDto("one", "profile", "bạn tên là Hoàn"), MemoryDto("two", "general", "một thông tin"))
        var failList = false
        var failDelete = false
        val deletions = mutableListOf<String>()
        override suspend fun listMemories(): Result<List<MemoryDto>> = if (failList) Result.failure(Exception("private content")) else Result.success(items)
        override suspend fun deleteMemory(id: String): Result<Unit> {
            if (failDelete) return Result.failure(Exception("private content"))
            deletions += id
            items = items.filterNot { it.id == id }
            return Result.success(Unit)
        }
    }

    @Test fun dtoParsesNullableDatesAndCheckIn() {
        val gson = Gson()
        val dto = gson.fromJson("""{"id":"m","kind":"event","content":"thi Android","event_date":"2026-10-30","remind_on":"2026-10-21","reminded_at":null} """, MemoryDto::class.java)
        assertEquals("2026-10-30", dto.eventDate)
        assertEquals("2026-10-21", dto.remindOn)
        assertNull(dto.remindedAt)
        assertNull(gson.fromJson("""{"message":null}""", CheckInResponse::class.java).message)
        val response = gson.fromJson("""{"message":{"id":"a","role":"assistant","text":"nhắc","emotion":"happy","created_at":"2026-10-21T04:00:00Z"}}""", CheckInResponse::class.java)
        assertEquals("a", response.message!!.id)
    }

    @Test fun settingsLoadingThenList() = runTest {
        val vm = MemoryViewModel(FakeGateway())
        assertTrue(vm.ui.value.loading)
        advanceUntilIdle()
        assertEquals(2, vm.ui.value.items.size)
        assertFalse(vm.ui.value.loading)
    }
    @Test fun settingsEmpty() = runTest {
        val gateway = FakeGateway().apply { items = emptyList() }
        val vm = MemoryViewModel(gateway)
        advanceUntilIdle()
        assertTrue(vm.ui.value.items.isEmpty())
        assertNull(vm.ui.value.error)
    }
    @Test fun settingsErrorAndRetryDoesNotExposeContent() = runTest {
        val gateway = FakeGateway().apply { failList = true }
        val vm = MemoryViewModel(gateway)
        advanceUntilIdle()
        assertNotNull(vm.ui.value.error)
        assertFalse(vm.ui.value.error!!.contains("private content"))
        gateway.failList = false
        vm.refresh()
        advanceUntilIdle()
        assertEquals(2, vm.ui.value.items.size)
        assertNull(vm.ui.value.error)
    }
    @Test fun deleteOneRefreshes() = runTest {
        val gateway = FakeGateway()
        val vm = MemoryViewModel(gateway)
        advanceUntilIdle()
        vm.delete("one")
        advanceUntilIdle()
        assertEquals(listOf("two"), vm.ui.value.items.map { it.id })
        assertEquals(listOf("one"), gateway.deletions)
    }
    @Test fun clearAllRequiresConfirmationAndCancelPreserves() = runTest {
        val gateway = FakeGateway()
        val vm = MemoryViewModel(gateway)
        advanceUntilIdle()
        vm.confirmClear()
        advanceUntilIdle()
        assertTrue(gateway.deletions.isEmpty())
        vm.requestClear()
        assertTrue(vm.ui.value.confirmClear)
        vm.cancelClear()
        vm.confirmClear()
        advanceUntilIdle()
        assertEquals(2, vm.ui.value.items.size)
    }
    @Test fun confirmedClearDeletesSnapshotAndRefreshes() = runTest {
        val gateway = FakeGateway()
        val vm = MemoryViewModel(gateway)
        advanceUntilIdle()
        vm.requestClear()
        vm.confirmClear()
        vm.confirmClear()
        advanceUntilIdle()
        assertEquals(listOf("one", "two"), gateway.deletions)
        assertTrue(vm.ui.value.items.isEmpty())
        assertFalse(vm.ui.value.confirmClear)
    }
    @Test fun failedDeleteReportsFriendlyError() = runTest {
        val vm = MemoryViewModel(FakeGateway().apply { failDelete = true })
        advanceUntilIdle()
        vm.delete("one")
        advanceUntilIdle()
        assertEquals(2, vm.ui.value.items.size)
        assertNotNull(vm.ui.value.error)
        assertFalse(vm.ui.value.loading)
    }

    @Test fun entryOnceAcrossRepeatedComposeOrRotationSignals() = runTest {
        var calls = 0
        val cached = mutableListOf<String>()
        val controller = ConversationEntryCheckIn(this, { calls++; Result.success(message()) }, { _, msg -> cached += msg.id })
        repeat(10) { controller.enter("conversation") }
        advanceUntilIdle()
        controller.enter("conversation")
        advanceUntilIdle()
        assertEquals(1, calls)
        assertEquals(listOf("message"), cached)
    }
    @Test fun noConversationNoRequest() = runTest {
        var calls = 0
        val controller = ConversationEntryCheckIn(this, { calls++; Result.success(null) }, { _, _ -> fail("No message") })
        controller.enter(null)
        advanceUntilIdle()
        assertEquals(0, calls)
    }
    @Test fun emptyAndFailedCheckInsDoNotChangeChat() = runTest {
        val initial = ChatUiState(input = "bản nháp", speechActive = true, playbackToken = "existing")
        for (response in listOf(Result.success(null), Result.failure(Exception("offline")))) {
            val controller = ConversationEntryCheckIn(this, { response }, { _, _ -> fail("No message") })
            controller.enter("conversation")
            advanceUntilIdle()
            assertEquals("bản nháp", initial.input)
            assertTrue(initial.speechActive)
        }
    }
    @Test fun switchingCancelsAndRejectsOldResponse() = runTest {
        val cached = mutableListOf<String>()
        val controller = ConversationEntryCheckIn(this, { id ->
            if (id == "old") withContext(NonCancellable) { delay(100) }
            Result.success(message(id))
        }, { id, msg -> cached += "$id:${msg.id}" })
        controller.enter("old")
        runCurrent()
        controller.enter("new")
        advanceUntilIdle()
        assertEquals(listOf("new:new"), cached)
    }
    @Test fun leavingCancelsCheckIn() = runTest {
        val controller = ConversationEntryCheckIn(this, { delay(100); Result.success(message()) }, { _, _ -> fail("Disposed") })
        controller.enter("conversation")
        runCurrent()
        controller.leave()
        advanceUntilIdle()
    }
    @Test fun sameMessageCannotBeCachedTwiceAcrossEntries() = runTest {
        var caches = 0
        val controller = ConversationEntryCheckIn(this, { Result.success(message()) }, { _, _ -> caches++ })
        controller.enter("first")
        advanceUntilIdle()
        controller.enter("second")
        advanceUntilIdle()
        assertEquals(1, caches)
    }
    @Test fun checkInIsHistoryOnlyAndCannotForceSpeechOrReveal() = runTest {
        val initial = ChatUiState()
        var cached = 0
        val controller = ConversationEntryCheckIn(this, { Result.success(message()) }, { _, _ -> cached++ })
        controller.enter("conversation")
        advanceUntilIdle()
        assertEquals(1, cached)
        assertFalse(initial.speechActive)
        assertNull(initial.reveal)
        assertNull(initial.playbackToken)
    }
    @Test fun checkInCacheFailureDoesNotCrashOrBlock() = runTest {
        val controller = ConversationEntryCheckIn(this, { Result.success(message()) }, { _, _ -> throw Exception("cache unavailable") })
        controller.enter("conversation")
        advanceUntilIdle()
    }
    @Test fun memoryPromptsFlagsIdsAndDraftOnlySelection() {
        val prompts = listOf("Anna hãy nhớ: mình tên là Hoàn.", "Anna hãy nhớ: mình thích học Android.", "Anna nhớ gì về mình?",
            "Anna hãy nhớ: mình thi Android vào thứ Sáu tuần sau. Nhắc mình khi mở ứng dụng từ hôm nay.", "Anna hãy quên việc mình thích học Android.")
        val questions = DemoQuestionCatalog.questions.filter { it.category == DemoCategory.Memory }
        assertEquals(prompts, questions.map { it.prompt })
        assertEquals(5, questions.map { it.id }.toSet().size)
        assertTrue(questions.all { it.enabled && it.requiresBackend && !it.requiresAi && !it.requiresRag && !it.requiresInternet })
        questions.forEach { question ->
            val state = ChatUiState().reduceDemo(DemoCommand.Pick(question.id))
            assertEquals(question.prompt, state.input)
            assertEquals(ChatUiState(), state.copy(input = "", demo = DemoState()))
        }
        assertEquals(listOf("memory_name", "memory_list"), DemoQuestionCatalog.scenario("full")!!.questionIds.drop(9).take(2))
        for (id in listOf("quick", "no_quota")) {
            assertTrue(DemoQuestionCatalog.scenario(id)!!.questionIds.none { it.startsWith("memory_") })
        }
    }
}
