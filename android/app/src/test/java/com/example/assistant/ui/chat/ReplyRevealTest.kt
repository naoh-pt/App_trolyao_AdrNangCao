package com.example.assistant.ui.chat

import com.example.assistant.data.local.MessageEntity
import org.junit.Assert.*
import org.junit.Test

class ReplyRevealTest {
    private fun reveal(text: String, enabled: Boolean = true) =
        ReplyReveal("new", "generation", text, ReplyRevealPlanner.plan(text, enabled))

    @Test fun emptyReplyIsAlreadyComplete() {
        val reply = reveal("")
        assertTrue(reply.complete)
        assertEquals("", reply.visibleText)
        assertEquals(0L, reply.plan.durationMs)
    }

    @Test fun oneCharacterHasPerceptibleDelay() {
        val reply = reveal("a")
        assertEquals("", reply.visibleText)
        assertEquals(300L, reply.plan.durationMs)
        assertEquals("a", reply.advance().visibleText)
    }

    @Test fun shortReplyTakesBetweenPointThreeAndOneSecond() {
        assertTrue(reveal("Xin chào bạn!").plan.durationMs in 300L..1000L)
    }

    @Test fun mediumReplyTakesOneToThreeSeconds() {
        assertTrue(reveal("a".repeat(100)).plan.durationMs in 1000L..3000L)
    }

    @Test fun longReplyBatchesClustersAndCapsDuration() {
        val text = "a".repeat(10000)
        val plan = ReplyRevealPlanner.plan(text)
        assertEquals(4500L, plan.durationMs)
        assertEquals(text.length, plan.endpoints.last())
        assertTrue(plan.endpoints.first() > 1)
        assertTrue(plan.endpoints.zipWithNext().all { (a, b) -> b > a })
    }

    @Test fun vietnameseRemainsUnchanged() {
        val text = "Tiếng Việt: Chào bạn, hôm nay thứ Tư nhé!"
        val reply = reveal(text)
        assertEquals(text, reply.skip().visibleText)
        assertEquals(text, reply.fullText)
    }

    @Test fun combiningCharactersAreNeverSplit() {
        val text = "a\u0301\u0323e\u0302\u0301"
        assertEquals(listOf(3, 6), ReplyRevealPlanner.plan(text).endpoints)
    }

    @Test fun surrogatePairsAreNeverSplit() {
        val text = "😀😊🚀"
        assertEquals(listOf(2, 4, 6), ReplyRevealPlanner.plan(text).endpoints)
    }

    @Test fun joinedEmojiSkinTonesAndFlagsStayWhole() {
        for (text in listOf("👩‍💻", "👨‍👩‍👧‍👦", "👍🏽", "🇻🇳", "1️⃣")) {
            assertEquals(text, listOf(text.length), ReplyRevealPlanner.plan(text).endpoints)
        }
    }

    @Test fun disabledPlannerHasNoDelay() {
        val plan = ReplyRevealPlanner.plan("Xin chào 😀", false)
        assertEquals(0L, plan.durationMs)
        assertEquals(listOf("Xin chào 😀".length), plan.endpoints)
    }

    @Test fun skipIsImmediateAndIdempotent() {
        val reply = reveal("Một câu trả lời dài hơn.")
        assertTrue(reply.skip().complete)
        assertEquals(reply.fullText, reply.skip().visibleText)
        assertEquals(reply.skip(), reply.skip().skip())
        assertEquals(reply.skip(), reply.skip().advance())
    }

    @Test fun historyAndUserMessagesAreImmediatelyVisible() {
        assertEquals("Lịch sử", visibleReplyText("history", "Lịch sử", reveal("Mới")))
        assertEquals("Câu hỏi", visibleReplyText("user", "Câu hỏi", null))
    }

    @Test fun onlyNewResponseStartsHidden() {
        assertEquals("", visibleReplyText("new", "Mới", reveal("Mới")))
    }

    @Test fun repeatedRenderingDoesNotRestartCompletedReveal() {
        val finished = reveal("Xin chào").skip()
        repeat(10) { assertEquals("Xin chào", visibleReplyText("new", "Xin chào", finished)) }
    }

    @Test fun cancellationShowsFullTextWithoutChangingMessage() {
        val message = MessageEntity("new", "conversation", "assistant", "Nội dung đầy đủ 😀", "happy", 1L)
        val snapshot = message.copy()
        assertEquals("", visibleReplyText(message.id, message.text, reveal(message.text)))
        assertEquals(message.text, visibleReplyText(message.id, message.text, null))
        assertEquals(snapshot, message)
    }

    @Test fun historicalIdempotentReplayDoesNotCreateReveal() {
        val controller = ReplyRevealController()
        controller.startRequest(listOf("stored"))
        assertFalse(controller.receive("stored", "retry", "Đã lưu", true, true))
        assertNull(controller.current)
    }

    @Test fun duplicateResponseDoesNotRestartProgress() {
        val controller = ReplyRevealController()
        controller.receive("new", "first", "Xin chào", true, true)
        controller.advance("first")
        val snapshot = controller.current
        assertFalse(controller.receive("new", "duplicate", "Xin chào", true, true))
        assertEquals(snapshot, controller.current)
        controller.skip("new")
        assertFalse(controller.receive("new", "again", "Xin chào", true, true))
        assertTrue(controller.current!!.complete)
    }

    @Test fun newRequestCancelsOldRevealAndRejectsOldTicks() {
        val controller = ReplyRevealController()
        controller.receive("old", "old-token", "Cũ", true, true)
        controller.startRequest(listOf("old"))
        assertNull(controller.current)
        controller.receive("new", "new-token", "Mới", true, true)
        assertNull(controller.advance("old-token"))
        assertEquals("", controller.current!!.visibleText)
    }

    @Test fun switchingConversationAndDisposalCancelWithoutReplayOnReturn() {
        val controller = ReplyRevealController()
        controller.receive("old", "token", "Nội dung", true, true)
        controller.cancel()
        assertNull(controller.advance("token"))
        assertFalse(controller.receive("old", "return", "Nội dung", true, true))
        assertNull(controller.current)
    }

    @Test fun responsesReceivedOffScreenOrWithSettingDisabledShowImmediately() {
        val controller = ReplyRevealController()
        assertTrue(controller.receive("offscreen", "a", "Đầy đủ", true, false))
        assertNull(controller.current)
        assertFalse(controller.receive("offscreen", "b", "Đầy đủ", true, true))
        assertTrue(controller.receive("disabled", "c", "Đầy đủ", false, true))
        assertNull(controller.current)
    }

    @Test fun staleSkipAndCompletedTicksHaveNoEffect() {
        val controller = ReplyRevealController()
        controller.receive("new", "token", "Xin chào", true, true)
        assertNull(controller.skip("old"))
        assertTrue(controller.skip("new")!!.complete)
        assertNull(controller.advance("token"))
        assertNull(controller.skip("new"))
    }

    @Test fun historyLoadsImmediatelyWhileExactIncomingRowWaitsForPresentation() {
        val history = MessageEntity("history", "chat", "assistant", "Lịch sử", "happy", 1L)
        val user = MessageEntity("user", "chat", "user", "Câu hỏi", null, 2L)
        val incoming = MessageEntity("incoming", "chat", "assistant", "Mới", "sad", 3L)
        val stored = listOf(history, user, incoming)
        assertEquals(listOf(history, user), visibleChatMessages(stored, "incoming"))
        assertEquals(stored, visibleChatMessages(stored, null))
        assertEquals("Mới", incoming.text)
    }
}
