import json
import logging
from typing import List, Dict, Tuple

# Sử dụng SDK chính thức của Google thay cho OpenAI
from google import genai
from google.genai import types

from app.config import GEMINI_API_KEY, GEMINI_MODEL, GEMINI_GENERATION_TIMEOUT_MS
from app.exceptions import (
    LLMUnavailableException,
    LLMTimeoutException,
    LLMQuotaExhaustedException,
    is_quota_exhausted_exception,
)
from app.services.personality import (
    ANNA_SYSTEM_PROMPT,
    ALLOWED_EMOTIONS,
    normalize_emotion,
)

# Only create a Google GenAI client when a Gemini key is configured.
client = genai.Client(
    api_key=GEMINI_API_KEY,
    http_options=types.HttpOptions(api_version="v1", timeout=GEMINI_GENERATION_TIMEOUT_MS),
) if GEMINI_API_KEY else None

SYSTEM_PROMPT = ANNA_SYSTEM_PROMPT


def generate_reply(
    context: List[Dict[str, str]], message: str, rag_context: str | None = None
) -> Tuple[str, str]:
    if not client:
        raise LLMUnavailableException("Chưa cấu hình API Key cho LLM.")

    try:
        # 1. Chuyển đổi lịch sử chat (context) sang định dạng của Google GenAI
        contents = []
        for msg in context:
            # Map role: Backend lưu là 'assistant', nhưng Google quy định là 'model'
            role = "model" if msg.get("role") == "assistant" else "user"
            contents.append(
                types.Content(role=role, parts=[types.Part.from_text(text=msg.get("text", ""))])
            )

        # 2. Thêm tin nhắn hiện tại của người dùng vào cuối
        contents.append(
            types.Content(role="user", parts=[types.Part.from_text(text=message)])
        )

        # 3. Gọi API với cấu hình ép kiểu trả về JSON và truyền System Prompt
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=(
                    f"{SYSTEM_PROMPT}\n\n{rag_context}" if rag_context else SYSTEM_PROMPT
                ),
                response_mime_type="application/json",
            ),
        )

        # 4. Parse kết quả trả về
        result_json = json.loads(response.text)
        reply = result_json.get("reply")

        # Bắt buộc phải có reply hợp lệ, nếu không thì báo lỗi hệ thống
        if not reply or not isinstance(reply, str) or not reply.strip():
            raise LLMUnavailableException("LLM trả về câu trả lời rỗng hoặc không hợp lệ.")

        emotion = normalize_emotion(result_json.get("emotion"))

        return reply.strip(), emotion

    except json.JSONDecodeError:
        logging.error("[AI Service Error] Malformed JSON response.")
        raise LLMUnavailableException("Dữ liệu LLM trả về không đúng định dạng.")
    except Exception as e:
        if is_quota_exhausted_exception(e):
            logging.warning("[AI Service Error] Provider quota or rate limit exhausted.")
            raise LLMQuotaExhaustedException("AI quota exhausted")
        error_msg = str(e).lower()
        if isinstance(e, TimeoutError) or "timeout" in error_msg or "timed out" in error_msg:
            logging.error("[AI Service Error] Request timed out.")
            raise LLMTimeoutException("Không thể kết nối AI do quá thời gian.")
        else:
            logging.error(f"[AI Service Error] API failed: {type(e).__name__}")
            raise LLMUnavailableException("Không thể kết nối AI.")
