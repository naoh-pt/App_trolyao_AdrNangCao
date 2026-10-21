"""Groq chat generation provider using official Groq Python SDK."""

import json
import logging
from typing import Any, Dict, List, Tuple

import groq

from app.exceptions import (
    LLMQuotaExhaustedException,
    LLMTimeoutException,
    LLMUnavailableException,
    is_quota_exhausted_exception,
)
from app.services.personality import ANNA_SYSTEM_PROMPT, normalize_emotion
from app.services.memory_context import provider_system_prompt
from app.services.providers.base import BaseProvider


class GroqProvider(BaseProvider):
    """Groq LLM generation provider."""

    name = "groq"

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "openai/gpt-oss-120b",
        timeout_ms: int = 15000,
        client: Any = None,
    ):
        self.api_key = api_key
        self.model = model
        self.timeout_ms = timeout_ms
        self._client = client

    def get_client(self) -> Any:
        """Return initialized Groq client or lazily construct one."""
        if self._client is not None:
            return self._client

        if not self.api_key:
            raise LLMUnavailableException("Chưa cấu hình API Key cho Groq.")

        self._client = groq.Groq(
            api_key=self.api_key,
            timeout=float(self.timeout_ms) / 1000.0,
            max_retries=0,
        )
        return self._client

    def generate_reply(
        self,
        history: List[Dict[str, Any]],
        message: str,
        rag_context: str | None = None,
    ) -> Tuple[str, str]:
        """Generate response via Groq API using Anna prompt and structured JSON."""
        client = self.get_client()

        try:
            system_instruction = provider_system_prompt(rag_context)

            messages = [{"role": "system", "content": system_instruction}]

            for msg in history:
                role = "assistant" if msg.get("role") == "assistant" else "user"
                messages.append({"role": role, "content": msg.get("text", "")})

            messages.append({"role": "user", "content": message})

            response = client.chat.completions.create(
                model=self.model,
                messages=messages,
                response_format={"type": "json_object"},
            )

            if not response.choices:
                raise LLMUnavailableException("Groq không trả về kết quả.")

            choice = response.choices[0]
            raw_text = choice.message.content

            if not raw_text or not isinstance(raw_text, str) or not raw_text.strip():
                raise LLMUnavailableException("Groq trả về câu trả lời rỗng hoặc không hợp lệ.")

            result_json = json.loads(raw_text)
            reply = result_json.get("reply")

            if not reply or not isinstance(reply, str) or not reply.strip():
                raise LLMUnavailableException("Groq trả về câu trả lời rỗng hoặc không hợp lệ.")

            emotion = normalize_emotion(result_json.get("emotion"))
            return reply.strip(), emotion

        except json.JSONDecodeError:
            logging.error("[Groq Provider Error] Malformed JSON response.")
            raise LLMUnavailableException("Dữ liệu Groq trả về không đúng định dạng.")
        except (LLMUnavailableException, LLMTimeoutException, LLMQuotaExhaustedException):
            raise
        except Exception as e:
            if is_quota_exhausted_exception(e) or isinstance(e, groq.RateLimitError):
                logging.warning("[Groq Provider Error] Quota or rate limit exhausted.")
                raise LLMQuotaExhaustedException("Groq quota/rate-limit exhausted")
            error_msg = str(e).lower()
            if isinstance(e, (TimeoutError, groq.APITimeoutError)) or "timeout" in error_msg or "timed out" in error_msg:
                logging.error("[Groq Provider Error] Request timed out.")
                raise LLMTimeoutException("Yêu cầu xử lý Groq quá thời gian chờ")
            elif isinstance(e, (groq.AuthenticationError, groq.PermissionDeniedError)):
                logging.error(f"[Groq Provider Error] Authentication failed: {type(e).__name__}")
                raise LLMUnavailableException("Xác thực Groq thất bại")
            elif isinstance(e, groq.APIConnectionError):
                logging.error(f"[Groq Provider Error] Connection failed: {type(e).__name__}")
                raise LLMUnavailableException("Lỗi kết nối tới Groq")
            elif isinstance(e, groq.InternalServerError):
                logging.error(f"[Groq Provider Error] Internal server error: {type(e).__name__}")
                raise LLMUnavailableException("Máy chủ Groq tạm thời không khả dụng")
            else:
                logging.error(f"[Groq Provider Error] API failed: {type(e).__name__}")
                raise LLMUnavailableException("Không thể kết nối Groq")
