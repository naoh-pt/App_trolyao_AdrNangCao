package com.example.assistant.domain

enum class CharacterState { IDLE, THINKING, TALKING }

enum class Emotion {
    NEUTRAL, HAPPY, SAD, SURPRISED;

    companion object {
        /** Giá trị lạ/null -> NEUTRAL (UC03). */
        fun from(value: String?): Emotion = when (value?.trim()?.lowercase()) {
            "happy" -> HAPPY
            "sad" -> SAD
            "surprised" -> SURPRISED
            else -> NEUTRAL
        }
    }
}
