package com.example.assistant.domain

import com.google.gson.annotations.SerializedName
import java.text.Normalizer

enum class AddressStyle(val label: String) {
    @SerializedName("anna_ban") ANNA_BAN("Anna – bạn"),
    @SerializedName("minh_ban") MINH_BAN("mình – bạn"),
    @SerializedName("chi_em") CHI_EM("chị – em"),
    @SerializedName("em_anh") EM_ANH("em – anh"),
    @SerializedName("em_chi") EM_CHI("em – chị"),
}
enum class HumorLevel(val label: String) {
    @SerializedName("low") LOW("Ít đùa"), @SerializedName("medium") MEDIUM("Vừa phải"), @SerializedName("high") HIGH("Tinh nghịch"),
}
enum class ResponseLength(val label: String) {
    @SerializedName("short") SHORT("Ngắn gọn"), @SerializedName("medium") MEDIUM("Vừa phải"), @SerializedName("detailed") DETAILED("Chi tiết"),
}
enum class SupportStyle(val label: String) {
    @SerializedName("balanced") BALANCED("Cân bằng"), @SerializedName("listen_first") LISTEN_FIRST("Lắng nghe trước"),
    @SerializedName("advice_first") ADVICE_FIRST("Ưu tiên lời khuyên"), @SerializedName("solve_together") SOLVE_TOGETHER("Cùng tìm giải pháp"),
}

data class CompanionPreferences(
    @SerializedName("preferred_name") val preferredName: String? = null,
    @SerializedName("address_style") val addressStyle: AddressStyle = AddressStyle.ANNA_BAN,
    @SerializedName("humor_level") val humorLevel: HumorLevel = HumorLevel.MEDIUM,
    @SerializedName("response_length") val responseLength: ResponseLength = ResponseLength.MEDIUM,
    @SerializedName("support_style") val supportStyle: SupportStyle = SupportStyle.BALANCED,
    @SerializedName("mood_check_in_enabled") val moodCheckInEnabled: Boolean = true,
) {
    fun valid(): Boolean = validPreferredName(preferredName) && AddressStyle.entries.contains(addressStyle) &&
        HumorLevel.entries.contains(humorLevel) && ResponseLength.entries.contains(responseLength) && SupportStyle.entries.contains(supportStyle)
}

fun validPreferredName(raw: String?): Boolean {
    if (raw == null) return true
    if (raw.any { Character.isISOControl(it) || Character.getType(it) == Character.FORMAT.toInt() || it == '\u2028' || it == '\u2029' }) return false
    val name = Normalizer.normalize(raw.trim(), Normalizer.Form.NFC)
    if (name.isEmpty()) return true
    if (name.codePointCount(0, name.length) > 30 || name.split(Regex("\\s+")).size > 4) return false
    if (!name.any { it.isLetterOrDigit() } || !name.all { it.isLetterOrDigit() || it in " .'-’" }) return false
    return !Regex("(?<![\\p{L}\\p{M}\\p{N}_])(?:ignore|instructions?|system|prompt|reveal|hãy|tiết lộ|bỏ qua)(?![\\p{L}\\p{M}\\p{N}_])", RegexOption.IGNORE_CASE).containsMatchIn(name)
}
