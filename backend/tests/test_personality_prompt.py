"""Tests for Anna personality specification, system prompt, and emotion rules."""

import pytest

from app.services.personality import (
    ALLOWED_EMOTIONS,
    ANNA_SYSTEM_PROMPT,
    ANNA_QUOTA_FALLBACK_TEXT,
    ANNA_QUOTA_FALLBACK_EMOTION,
    DEFAULT_EMOTION,
    normalize_emotion,
)


def test_anna_name_in_prompt():
    """Anna's name must be explicitly declared in the system instruction."""
    assert "Anna" in ANNA_SYSTEM_PROMPT


def test_school_context_in_prompt():
    """Học viện Kỹ thuật Mật mã context must be declared in the system instruction."""
    assert "Học viện Kỹ thuật Mật mã" in ANNA_SYSTEM_PROMPT


def test_moderate_answer_length_guidance():
    """Guidance for moderate length (2-5 sentences) must be present."""
    assert "2 đến 5 câu" in ANNA_SYSTEM_PROMPT or "2-5 câu" in ANNA_SYSTEM_PROMPT


def test_allowed_emotions_in_prompt():
    """All 4 allowed emotion values must be explicitly specified in the prompt."""
    for emotion in ["neutral", "happy", "sad", "surprised"]:
        assert f'"{emotion}"' in ANNA_SYSTEM_PROMPT or f"'{emotion}'" in ANNA_SYSTEM_PROMPT


def test_structured_json_response_in_prompt():
    """System instruction must require JSON format with reply and emotion fields."""
    assert "JSON" in ANNA_SYSTEM_PROMPT
    assert '"reply"' in ANNA_SYSTEM_PROMPT
    assert '"emotion"' in ANNA_SYSTEM_PROMPT


def test_android_ui_states_not_requested_as_emotions():
    """Prompt must strictly forbid Android UI states (idle, talk, thinking) as emotion values."""
    prompt_lower = ANNA_SYSTEM_PROMPT.lower()
    assert "idle" in prompt_lower
    assert "talk" in prompt_lower
    assert "thinking" in prompt_lower
    # Ensure they are explicitly discouraged / forbidden, not listed as valid emotions
    assert "không sử dụng các trạng thái giao diện" in prompt_lower or "tuyệt đối không" in prompt_lower


def test_rag_truthfulness_instruction_in_prompt():
    """Prompt must instruct Anna not to invent school rules or regulations when not in RAG."""
    assert "không tự suy diễn hoặc bịa đặt quy định" in ANNA_SYSTEM_PROMPT or "không bịa đặt" in ANNA_SYSTEM_PROMPT


@pytest.mark.parametrize("valid_emotion", ["neutral", "happy", "sad", "surprised"])
def test_valid_emotions_survive(valid_emotion):
    """All valid emotion strings remain unchanged."""
    assert normalize_emotion(valid_emotion) == valid_emotion


@pytest.mark.parametrize(
    "raw_input,expected",
    [
        ("HAPPY", "happy"),
        ("  SAD  ", "sad"),
        ("Neutral", "neutral"),
        ("SuRpRiSeD", "surprised"),
    ],
)
def test_uppercase_whitespace_emotion_normalized(raw_input, expected):
    """Case and whitespace variations of allowed emotions are normalized safely."""
    assert normalize_emotion(raw_input) == expected


@pytest.mark.parametrize(
    "invalid_input",
    [
        "angry",
        "fear",
        "idle",
        "talk",
        "thinking",
        "excited",
        "",
        "   ",
        None,
        42,
        {"emotion": "happy"},
        ["neutral"],
    ],
)
def test_invalid_emotion_becomes_neutral(invalid_input):
    """Any invalid, missing, or unsupported emotion safely defaults to neutral."""
    assert normalize_emotion(invalid_input) == "neutral"


def test_quota_fallback_constants():
    """Quota fallback message must use friendly Anna voice and sad emotion."""
    assert "Anna" in ANNA_QUOTA_FALLBACK_TEXT
    assert "hết lượt" in ANNA_QUOTA_FALLBACK_TEXT or "AI" in ANNA_QUOTA_FALLBACK_TEXT
    assert ANNA_QUOTA_FALLBACK_EMOTION == "sad"
    assert ANNA_QUOTA_FALLBACK_EMOTION in ALLOWED_EMOTIONS
