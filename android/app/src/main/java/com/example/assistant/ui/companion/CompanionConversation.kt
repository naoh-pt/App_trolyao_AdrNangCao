package com.example.assistant.ui.companion

import java.text.Normalizer
import java.time.Instant
import java.time.ZoneId
import com.example.assistant.ui.chat.ChatUiState

fun moodDate(now: Instant = Instant.now(), zone: ZoneId = ZoneId.systemDefault()): String = now.atZone(zone).toLocalDate().toString()

enum class MoodChoice(val label: String, val message: String) {
    JOY("Rất vui", "Hôm nay mình cảm thấy rất vui."),
    GOOD("Khá ổn", "Hôm nay mình cảm thấy khá ổn."),
    NORMAL("Bình thường", "Hôm nay mình cảm thấy bình thường."),
    SAD("Hơi buồn", "Hôm nay mình cảm thấy hơi buồn."),
    STRESSED("Căng thẳng", "Hôm nay mình đang cảm thấy căng thẳng."),
}
enum class SupportChoice(val label: String, val message: String) {
    LISTEN("Chỉ cần lắng nghe", "Anna chỉ cần lắng nghe mình thôi nhé."),
    ADVICE("Cho mình lời khuyên", "Anna cho mình một vài lời khuyên nhé."),
    SOLVE("Cùng tìm giải pháp", "Anna cùng mình tìm cách giải quyết nhé."),
}

data class CompanionChatState(
    val moodVisible: Boolean = false,
    val manualMoodVisible: Boolean = false,
    val moodOwner: String? = null,
    val supportMessageId: String? = null,
    val selectionBusy: Boolean = false,
    val entryEngaged: Boolean = false,
) {
    fun userTurn() = copy(moodVisible = false, manualMoodVisible = false, supportMessageId = null, entryEngaged = true)
    fun takeMood(choice: MoodChoice): Pair<CompanionChatState, String>? =
        if ((!moodVisible && !manualMoodVisible) || selectionBusy) null else copy(moodVisible = false, manualMoodVisible = false, supportMessageId = null, selectionBusy = true) to choice.message
    fun takeSupport(choice: SupportChoice): Pair<CompanionChatState, String>? =
        if (supportMessageId == null || selectionBusy) null else copy(supportMessageId = null, moodVisible = false, selectionBusy = true) to choice.message
}

fun moodEligible(existing: Boolean, enabled: Boolean, memoryDelivered: Boolean?, claimedToday: Boolean): Boolean =
    existing && enabled && memoryDelivered == false && !claimedToday

fun ChatUiState.selectCompanion(mood: MoodChoice?, support: SupportChoice?): Pair<CompanionChatState, String>? {
    if (!online || sending || pending != null || (mood == null) == (support == null)) return null
    return if (mood != null) companion.takeMood(mood) else companion.takeSupport(support!!)
}

fun ChatUiState.openManualMood(): ChatUiState =
    if (!online || sending || pending != null || companion.selectionBusy) this
    else copy(companion = companion.copy(manualMoodVisible = true))

fun ChatUiState.dismissManualMood(): ChatUiState =
    copy(companion = companion.copy(manualMoodVisible = false))

fun emotionalSupportCue(raw: String): Boolean {
    val text = Normalizer.normalize(raw, Normalizer.Form.NFC).lowercase().replace(Regex("[\\s\\p{Z}]+"), " ").trim()
    // Explicit Unicode boundaries work on Android ICU and desktop JVM alike;
    // Android does not support Java's UNICODE_CHARACTER_CLASS flag.
    fun words(choices: String) = Regex("(?<![\\p{L}\\p{M}\\p{N}_])(?:$choices)(?![\\p{L}\\p{M}\\p{N}_])", RegexOption.IGNORE_CASE)
    if (words("là gì|giải thích|định nghĩa|dịch|viết câu|phân tích|bài hát|bài nhạc|công thức|vật lý|bộ nhớ|API").containsMatchIn(text)) return false
    return words("mình|tôi|em|anh|chị").containsMatchIn(text) &&
        words("buồn|thất vọng|mất động lực|căng thẳng|áp lực|mệt mỏi|lo lắng|cô đơn|khó chịu|quá tải").containsMatchIn(text)
}
