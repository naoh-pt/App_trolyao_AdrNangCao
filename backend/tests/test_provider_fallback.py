"""Fallback matrix and provider orchestration tests (offline).

Verifies:
- Primary succeeds -> Fallback not called
- Primary quota / timeout / 5xx error -> Fallback called and succeeds
- Primary Groq -> Fallback Gemini
- Fallback disabled ('none') behavior
- Both providers quota exhausted -> raises LLMQuotaExhaustedException (leading to Anna friendly fallback)
- Both providers timeout -> raises LLMTimeoutException (504)
- Both providers network failure -> raises LLMUnavailableException (503)
- Primary auth failure behavior (documented choice: fallback attempted if configured)
- Programming errors do not trigger fallback
- RAG context passed identically to active provider
- Route level: quick replies bypass both providers
- Route level: idempotency replay bypasses both providers
- Route level: dual quota failure returns Anna friendly sad reply
"""

import uuid
from typing import Any, Dict, List, Tuple
import pytest

import app.api.v1.conversations as routes
from app.exceptions import (
    LLMQuotaExhaustedException,
    LLMTimeoutException,
    LLMUnavailableException,
)
from app.services.personality import (
    ANNA_QUOTA_FALLBACK_EMOTION,
    ANNA_QUOTA_FALLBACK_TEXT,
)
from app.services.providers.base import BaseProvider
from app.services.providers.provider_service import ProviderService, is_fallback_eligible
from app.services.providers import set_provider_service


# ---------------------------------------------------------------------------
# Test Helpers & Mock Provider
# ---------------------------------------------------------------------------

class MockProvider(BaseProvider):
    """Configurable mock provider for testing orchestration without network."""

    def __init__(
        self,
        name: str,
        return_value: Tuple[str, str] | None = None,
        side_effect: Exception | None = None,
    ):
        self.name = name
        self.return_value = return_value or (f"Reply from {name}", "happy")
        self.side_effect = side_effect
        self.call_count = 0
        self.last_history = None
        self.last_message = None
        self.last_rag_context = None

    def generate_reply(
        self,
        history: List[Dict[str, Any]],
        message: str,
        rag_context: str | None = None,
    ) -> Tuple[str, str]:
        self.call_count += 1
        self.last_history = history
        self.last_message = message
        self.last_rag_context = rag_context
        if self.side_effect:
            raise self.side_effect
        return self.return_value


class FakeQuotaException(Exception):
    code = 429
    status = "RESOURCE_EXHAUSTED"


def _create_chat(client) -> Tuple[Dict[str, str], str]:
    headers = {"X-Client-Id": str(uuid.uuid4())}
    res = client.post("/api/v1/conversations", headers=headers)
    assert res.status_code == 200
    return headers, res.json()["id"]


# ===========================================================================
# 1. Fallback Eligibility & Unit Tests
# ===========================================================================

class TestFallbackEligibility:

    def test_programming_errors_not_eligible(self):
        assert is_fallback_eligible(TypeError("type mismatch")) is False
        assert is_fallback_eligible(KeyError("missing key")) is False
        assert is_fallback_eligible(IndexError("out of bounds")) is False
        assert is_fallback_eligible(AttributeError("no attr")) is False
        assert is_fallback_eligible(AssertionError("assertion failed")) is False

    def test_quota_and_rate_limits_eligible(self):
        assert is_fallback_eligible(LLMQuotaExhaustedException()) is True
        assert is_fallback_eligible(FakeQuotaException()) is True

    def test_timeouts_eligible(self):
        assert is_fallback_eligible(LLMTimeoutException()) is True
        assert is_fallback_eligible(TimeoutError("timed out")) is True
        assert is_fallback_eligible(Exception("Request deadline exceeded")) is True

    def test_server_and_network_errors_eligible(self):
        assert is_fallback_eligible(LLMUnavailableException("503 Service Unavailable")) is True
        class Fake500(Exception):
            status_code = 500
        assert is_fallback_eligible(Fake500()) is True


# ===========================================================================
# 2. ProviderService Fallback Matrix Tests
# ===========================================================================

class TestProviderServiceFallbackMatrix:

    def test_primary_gemini_succeeds_fallback_not_called(self):
        gemini = MockProvider("gemini", return_value=("Chào bạn từ Gemini!", "happy"))
        groq = MockProvider("groq", return_value=("Chào bạn từ Groq!", "neutral"))
        service = ProviderService(primary_provider=gemini, fallback_provider=groq)

        reply, emotion = service.generate_reply([], "Xin chào")
        assert reply == "Chào bạn từ Gemini!"
        assert emotion == "happy"
        assert gemini.call_count == 1
        assert groq.call_count == 0

    def test_primary_gemini_quota_exhausted_fallback_groq_succeeds(self):
        gemini = MockProvider("gemini", side_effect=FakeQuotaException("Quota exceeded"))
        groq = MockProvider("groq", return_value=("Chào bạn từ Groq sau quota!", "surprised"))
        service = ProviderService(primary_provider=gemini, fallback_provider=groq)

        reply, emotion = service.generate_reply([], "Câu hỏi kiểm tra")
        assert reply == "Chào bạn từ Groq sau quota!"
        assert emotion == "surprised"
        assert gemini.call_count == 1
        assert groq.call_count == 1

    def test_primary_gemini_timeout_fallback_groq_succeeds(self):
        gemini = MockProvider("gemini", side_effect=LLMTimeoutException("Gemini timed out"))
        groq = MockProvider("groq", return_value=("Groq cứu cánh sau timeout!", "happy"))
        service = ProviderService(primary_provider=gemini, fallback_provider=groq)

        reply, emotion = service.generate_reply([], "Câu hỏi kiểm tra")
        assert reply == "Groq cứu cánh sau timeout!"
        assert gemini.call_count == 1
        assert groq.call_count == 1

    def test_primary_gemini_network_5xx_fallback_groq_succeeds(self):
        gemini = MockProvider("gemini", side_effect=LLMUnavailableException("Gemini 500 error"))
        groq = MockProvider("groq", return_value=("Groq trả lời sau 500!", "neutral"))
        service = ProviderService(primary_provider=gemini, fallback_provider=groq)

        reply, emotion = service.generate_reply([], "Câu hỏi kiểm tra")
        assert reply == "Groq trả lời sau 500!"
        assert gemini.call_count == 1
        assert groq.call_count == 1

    def test_primary_groq_succeeds_when_configured_as_primary(self):
        groq = MockProvider("groq", return_value=("Groq là primary!", "happy"))
        gemini = MockProvider("gemini", return_value=("Gemini không được gọi", "neutral"))
        service = ProviderService(primary_provider=groq, fallback_provider=gemini)

        reply, emotion = service.generate_reply([], "Câu hỏi")
        assert reply == "Groq là primary!"
        assert groq.call_count == 1
        assert gemini.call_count == 0

    def test_primary_groq_fails_fallback_gemini_succeeds(self):
        groq = MockProvider("groq", side_effect=LLMTimeoutException("Groq timeout"))
        gemini = MockProvider("gemini", return_value=("Gemini phản hồi khi Groq lỗi!", "happy"))
        service = ProviderService(primary_provider=groq, fallback_provider=gemini)

        reply, emotion = service.generate_reply([], "Câu hỏi")
        assert reply == "Gemini phản hồi khi Groq lỗi!"
        assert groq.call_count == 1
        assert gemini.call_count == 1

    def test_primary_fails_fallback_disabled_raises_original_or_quota(self):
        gemini = MockProvider("gemini", side_effect=LLMUnavailableException("Gemini down"))
        service = ProviderService(primary_provider=gemini, fallback_provider=None)

        with pytest.raises(LLMUnavailableException):
            service.generate_reply([], "Câu hỏi")
        assert gemini.call_count == 1

        # With quota error and no fallback
        gemini_quota = MockProvider("gemini", side_effect=FakeQuotaException("Quota 429"))
        service_quota = ProviderService(primary_provider=gemini_quota, fallback_provider=None)
        with pytest.raises(LLMQuotaExhaustedException):
            service_quota.generate_reply([], "Câu hỏi")

    def test_primary_quota_exhausted_fallback_quota_exhausted_raises_quota_exhausted(self):
        gemini = MockProvider("gemini", side_effect=FakeQuotaException("Gemini quota 429"))
        groq = MockProvider("groq", side_effect=FakeQuotaException("Groq quota 429"))
        service = ProviderService(primary_provider=gemini, fallback_provider=groq)

        with pytest.raises(LLMQuotaExhaustedException):
            service.generate_reply([], "Câu hỏi")
        assert gemini.call_count == 1
        assert groq.call_count == 1

    def test_primary_timeout_fallback_timeout_raises_timeout_exception(self):
        gemini = MockProvider("gemini", side_effect=LLMTimeoutException("Gemini timeout"))
        groq = MockProvider("groq", side_effect=LLMTimeoutException("Groq timeout"))
        service = ProviderService(primary_provider=gemini, fallback_provider=groq)

        with pytest.raises(LLMTimeoutException):
            service.generate_reply([], "Câu hỏi")
        assert gemini.call_count == 1
        assert groq.call_count == 1

    def test_primary_network_failure_fallback_network_failure_raises_unavailable(self):
        gemini = MockProvider("gemini", side_effect=LLMUnavailableException("Gemini 503"))
        groq = MockProvider("groq", side_effect=LLMUnavailableException("Groq 503"))
        service = ProviderService(primary_provider=gemini, fallback_provider=groq)

        with pytest.raises(LLMUnavailableException):
            service.generate_reply([], "Câu hỏi")
        assert gemini.call_count == 1
        assert groq.call_count == 1

    def test_primary_auth_failure_attempts_fallback_when_configured(self):
        """Design choice: Primary authentication failure (missing/invalid key) falls back to secondary provider."""
        gemini = MockProvider("gemini", side_effect=LLMUnavailableException("Chưa cấu hình API Key cho Gemini"))
        groq = MockProvider("groq", return_value=("Groq phản hồi khi Gemini thiếu key!", "happy"))
        service = ProviderService(primary_provider=gemini, fallback_provider=groq)

        reply, emotion = service.generate_reply([], "Câu hỏi")
        assert reply == "Groq phản hồi khi Gemini thiếu key!"
        assert gemini.call_count == 1
        assert groq.call_count == 1

    def test_primary_auth_failure_without_fallback_raises_unavailable(self):
        gemini = MockProvider("gemini", side_effect=LLMUnavailableException("Chưa cấu hình API Key cho Gemini"))
        service = ProviderService(primary_provider=gemini, fallback_provider=None)

        with pytest.raises(LLMUnavailableException) as exc_info:
            service.generate_reply([], "Câu hỏi")
        assert "Chưa cấu hình API Key" in exc_info.value.message
        assert gemini.call_count == 1

    def test_programming_error_does_not_trigger_fallback(self):
        gemini = MockProvider("gemini", side_effect=TypeError("Unhandled null pointer bug"))
        groq = MockProvider("groq", return_value=("Groq không nên được gọi!", "happy"))
        service = ProviderService(primary_provider=gemini, fallback_provider=groq)

        with pytest.raises(TypeError):
            service.generate_reply([], "Câu hỏi")
        assert gemini.call_count == 1
        assert groq.call_count == 0

    def test_rag_context_passed_identically_to_active_provider(self):
        rag_doc = "[Học viện Kỹ thuật Mật mã] Quy chế thi 2026"

        # Case 1: Primary succeeds -> Primary gets RAG doc
        gemini1 = MockProvider("gemini")
        groq1 = MockProvider("groq")
        service1 = ProviderService(gemini1, groq1)
        service1.generate_reply([], "Quy chế thi thế nào?", rag_context=rag_doc)
        assert gemini1.last_rag_context == rag_doc
        assert groq1.call_count == 0

        # Case 2: Primary fails, Fallback succeeds -> Fallback gets exact same RAG doc
        gemini2 = MockProvider("gemini", side_effect=LLMTimeoutException("Gemini timeout"))
        groq2 = MockProvider("groq")
        service2 = ProviderService(gemini2, groq2)
        service2.generate_reply([], "Quy chế thi thế nào?", rag_context=rag_doc)
        assert gemini2.last_rag_context == rag_doc
        assert groq2.last_rag_context == rag_doc


# ===========================================================================
# 3. Route-Level Integration Tests
# ===========================================================================

class TestRouteLevelFallbackOrchestration:

    def test_route_primary_quota_fallback_to_groq_returns_200(self, client, monkeypatch):
        monkeypatch.setattr(routes, "USE_REAL_AI", True)
        gemini = MockProvider("gemini", side_effect=FakeQuotaException("Gemini quota 429"))
        groq = MockProvider("groq", return_value=("Anna trả lời từ Groq mượt mà!", "happy"))
        service = ProviderService(primary_provider=gemini, fallback_provider=groq)
        set_provider_service(service)

        try:
            headers, conv_id = _create_chat(client)
            req_id = str(uuid.uuid4())
            res = client.post(
                f"/api/v1/conversations/{conv_id}/messages",
                headers=headers,
                json={"request_id": req_id, "message": "Giải thích môn Mật mã ứng dụng"},
            )
            assert res.status_code == 200
            data = res.json()
            assert data["assistant_message"]["text"] == "Anna trả lời từ Groq mượt mà!"
            assert data["assistant_message"]["emotion"] == "happy"
            assert gemini.call_count == 1
            assert groq.call_count == 1
        finally:
            set_provider_service(None)

    def test_route_both_providers_quota_exhausted_returns_anna_friendly_fallback(
        self, client, monkeypatch
    ):
        monkeypatch.setattr(routes, "USE_REAL_AI", True)
        gemini = MockProvider("gemini", side_effect=FakeQuotaException("Gemini quota 429"))
        groq = MockProvider("groq", side_effect=FakeQuotaException("Groq quota 429"))
        service = ProviderService(primary_provider=gemini, fallback_provider=groq)
        set_provider_service(service)

        try:
            headers, conv_id = _create_chat(client)
            req_id = str(uuid.uuid4())
            res = client.post(
                f"/api/v1/conversations/{conv_id}/messages",
                headers=headers,
                json={"request_id": req_id, "message": "Câu hỏi trong lúc cả hai hết quota"},
            )
            assert res.status_code == 200
            data = res.json()
            assert data["assistant_message"]["text"] == ANNA_QUOTA_FALLBACK_TEXT
            assert data["assistant_message"]["emotion"] == ANNA_QUOTA_FALLBACK_EMOTION
            assert data["sources"] == []
            assert gemini.call_count == 1
            assert groq.call_count == 1
        finally:
            set_provider_service(None)

    def test_route_quick_replies_bypass_both_providers(self, client, monkeypatch):
        monkeypatch.setattr(routes, "USE_REAL_AI", True)
        gemini = MockProvider("gemini", return_value=("Không được gọi", "neutral"))
        groq = MockProvider("groq", return_value=("Không được gọi", "neutral"))
        service = ProviderService(primary_provider=gemini, fallback_provider=groq)
        set_provider_service(service)

        try:
            headers, conv_id = _create_chat(client)
            req_id = str(uuid.uuid4())
            res = client.post(
                f"/api/v1/conversations/{conv_id}/messages",
                headers=headers,
                json={"request_id": req_id, "message": "xin chào"},
            )
            assert res.status_code == 200
            data = res.json()
            assert "Anna" in data["assistant_message"]["text"]
            assert data["assistant_message"]["emotion"] == "happy"
            # Both providers bypassed!
            assert gemini.call_count == 0
            assert groq.call_count == 0
        finally:
            set_provider_service(None)

    def test_route_idempotency_replay_returns_cached_response_without_calling_providers_again(
        self, client, monkeypatch
    ):
        monkeypatch.setattr(routes, "USE_REAL_AI", True)
        gemini = MockProvider("gemini", return_value=("Câu trả lời một lần duy nhất!", "happy"))
        groq = MockProvider("groq")
        service = ProviderService(primary_provider=gemini, fallback_provider=groq)
        set_provider_service(service)

        try:
            headers, conv_id = _create_chat(client)
            req_id = str(uuid.uuid4())
            msg_payload = {"request_id": req_id, "message": "Thử nghiệm idempotency"}

            # First call -> Gemini generates reply
            res1 = client.post(f"/api/v1/conversations/{conv_id}/messages", headers=headers, json=msg_payload)
            assert res1.status_code == 200
            assert gemini.call_count == 1

            # Second call with same request_id -> Replay from database
            res2 = client.post(f"/api/v1/conversations/{conv_id}/messages", headers=headers, json=msg_payload)
            assert res2.status_code == 200
            assert res2.json() == res1.json()
            assert gemini.call_count == 1  # Not called again!
            assert groq.call_count == 0
        finally:
            set_provider_service(None)

    def test_route_both_providers_timeout_returns_504(self, client, monkeypatch):
        monkeypatch.setattr(routes, "USE_REAL_AI", True)
        gemini = MockProvider("gemini", side_effect=LLMTimeoutException("Gemini timed out"))
        groq = MockProvider("groq", side_effect=LLMTimeoutException("Groq timed out"))
        service = ProviderService(primary_provider=gemini, fallback_provider=groq)
        set_provider_service(service)

        try:
            headers, conv_id = _create_chat(client)
            req_id = str(uuid.uuid4())
            res = client.post(
                f"/api/v1/conversations/{conv_id}/messages",
                headers=headers,
                json={"request_id": req_id, "message": "Câu hỏi bị timeout"},
            )
            assert res.status_code == 504
            data = res.json()
            assert data["error"]["code"] == "LLM_TIMEOUT"
            assert gemini.call_count == 1
            assert groq.call_count == 1
        finally:
            set_provider_service(None)
