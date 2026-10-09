"""Provider orchestration service implementing primary generation and fallback policy."""

import logging
from typing import Any, Dict, List, Tuple

import httpx

from app.exceptions import (
    APIException,
    LLMQuotaExhaustedException,
    LLMTimeoutException,
    LLMUnavailableException,
    is_quota_exhausted_exception,
)
from app.services.providers.base import BaseProvider
from app.services.providers.config import ProviderConfig, read_provider_config
from app.services.providers.gemini_provider import GeminiProvider
from app.services.providers.groq_provider import GroqProvider

# Programming errors that must never trigger fallback
_NON_FALLBACK_TYPES = (
    TypeError,
    KeyError,
    IndexError,
    AttributeError,
    NameError,
    NotImplementedError,
    AssertionError,
)


def is_fallback_eligible(exc: Exception) -> bool:
    """Determine if a primary provider failure is eligible for fallback to secondary provider."""
    # Programming bugs must not trigger fallback
    if isinstance(exc, _NON_FALLBACK_TYPES):
        return False

    # Quota / rate limit (429, RESOURCE_EXHAUSTED)
    if is_quota_exhausted_exception(exc):
        return True

    # Timeout
    if isinstance(exc, (LLMTimeoutException, TimeoutError)):
        return True
    error_msg = str(exc).lower()
    if "timeout" in error_msg or "timed out" in error_msg or "deadline exceeded" in error_msg:
        return True

    # Network / connection failure
    if isinstance(exc, (httpx.ConnectError, httpx.NetworkError, httpx.ConnectTimeout)):
        return True

    # Provider HTTP status codes (429, 500, 502, 503, 504)
    code = getattr(exc, "status_code", None) or getattr(exc, "code", None)
    if code in {429, 500, 502, 503, 504}:
        return True

    # Controlled provider unavailable exception (e.g. LLMUnavailableException)
    if isinstance(exc, LLMUnavailableException):
        return True

    # Check for Groq-specific exception classes if groq is imported
    try:
        import groq
        if isinstance(
            exc,
            (
                groq.RateLimitError,
                groq.APITimeoutError,
                groq.APIConnectionError,
                groq.InternalServerError,
                groq.APIStatusError,
            ),
        ):
            return True
    except ImportError:
        pass

    return False


class ProviderService:
    """Orchestrates LLM generation across primary and fallback providers."""

    def __init__(
        self,
        primary_provider: BaseProvider,
        fallback_provider: BaseProvider | None = None,
        total_timeout_ms: int = 55000,
    ):
        self.primary_provider = primary_provider
        self.fallback_provider = fallback_provider
        self.total_timeout_ms = total_timeout_ms

    def generate_reply(
        self,
        history: List[Dict[str, Any]],
        message: str,
        rag_context: str | None = None,
    ) -> Tuple[str, str]:
        """Generate response via primary provider, falling back to secondary if eligible."""
        primary_exc: Exception | None = None

        try:
            return self.primary_provider.generate_reply(history, message, rag_context)
        except Exception as exc:
            primary_exc = exc

        # Primary failed. Check if fallback should be attempted.
        if not is_fallback_eligible(primary_exc) or self.fallback_provider is None:
            if is_quota_exhausted_exception(primary_exc):
                raise LLMQuotaExhaustedException("AI quota exhausted on primary provider") from primary_exc
            raise primary_exc

        # Attempt fallback
        logging.warning(
            f"Primary provider '{self.primary_provider.name}' failed with {type(primary_exc).__name__}; "
            f"attempting fallback '{self.fallback_provider.name}'"
        )

        try:
            result = self.fallback_provider.generate_reply(history, message, rag_context)
            logging.info(f"Fallback provider '{self.fallback_provider.name}' succeeded.")
            return result
        except Exception as fallback_exc:
            logging.error(
                f"Fallback provider '{self.fallback_provider.name}' failed with {type(fallback_exc).__name__}"
            )

            # Both usable providers failed. Determine final outcome according to policy:
            # 1. At least one confirmed quota exhaustion -> Anna friendly quota fallback (sad)
            if is_quota_exhausted_exception(primary_exc) or is_quota_exhausted_exception(fallback_exc):
                raise LLMQuotaExhaustedException("AI quota exhausted across usable providers") from fallback_exc

            # 2. Both providers timed out -> controlled timeout (504)
            p_timeout = isinstance(primary_exc, (LLMTimeoutException, TimeoutError)) or "timeout" in str(primary_exc).lower()
            f_timeout = isinstance(fallback_exc, (LLMTimeoutException, TimeoutError)) or "timeout" in str(fallback_exc).lower()

            if p_timeout and f_timeout:
                raise LLMTimeoutException("Yêu cầu xử lý AI quá thời gian chờ trên toàn bộ provider") from fallback_exc

            # 3. Either provider timed out
            if f_timeout or p_timeout:
                cause = fallback_exc if f_timeout else primary_exc
                raise LLMTimeoutException("Yêu cầu xử lý AI quá thời gian chờ") from cause


            # 4. Controlled service unavailable
            if isinstance(fallback_exc, APIException):
                raise fallback_exc
            raise LLMUnavailableException("Không thể kết nối AI trên toàn bộ provider.") from fallback_exc


def create_provider(name: str, config: ProviderConfig) -> BaseProvider:
    """Factory creating provider instance from configuration."""
    if name == "gemini":
        return GeminiProvider(
            api_key=config.gemini_api_key,
            model=config.gemini_model,
            timeout_ms=config.gemini_generation_timeout_ms,
        )
    elif name == "groq":
        return GroqProvider(
            api_key=config.groq_api_key,
            model=config.groq_model or "openai/gpt-oss-120b",
            timeout_ms=config.groq_timeout_ms,
        )
    raise ValueError(f"Unknown provider name: '{name}'")


def build_provider_service(config: ProviderConfig) -> ProviderService:
    """Build ProviderService from validated ProviderConfig."""
    primary = create_provider(config.primary_provider, config)
    fallback = create_provider(config.fallback_provider, config) if config.fallback_provider else None
    return ProviderService(
        primary_provider=primary,
        fallback_provider=fallback,
        total_timeout_ms=config.ai_total_timeout_ms,
    )
