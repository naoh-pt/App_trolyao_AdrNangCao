package com.example.assistant.ui.demo

enum class DemoCategory(val title: String, val enabled: Boolean = true) {
    Conversation("Trò chuyện"), Time("Thời gian"), Study("Học tập & RAG"),
    Emotion("Cảm xúc"), Utilities("Tiện ích"), Weather("Thời tiết"), Memory("Trí nhớ"),
}

data class DemoQuestion(
    val id: String,
    val title: String,
    val prompt: String,
    val category: DemoCategory,
    val requiresBackend: Boolean = true,
    val requiresAi: Boolean = false,
    val requiresRag: Boolean = false,
    val requiresInternet: Boolean = false,
    val enabled: Boolean = true,
)

data class DemoScenario(
    val id: String,
    val title: String,
    val description: String,
    val questionIds: List<String>,
)

/** Bundled, read-only presentation data. Loading this object performs no I/O. */
object DemoQuestionCatalog {
    val questions: List<DemoQuestion> = listOf(
        DemoQuestion("chat_greeting", "Chào Anna", "Xin chào Anna", DemoCategory.Conversation),
        DemoQuestion("chat_help", "Anna giúp được gì?", "Anna có thể giúp mình những gì?", DemoCategory.Conversation, requiresAi = true, requiresInternet = true),
        DemoQuestion("chat_intro", "Giới thiệu bản thân", "Anna hãy giới thiệu ngắn gọn về bản thân nhé", DemoCategory.Conversation, requiresAi = true, requiresInternet = true),
        DemoQuestion("chat_joke", "Chuyện vui học tập", "Kể mình nghe một câu đùa vui về việc học đi", DemoCategory.Conversation, requiresAi = true, requiresInternet = true),
        DemoQuestion("time_now", "Giờ hiện tại", "Mấy giờ rồi?", DemoCategory.Time),
        DemoQuestion("time_date", "Ngày hôm nay", "Hôm nay là ngày bao nhiêu?", DemoCategory.Time),
        DemoQuestion("time_weekday", "Thứ trong tuần", "Hôm nay là thứ mấy?", DemoCategory.Time),
        DemoQuestion("time_period", "Buổi trong ngày", "Bây giờ là buổi gì?", DemoCategory.Time),
        DemoQuestion("study_tuition", "Học phí theo tín chỉ", "Học phí đại học hệ chính quy là bao nhiêu tiền một tín chỉ?", DemoCategory.Study, requiresAi = true, requiresRag = true, requiresInternet = true),
        DemoQuestion("study_rest", "Giải thích REST API", "Anna hãy giải thích REST API trong khoảng 5 câu dễ hiểu", DemoCategory.Study, requiresAi = true, requiresInternet = true),
        DemoQuestion("study_plan", "Kế hoạch học Android", "Hãy lập kế hoạch học Android cho mình trong tối nay", DemoCategory.Study, requiresAi = true, requiresInternet = true),
        DemoQuestion("study_summary", "Tóm tắt cuộc trò chuyện", "Tóm tắt giúp mình nội dung vừa trao đổi", DemoCategory.Study, requiresAi = true, requiresInternet = true),
        DemoQuestion("emotion_happy", "Chia sẻ niềm vui", "Hôm nay mình vừa đạt điểm cao!", DemoCategory.Emotion, requiresAi = true, requiresInternet = true),
        DemoQuestion("emotion_sad", "Khi mất động lực", "Hôm nay mình hơi buồn và mất động lực học.", DemoCategory.Emotion, requiresAi = true, requiresInternet = true),
        DemoQuestion("emotion_surprised", "Tin bất ngờ", "Anna ơi, mình vừa nhận được học bổng bất ngờ!", DemoCategory.Emotion, requiresAi = true, requiresInternet = true),
        DemoQuestion("emotion_stressed", "Trước buổi báo cáo", "Mình đang khá căng thẳng vì sắp phải báo cáo.", DemoCategory.Emotion, requiresAi = true, requiresInternet = true),
        DemoQuestion("emotion_disappointed", "Khi bị điểm thấp", "Hôm nay mình bị điểm thấp và cảm thấy thất vọng.", DemoCategory.Emotion, requiresAi = true, requiresInternet = true),
        DemoQuestion("emotion_listen", "Chỉ muốn được lắng nghe", "Anna ơi, lúc này mình chỉ muốn được lắng nghe thôi.", DemoCategory.Emotion, requiresAi = true, requiresInternet = true),
        DemoQuestion("utility_timer", "Hẹn giờ 5 phút", "Nhắc tôi học bài sau 5 phút", DemoCategory.Utilities),
        DemoQuestion("utility_calendar", "Lịch học ngày mai", "Tạo lịch học Android lúc 8 giờ tối ngày mai", DemoCategory.Utilities),
        DemoQuestion("utility_weekday", "Họp thứ Hai tuần sau", "Tạo lịch họp nhóm lúc 7 giờ tối thứ 2 tuần sau", DemoCategory.Utilities),
        DemoQuestion("utility_map_kma", "Bản đồ Học viện", "Tìm trên bản đồ Học viện Kỹ thuật Mật mã", DemoCategory.Utilities, requiresInternet = true),
        DemoQuestion("utility_map_lake", "Bản đồ Hồ Gươm", "Tìm trên bản đồ Hồ Gươm.", DemoCategory.Utilities, requiresInternet = true),
        DemoQuestion("weather_now", "Thời tiết hiện tại", "Thời tiết Hà Nội hiện tại thế nào?", DemoCategory.Weather, requiresInternet = true),
        DemoQuestion("weather_rain", "Dự báo mưa", "Ngày mai Hà Nội có mưa không?", DemoCategory.Weather, requiresInternet = true),
        DemoQuestion("weather_temperature", "Nhiệt độ Bắc Ninh", "Nhiệt độ ở Bắc Ninh hôm nay bao nhiêu?", DemoCategory.Weather, requiresInternet = true),
        DemoQuestion("weather_raincoat", "Có cần áo mưa?", "Hôm nay mình có nên mang áo mưa ở Hà Nội không?", DemoCategory.Weather, requiresInternet = true),
        DemoQuestion("memory_name", "Lưu tên", "Anna hãy nhớ: mình tên là Hoàn.", DemoCategory.Memory),
        DemoQuestion("memory_preference", "Lưu sở thích", "Anna hãy nhớ: mình thích học Android.", DemoCategory.Memory),
        DemoQuestion("memory_list", "Xem trí nhớ", "Anna nhớ gì về mình?", DemoCategory.Memory),
        DemoQuestion("memory_event", "Nhắc khi vào trò chuyện", "Anna hãy nhớ: mình thi Android vào thứ Sáu tuần sau. Nhắc mình khi mở ứng dụng từ hôm nay.", DemoCategory.Memory),
        DemoQuestion("memory_forget", "Quên sở thích", "Anna hãy quên việc mình thích học Android.", DemoCategory.Memory),
    )

    val scenarios: List<DemoScenario> = listOf(
        DemoScenario("quick", "Demo nhanh 3 phút", "Chào hỏi, giờ hiện tại và hai tiện ích quen thuộc.",
            listOf("chat_greeting", "time_now", "utility_timer", "utility_map_kma")),
        DemoScenario("full", "Demo đầy đủ", "Trò chuyện, RAG, cảm xúc và các tiện ích. Cần nạp tài liệu RAG.",
            listOf("chat_greeting", "chat_help", "time_now", "study_tuition", "emotion_sad", "utility_timer", "utility_calendar", "utility_map_kma", "weather_now", "memory_name", "memory_list", "emotion_disappointed")),
        DemoScenario("no_quota", "Demo không phụ thuộc quota", "Không cần quota AI; backend vẫn phải chạy",
            listOf("chat_greeting", "time_now", "time_weekday", "utility_timer", "utility_calendar", "utility_map_lake")),
    )

    fun question(id: String): DemoQuestion? = questions.firstOrNull { it.id == id }
    fun scenario(id: String): DemoScenario? = scenarios.firstOrNull { it.id == id }
}
