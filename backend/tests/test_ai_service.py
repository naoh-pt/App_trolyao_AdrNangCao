"""Unit tests for the Gemini integration without any network calls."""

from unittest.mock import MagicMock, patch

import pytest

from ai_service import generate_reply
from app.exceptions import LLMTimeoutException, LLMUnavailableException


@pytest.fixture
def mock_gemini_client():
    with patch("ai_service.client") as client:
        yield client


def test_generate_reply_success(mock_gemini_client):
    response = MagicMock()
    response.text = '{"reply": "Chao ban", "emotion": "happy"}'
    mock_gemini_client.models.generate_content.return_value = response

    reply, emotion = generate_reply([{"role": "user", "text": "Cau cu"}], "Cau moi")

    assert reply == "Chao ban"
    assert emotion == "happy"
    contents = mock_gemini_client.models.generate_content.call_args.kwargs["contents"]
    assert contents[0].role == "user"
    assert contents[0].parts[0].text == "Cau cu"
    assert contents[1].parts[0].text == "Cau moi"


def test_generate_reply_timeout(mock_gemini_client):
    mock_gemini_client.models.generate_content.side_effect = TimeoutError("timeout")

    with pytest.raises(LLMTimeoutException):
        generate_reply([], "test")


def test_generate_reply_requires_reply_field(mock_gemini_client):
    response = MagicMock()
    response.text = '{"emotion": "sad"}'
    mock_gemini_client.models.generate_content.return_value = response

    with pytest.raises(LLMUnavailableException):
        generate_reply([], "test")


def test_generate_reply_normalizes_invalid_emotion(mock_gemini_client):
    response = MagicMock()
    response.text = '{"reply": "Ok", "emotion": "angry"}'
    mock_gemini_client.models.generate_content.return_value = response

    _, emotion = generate_reply([], "test")
    assert emotion == "neutral"
