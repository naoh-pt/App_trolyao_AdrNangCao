package com.example.assistant.ui.chat

import java.text.BreakIterator
import java.util.Locale
import com.example.assistant.data.local.MessageEntity

/** UTF-16 endpoints are used only after character-boundary segmentation. */
data class ReplyRevealPlan(val endpoints: List<Int>, val tickMs: Long) {
    val durationMs: Long get() = endpoints.size * tickMs
}

object ReplyRevealPlanner {
    const val TICK_MS = 30L
    const val MAX_DURATION_MS = 4500L

    fun plan(text: String, enabled: Boolean = true): ReplyRevealPlan {
        if (text.isEmpty()) return ReplyRevealPlan(emptyList(), 0)
        if (!enabled) return ReplyRevealPlan(listOf(text.length), 0)
        val iterator = BreakIterator.getCharacterInstance(Locale.ROOT)
        iterator.setText(text)
        val boundaries = mutableListOf<Int>()
        var end = iterator.next()
        while (end != BreakIterator.DONE) {
            // Older platform/JVM character iterators split some extended emoji clusters.
            val next = if (end < text.length) text.codePointAt(end) else -1
            val previous = text.codePointBefore(end)
            val kind = if (next >= 0) Character.getType(next) else -1
            var regionalCount = 0
            var index = end
            while (index > 0 && text.codePointBefore(index) in 0x1F1E6..0x1F1FF) {
                regionalCount++
                index -= Character.charCount(text.codePointBefore(index))
            }
            val joins = next == 0x200D || previous == 0x200D ||
                kind == Character.NON_SPACING_MARK.toInt() ||
                kind == Character.COMBINING_SPACING_MARK.toInt() ||
                kind == Character.ENCLOSING_MARK.toInt() ||
                next in 0x1F3FB..0x1F3FF || next in 0xE0020..0xE007F ||
                (next in 0x1F1E6..0x1F1FF && regionalCount % 2 == 1)
            if (end == text.length || !joins) boundaries += end
            end = iterator.next()
        }
        val duration = (boundaries.size * 20L).coerceIn(300L, MAX_DURATION_MS)
        val ticks = minOf(boundaries.size, (duration / TICK_MS).toInt()).coerceAtLeast(1)
        val endpoints = (1..ticks).map { tick ->
            boundaries[((tick.toLong() * boundaries.size + ticks - 1) / ticks).toInt() - 1]
        }
        // Tiny replies still get a perceptible reveal; longer replies batch clusters each tick.
        return ReplyRevealPlan(endpoints, if (ticks < 10) 300L / ticks else TICK_MS)
    }
}

/** Presentation only. The complete Room/domain message is never mutated. */
data class ReplyReveal(
    val messageId: String,
    val token: String,
    val fullText: String,
    val plan: ReplyRevealPlan,
    val tick: Int = 0,
) {
    val complete: Boolean get() = tick >= plan.endpoints.size
    val visibleText: String get() = if (complete) fullText else
        fullText.substring(0, if (tick == 0) 0 else plan.endpoints[tick - 1])
    fun advance(): ReplyReveal = copy(tick = (tick + 1).coerceAtMost(plan.endpoints.size))
    fun skip(): ReplyReveal = copy(tick = plan.endpoints.size)
}

fun visibleReplyText(messageId: String, fullText: String, reveal: ReplyReveal?): String =
    if (reveal?.messageId == messageId) reveal.visibleText else fullText

/** History can continue loading while only the exact incoming Room row awaits presentation. */
fun visibleChatMessages(messages: List<MessageEntity>, incomingAssistantId: String?): List<MessageEntity> =
    messages.filter { it.id != incomingAssistantId }

/** ViewModel-owned session: recomposition never creates or restarts a reveal. */
class ReplyRevealController {
    private val presentedIds = mutableSetOf<String>()
    var current: ReplyReveal? = null
        private set

    fun startRequest(historyIds: Collection<String>) {
        presentedIds += historyIds
        cancel()
    }

    fun receive(messageId: String, token: String, text: String, enabled: Boolean, screenActive: Boolean): Boolean {
        if (!presentedIds.add(messageId)) return false
        current = if (enabled && screenActive && text.isNotEmpty())
            ReplyReveal(messageId, token, text, ReplyRevealPlanner.plan(text)) else null
        return true
    }

    fun advance(token: String): ReplyReveal? {
        val reveal = current ?: return null
        if (reveal.token != token || reveal.complete) return null
        return reveal.advance().also { current = it }
    }

    fun skip(messageId: String): ReplyReveal? {
        val reveal = current ?: return null
        if (reveal.messageId != messageId || reveal.complete) return null
        return reveal.skip().also { current = it }
    }

    fun cancel() { current = null }
}
