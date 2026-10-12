"""Contract tests for Gemini and Groq providers.

Verifies:
- Structured JSON parsing (reply, emotion)
- Emotion normalization (missing, invalid, uppercase, whitespace)
- Non-empty reply validation
- Malformed JSON safety
- Exception classification (quota -> 429, timeout -> 504, auth/5xx/conn -> 503)
- Anna prompt inclusion
- Conversation history order preservation
- RAG context propagation
"""

import json
from unittest.mock import MagicMock
import httpx
import pytest

from app.exceptions import (
    LLMQuotaExhaustedException,
    LLMTimeoutException,
    LLMUnavailableException,
)
from app.services.personality import ANNA_SYSTEM_PROMPT
from app.services.providers.gemini_provider import GeminiProvider
from app.services.providers.groq_provider import GroqProvider
import groq


# ---------------------------------------------------------------------------
# Helpers & Fakes
# ---------------------------------------------------------------------------

def _dummy_request() -> httpx.Request:
    return httpx.Request("POST", "https://api.test.example/v1")


class FakeGeminiResponse:
    """Simulates google.genai response object."""

    def __init__(self, text: str):
        self.text = text


class FakeGeminiModels:
    """Simulates client.models namespace."""

    def __init__(self, response_text: str | None = None, side_effect: Exception | None = None):
        self.response_text = response_text
        self.side_effect = side_effect
        self.last_call_kwargs = None

    def generate_content(self, **kwargs):
        self.last_call_kwargs = kwargs
        if self.side_effect:
            raise self.side_effect
        return FakeGeminiResponse(self.response_text or "{}")


class FakeGeminiClient:
    """Simulates google.genai.Client."""

    def __init__(self, response_text: str | None = None, side_effect: Exception | None = None):
        self.models = FakeGeminiModels(response_text=response_text, side_effect=side_effect)


class FakeGroqChoice:
    def __init__(self, content: str):
        self.message = MagicMock()
        self.message.content = content


class FakeGroqResponse:
    def __init__(self, content: str | None = None, choices: list | None = None):
        if choices is not None:
            self.choices = choices
        elif content is not None:
            self.choices = [FakeGroqChoice(content)]
        else:
            self.choices = []


class FakeGroqCompletions:
    def __init__(self, content: str | None = None, side_effect: Exception | None = None, choices: list | None = None):
        self.content = content
        self.side_effect = side_effect
        self.choices = choices
        self.last_call_kwargs = None

    def create(self, **kwargs):
        self.last_call_kwargs = kwargs
        if self.side_effect:
            raise self.side_effect
        return FakeGroqResponse(content=self.content, choices=self.choices)


class FakeGroqChat:
    def __init__(self, completions: FakeGroqCompletions):
        self.completions = completions


class FakeGroqClient:
    def __init__(self, content: str | None = None, side_effect: Exception | None = None, choices: list | None = None):
        self.chat = FakeGroqChat(FakeGroqCompletions(content=content, side_effect=side_effect, choices=choices))


# ===========================================================================
# 1. GeminiProvider Contract Tests
# ===========================================================================

class TestGeminiProviderContract:

    def test_gemini_valid_json_parses_correctly(self):
        client = FakeGeminiClient(
            response_text=json.dumps({"reply": "Chào bạn! Mình là Anna.", "emotion": "happy"})
        )
        provider = GeminiProvider(api_key="test-key", client=client)

        reply, emotion = provider.generate_reply([], "Xin chào")
        assert reply == "Chào bạn! Mình là Anna."
        assert emotion == "happy"

    def test_gemini_missing_emotion_defaults_to_neutral(self):
        client = FakeGeminiClient(
            response_text=json.dumps({"reply": "Hôm nay thời tiết đẹp quá."})
        )
        provider = GeminiProvider(api_key="test-key", client=client)

        reply, emotion = provider.generate_reply([], "Thời tiết sao?")
        assert reply == "Hôm nay thời tiết đẹp quá."
        assert emotion == "neutral"

    def test_gemini_invalid_emotion_normalizes_to_neutral(self):
        client = FakeGeminiClient(
            response_text=json.dumps({"reply": "Tôi ổn.", "emotion": "angry"})
        )
        provider = GeminiProvider(api_key="test-key", client=client)

        _, emotion = provider.generate_reply([], "Bạn sao rồi?")
        assert emotion == "neutral"

    def test_gemini_uppercase_emotion_normalizes_to_lowercase(self):
        client = FakeGeminiClient(
            response_text=json.dumps({"reply": "Tuyệt vời!", "emotion": "HAPPY"})
        )
        provider = GeminiProvider(api_key="test-key", client=client)

        _, emotion = provider.generate_reply([], "Tin vui!")
        assert emotion == "happy"

    def test_gemini_whitespace_emotion_strips_and_normalizes(self):
        client = FakeGeminiClient(
            response_text=json.dumps({"reply": "Ồ thật sao!", "emotion": "  surprised \n"})
        )
        provider = GeminiProvider(api_key="test-key", client=client)

        _, emotion = provider.generate_reply([], "Bất ngờ chưa?")
        assert emotion == "surprised"

    def test_gemini_reply_content_non_empty(self):
        client = FakeGeminiClient(
            response_text=json.dumps({"reply": "  Có nội dung  ", "emotion": "neutral"})
        )
        provider = GeminiProvider(api_key="test-key", client=client)

        reply, _ = provider.generate_reply([], "Alo")
        assert reply == "Có nội dung"

    def test_gemini_empty_reply_rejected(self):
        client = FakeGeminiClient(
            response_text=json.dumps({"reply": "   ", "emotion": "neutral"})
        )
        provider = GeminiProvider(api_key="test-key", client=client)

        with pytest.raises(LLMUnavailableException) as exc_info:
            provider.generate_reply([], "Alo")
        assert "rỗng hoặc không hợp lệ" in str(exc_info.value.message)

    def test_gemini_malformed_json_handled_safely(self):
        client = FakeGeminiClient(response_text="Not valid JSON at all")
        provider = GeminiProvider(api_key="test-key", client=client)

        with pytest.raises(LLMUnavailableException) as exc_info:
            provider.generate_reply([], "Alo")
        assert "không đúng định dạng" in str(exc_info.value.message)

    def test_gemini_quota_error_maps_to_quota_exhausted(self):
        # google.genai error with RESOURCE_EXHAUSTED / code 429
        class FakeGenaiQuotaError(Exception):
            code = 429
            status = "RESOURCE_EXHAUSTED"

        err = FakeGenaiQuotaError("429 RESOURCE_EXHAUSTED: Quota exceeded for model")
        client = FakeGeminiClient(side_effect=err)
        provider = GeminiProvider(api_key="test-key", client=client)

        with pytest.raises(LLMQuotaExhaustedException):
            provider.generate_reply([], "Alo")

    def test_gemini_timeout_maps_to_timeout_exception(self):
        client = FakeGeminiClient(side_effect=TimeoutError("Request timed out"))
        provider = GeminiProvider(api_key="test-key", client=client)

        with pytest.raises(LLMTimeoutException):
            provider.generate_reply([], "Alo")

    def test_gemini_auth_error_maps_to_controlled_exception(self):
        err = Exception("401 Unauthorized: API key invalid")
        client = FakeGeminiClient(side_effect=err)
        provider = GeminiProvider(api_key="test-key", client=client)

        with pytest.raises(LLMUnavailableException):
            provider.generate_reply([], "Alo")

    def test_gemini_missing_api_key_raises_unavailable(self):
        provider = GeminiProvider(api_key=None, client=None)
        with pytest.raises(LLMUnavailableException) as exc_info:
            provider.generate_reply([], "Alo")
        assert "Chưa cấu hình API Key" in str(exc_info.value.message)

    def test_gemini_5xx_maps_to_controlled_exception(self):
        err = Exception("500 Internal Server Error: Gemini backend crash")
        client = FakeGeminiClient(side_effect=err)
        provider = GeminiProvider(api_key="test-key", client=client)

        with pytest.raises(LLMUnavailableException):
            provider.generate_reply([], "Alo")

    def test_gemini_anna_prompt_passed(self):
        client = FakeGeminiClient(
            response_text=json.dumps({"reply": "Dạ em chào anh!", "emotion": "happy"})
        )
        provider = GeminiProvider(api_key="test-key", client=client)

        provider.generate_reply([], "Chào bạn")
        call_kwargs = client.models.last_call_kwargs
        assert call_kwargs is not None
        config = call_kwargs.get("config")
        assert config is not None
        assert ANNA_SYSTEM_PROMPT in config.system_instruction

    def test_gemini_history_order_preserved(self):
        client = FakeGeminiClient(
            response_text=json.dumps({"reply": "Dạ được ạ!", "emotion": "neutral"})
        )
        provider = GeminiProvider(api_key="test-key", client=client)

        history = [
            {"role": "user", "text": "Câu 1"},
            {"role": "assistant", "text": "Trả lời 1"},
            {"role": "user", "text": "Câu 2"},
        ]
        provider.generate_reply(history, "Câu 3 mới")

        call_kwargs = client.models.last_call_kwargs
        contents = call_kwargs.get("contents")
        assert len(contents) == 4
        assert contents[0].role == "user"
        assert contents[0].parts[0].text == "Câu 1"
        assert contents[1].role == "model"
        assert contents[1].parts[0].text == "Trả lời 1"
        assert contents[2].role == "user"
        assert contents[2].parts[0].text == "Câu 2"
        assert contents[3].role == "user"
        assert contents[3].parts[0].text == "Câu 3 mới"

    def test_gemini_rag_context_included_when_present(self):
        client = FakeGeminiClient(
            response_text=json.dumps({"reply": "Theo tài liệu KMA...", "emotion": "neutral"})
        )
        provider = GeminiProvider(api_key="test-key", client=client)

        rag_doc = "[Tài liệu KMA] Học viện Kỹ thuật Mật mã xét tuyển..."
        provider.generate_reply([], "KMA tuyển sinh thế nào?", rag_context=rag_doc)

        call_kwargs = client.models.last_call_kwargs
        config = call_kwargs.get("config")
        assert rag_doc in config.system_instruction
        assert ANNA_SYSTEM_PROMPT in config.system_instruction


# ===========================================================================
# 2. GroqProvider Contract Tests
# ===========================================================================

class TestGroqProviderContract:

    def test_groq_valid_json_parses_correctly(self):
        client = FakeGroqClient(
            content=json.dumps({"reply": "Chào bạn nhé! Mình là Anna.", "emotion": "happy"})
        )
        provider = GroqProvider(api_key="gsk-test", client=client)

        reply, emotion = provider.generate_reply([], "Xin chào")
        assert reply == "Chào bạn nhé! Mình là Anna."
        assert emotion == "happy"

    def test_groq_missing_emotion_defaults_to_neutral(self):
        client = FakeGroqClient(
            content=json.dumps({"reply": "Mình có thể hỗ trợ gì cho bạn?"})
        )
        provider = GroqProvider(api_key="gsk-test", client=client)

        reply, emotion = provider.generate_reply([], "Alo")
        assert reply == "Mình có thể hỗ trợ gì cho bạn?"
        assert emotion == "neutral"

    def test_groq_invalid_emotion_normalizes_to_neutral(self):
        client = FakeGroqClient(
            content=json.dumps({"reply": "Ừm.", "emotion": "fearful"})
        )
        provider = GroqProvider(api_key="gsk-test", client=client)

        _, emotion = provider.generate_reply([], "Alo")
        assert emotion == "neutral"

    def test_groq_uppercase_emotion_normalizes_to_lowercase(self):
        client = FakeGroqClient(
            content=json.dumps({"reply": "Buồn quá bạn ơi.", "emotion": "SAD"})
        )
        provider = GroqProvider(api_key="gsk-test", client=client)

        _, emotion = provider.generate_reply([], "Mình trượt môn rồi")
        assert emotion == "sad"

    def test_groq_whitespace_emotion_strips_and_normalizes(self):
        client = FakeGroqClient(
            content=json.dumps({"reply": "Vui ghê!", "emotion": "   happy \t"})
        )
        provider = GroqProvider(api_key="gsk-test", client=client)

        _, emotion = provider.generate_reply([], "Được 10 điểm nè")
        assert emotion == "happy"

    def test_groq_reply_content_non_empty(self):
        client = FakeGroqClient(
            content=json.dumps({"reply": "  Nội dung phản hồi  ", "emotion": "neutral"})
        )
        provider = GroqProvider(api_key="gsk-test", client=client)

        reply, _ = provider.generate_reply([], "Alo")
        assert reply == "Nội dung phản hồi"

    def test_groq_empty_reply_rejected(self):
        client = FakeGroqClient(
            content=json.dumps({"reply": "    ", "emotion": "neutral"})
        )
        provider = GroqProvider(api_key="gsk-test", client=client)

        with pytest.raises(LLMUnavailableException) as exc_info:
            provider.generate_reply([], "Alo")
        assert "rỗng hoặc không hợp lệ" in str(exc_info.value.message)

    def test_groq_empty_choices_handled(self):
        client = FakeGroqClient(choices=[])
        provider = GroqProvider(api_key="gsk-test", client=client)

        with pytest.raises(LLMUnavailableException) as exc_info:
            provider.generate_reply([], "Alo")
        assert "không trả về kết quả" in str(exc_info.value.message)

    def test_groq_malformed_json_handled_safely(self):
        client = FakeGroqClient(content="<<<malformed non-json>>>")
        provider = GroqProvider(api_key="gsk-test", client=client)

        with pytest.raises(LLMUnavailableException) as exc_info:
            provider.generate_reply([], "Alo")
        assert "không đúng định dạng" in str(exc_info.value.message)

    def test_groq_quota_error_maps_to_quota_exhausted(self):
        req = _dummy_request()
        resp = httpx.Response(429, request=req)
        err = groq.RateLimitError("Rate limit reached: TPM exceeded", response=resp, body=None)
        client = FakeGroqClient(side_effect=err)
        provider = GroqProvider(api_key="gsk-test", client=client)

        with pytest.raises(LLMQuotaExhaustedException):
            provider.generate_reply([], "Alo")

    def test_groq_timeout_maps_to_timeout_exception(self):
        req = _dummy_request()
        err = groq.APITimeoutError(request=req)
        client = FakeGroqClient(side_effect=err)
        provider = GroqProvider(api_key="gsk-test", client=client)

        with pytest.raises(LLMTimeoutException):
            provider.generate_reply([], "Alo")

    def test_groq_auth_error_maps_to_controlled_exception(self):
        req = _dummy_request()
        resp = httpx.Response(401, request=req)
        err = groq.AuthenticationError("Invalid API Key provided", response=resp, body=None)
        client = FakeGroqClient(side_effect=err)
        provider = GroqProvider(api_key="gsk-test", client=client)

        with pytest.raises(LLMUnavailableException) as exc_info:
            provider.generate_reply([], "Alo")
        assert "Xác thực Groq thất bại" in str(exc_info.value.message)

    def test_groq_missing_api_key_raises_unavailable(self):
        provider = GroqProvider(api_key=None, client=None)
        with pytest.raises(LLMUnavailableException) as exc_info:
            provider.generate_reply([], "Alo")
        assert "Chưa cấu hình API Key cho Groq" in str(exc_info.value.message)

    def test_groq_5xx_maps_to_controlled_exception(self):
        req = _dummy_request()
        resp = httpx.Response(500, request=req)
        err = groq.InternalServerError("Internal server error", response=resp, body=None)
        client = FakeGroqClient(side_effect=err)
        provider = GroqProvider(api_key="gsk-test", client=client)

        with pytest.raises(LLMUnavailableException) as exc_info:
            provider.generate_reply([], "Alo")
        assert "không khả dụng" in str(exc_info.value.message)

    def test_groq_connection_error_maps_to_controlled_exception(self):
        req = _dummy_request()
        err = groq.APIConnectionError(request=req)
        client = FakeGroqClient(side_effect=err)
        provider = GroqProvider(api_key="gsk-test", client=client)

        with pytest.raises(LLMUnavailableException) as exc_info:
            provider.generate_reply([], "Alo")
        assert "Lỗi kết nối tới Groq" in str(exc_info.value.message)

    def test_groq_anna_prompt_passed(self):
        client = FakeGroqClient(
            content=json.dumps({"reply": "Chào bạn nhé!", "emotion": "happy"})
        )
        provider = GroqProvider(api_key="gsk-test", client=client)

        provider.generate_reply([], "Chào bạn")
        call_kwargs = client.chat.completions.last_call_kwargs
        assert call_kwargs is not None
        messages = call_kwargs.get("messages", [])
        assert len(messages) >= 1
        assert messages[0]["role"] == "system"
        assert ANNA_SYSTEM_PROMPT in messages[0]["content"]

    def test_groq_history_order_preserved(self):
        client = FakeGroqClient(
            content=json.dumps({"reply": "Okie bạn!", "emotion": "neutral"})
        )
        provider = GroqProvider(api_key="gsk-test", client=client)

        history = [
            {"role": "user", "text": "Câu hỏi 1"},
            {"role": "assistant", "text": "Trả lời 1"},
            {"role": "user", "text": "Câu hỏi 2"},
        ]
        provider.generate_reply(history, "Câu hỏi 3")

        call_kwargs = client.chat.completions.last_call_kwargs
        messages = call_kwargs.get("messages", [])
        # messages[0] = system, messages[1] = u1, messages[2] = a1, messages[3] = u2, messages[4] = u3
        assert len(messages) == 5
        assert messages[0]["role"] == "system"
        assert messages[1] == {"role": "user", "content": "Câu hỏi 1"}
        assert messages[2] == {"role": "assistant", "content": "Trả lời 1"}
        assert messages[3] == {"role": "user", "content": "Câu hỏi 2"}
        assert messages[4] == {"role": "user", "content": "Câu hỏi 3"}

    def test_groq_rag_context_included_when_present(self):
        client = FakeGroqClient(
            content=json.dumps({"reply": "Thông tin học phí...", "emotion": "neutral"})
        )
        provider = GroqProvider(api_key="gsk-test", client=client)

        rag_doc = "[Tài liệu Học viện Kỹ thuật Mật mã] Quy chế đào tạo tín chỉ..."
        provider.generate_reply([], "Học phí KMA bao nhiêu?", rag_context=rag_doc)

        call_kwargs = client.chat.completions.last_call_kwargs
        system_msg = call_kwargs.get("messages", [])[0]["content"]
        assert rag_doc in system_msg
        assert ANNA_SYSTEM_PROMPT in system_msg

    def test_groq_response_format_json_requested(self):
        client = FakeGroqClient(
            content=json.dumps({"reply": "Json format test", "emotion": "happy"})
        )
        provider = GroqProvider(api_key="gsk-test", client=client)

        provider.generate_reply([], "Test format")
        call_kwargs = client.chat.completions.last_call_kwargs
        assert call_kwargs.get("response_format") == {"type": "json_object"}

    def test_groq_default_model_is_openai_gpt_oss_120b(self):
        provider = GroqProvider(api_key="gsk-test")
        assert provider.model == "openai/gpt-oss-120b"
        assert "llama-3.3-70b-versatile" not in provider.model

    def test_groq_client_configured_with_max_retries_zero_and_seconds_timeout(self, monkeypatch):
        captured = {}

        def fake_groq_init(**kwargs):
            captured.update(kwargs)
            return MagicMock()

        monkeypatch.setattr("groq.Groq", fake_groq_init)
        provider = GroqProvider(api_key="gsk-key-xyz", timeout_ms=15000)
        provider.get_client()

        assert captured["max_retries"] == 0
        assert captured["timeout"] == 15.0
        assert captured["api_key"] == "gsk-key-xyz"

    def test_groq_real_client_attributes_offline(self):
        # Official Groq 1.x client initialization runs offline without network
        provider = GroqProvider(api_key="gsk-offline-test", timeout_ms=15000)
        client = provider.get_client()
        assert client.max_retries == 0
        assert client.timeout == 15.0


class TestRetryConfiguration:

    def test_gemini_generation_client_configured_with_single_attempt(self, monkeypatch):
        captured = {}

        def fake_genai_client(**kwargs):
            captured.update(kwargs)
            return MagicMock()

        monkeypatch.setattr("google.genai.Client", fake_genai_client)
        provider = GeminiProvider(api_key="test-key", timeout_ms=28000)
        provider.get_client()

        assert "http_options" in captured
        http_options = captured["http_options"]
        assert http_options.timeout == 28000
        assert http_options.retry_options is not None
        assert http_options.retry_options.attempts == 1

    def test_gemini_embedding_client_configured_with_single_attempt(self):
        from google.genai import types
        import app.services.rag_service as rag_service

        # Verify that rag_service imports HttpRetryOptions and constructs with attempts=1
        retry_opts = types.HttpRetryOptions(attempts=1)
        assert retry_opts.attempts == 1
        # Check rag_service source code ensures retry_options with attempts=1
        import inspect
        src = inspect.getsource(rag_service)
        assert "HttpRetryOptions(attempts=1)" in src

