"""AI generation service delegating to the provider orchestration service."""

from typing import Dict, List, Tuple

from google import genai
from google.genai import types

from app.config import (
    GEMINI_API_KEY,
    GEMINI_GENERATION_TIMEOUT_MS,
    GEMINI_MODEL,
)
from app.exceptions import (
    LLMQuotaExhaustedException,
    LLMTimeoutException,
    LLMUnavailableException,
    is_quota_exhausted_exception,
)
from app.services.personality import (
    ALLOWED_EMOTIONS,
    ANNA_SYSTEM_PROMPT,
    normalize_emotion,
)
from app.services.providers import get_provider_service

# Only create a Google GenAI client when a Gemini key is configured.
client = genai.Client(
    api_key=GEMINI_API_KEY,
    http_options=types.HttpOptions(
        api_version="v1",
        timeout=GEMINI_GENERATION_TIMEOUT_MS,
        retry_options=types.HttpRetryOptions(attempts=1),
    ),
) if GEMINI_API_KEY else None

SYSTEM_PROMPT = ANNA_SYSTEM_PROMPT


def generate_reply(
    context: List[Dict[str, str]], message: str, rag_context: str | None = None
) -> Tuple[str, str]:
    """Generate chat reply via provider service with primary/fallback orchestration."""
    provider_service = get_provider_service()
    return provider_service.generate_reply(context, message, rag_context)
