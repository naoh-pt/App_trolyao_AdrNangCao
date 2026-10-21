"""Gemini chat generation provider using official Google GenAI SDK."""

import json
import logging
from typing import Any, Dict, List, Tuple

from google import genai
from google.genai import types

from app.exceptions import (
    LLMQuotaExhaustedException,
    LLMTimeoutException,
    LLMUnavailableException,
    is_quota_exhausted_exception,
)
from app.services.personality import ANNA_SYSTEM_PROMPT, normalize_emotion
from app.services.memory_context import provider_system_prompt
from app.services.providers.base import BaseProvider


class GeminiProvider(BaseProvider):
    """Google Gemini LLM generation provider."""

    name = "gemini"

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "gemini-3.5-flash",
        timeout_ms: int = 28000,
        client: Any = None,
    ):
        self.api_key = api_key
        self.model = model
        self.timeout_ms = timeout_ms
        self._client = client

    def get_client(self) -> Any:
        """Return initialized client or lazily construct one."""
        if self._client is not None:
            return self._client

        # Backward compatibility with existing tests that patch ai_service.client
        try:
            import ai_service
            if getattr(ai_service, "client", None) is not None:
                return ai_service.client
        except ImportError:
            pass

        if not self.api_key:
            raise LLMUnavailableException("Chưa cấu hình API Key cho Gemini.")

        self._client = genai.Client(
            api_key=self.api_key,
            http_options=types.HttpOptions(
                api_version="v1",
                timeout=self.timeout_ms,
                retry_options=types.HttpRetryOptions(attempts=1),
            ),
        )
        return self._client

    def generate_reply(
        self,
        history: List[Dict[str, Any]],
        message: str,
        rag_context: str | None = None,
    ) -> Tuple[str, str]:
        """Generate response via Gemini API using Anna prompt and structured JSON."""
        client = self.get_client()

        try:
            contents = []
            for msg in history:
                role = "model" if msg.get("role") == "assistant" else "user"
                contents.append(
                    types.Content(role=role, parts=[types.Part.from_text(text=msg.get("text", ""))])
                )

            contents.append(
                types.Content(role="user", parts=[types.Part.from_text(text=message)])
            )

            system_instruction = provider_system_prompt(rag_context)

            response = client.models.generate_content(
                model=self.model,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    response_mime_type="application/json",
                ),
            )

            result_json = json.loads(response.text)
            reply = result_json.get("reply")

            if not reply or not isinstance(reply, str) or not reply.strip():
                raise LLMUnavailableException("LLM trả về câu trả lời rỗng hoặc không hợp lệ.")

            emotion = normalize_emotion(result_json.get("emotion"))
            return reply.strip(), emotion

        except json.JSONDecodeError:
            logging.error("[Gemini Provider Error] Malformed JSON response.")
            raise LLMUnavailableException("Dữ liệu LLM trả về không đúng định dạng.")
        except (LLMUnavailableException, LLMTimeoutException, LLMQuotaExhaustedException):
            raise
        except Exception as e:
            if is_quota_exhausted_exception(e):
                logging.warning("[Gemini Provider Error] Quota or rate limit exhausted.")
                raise LLMQuotaExhaustedException("AI quota exhausted")
            error_msg = str(e).lower()
            if isinstance(e, TimeoutError) or "timeout" in error_msg or "timed out" in error_msg:
                logging.error("[Gemini Provider Error] Request timed out.")
                raise LLMTimeoutException("Không thể kết nối AI do quá thời gian.")
            else:
                logging.error(f"[Gemini Provider Error] API failed: {type(e).__name__}")
                raise LLMUnavailableException("Không thể kết nối AI.")
