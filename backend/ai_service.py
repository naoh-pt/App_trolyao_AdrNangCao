import json
import logging
from typing import List, Dict, Tuple

# Sử dụng SDK chính thức của Google thay cho OpenAI
from google import genai
from google.genai import types

from app.config import GEMINI_API_KEY, GEMINI_MODEL, GEMINI_TIMEOUT_MS
from app.exceptions import LLMUnavailableException, LLMTimeoutException

# Only create a Google GenAI client when a Gemini key is configured.
client = genai.Client(
    api_key=GEMINI_API_KEY,
    http_options=types.HttpOptions(api_version="v1", timeout=GEMINI_TIMEOUT_MS),
) if GEMINI_API_KEY else None

ALLOWED_EMOTIONS = ["neutral", "happy", "sad", "surprised"]

SYSTEM_PROMPT = """Bạn là một trợ lý ảo trên điện thoại Android, có hình dáng một nhân vật anime.
Hãy trả lời bằng tiếng Việt một cách tự nhiên, ngắn gọn và rõ ràng.
Tuyệt đối không tự nhận là đã thực hiện các thao tác trên điện thoại hay laptop vì bạn chưa được cung cấp công cụ (tool) để làm việc đó.
Phản hồi của bạn BẮT BUỘC phải là một JSON hợp lệ với 2 trường:
- "reply": Nội dung câu trả lời.
- "emotion": Cảm xúc của bạn, CHỈ ĐƯỢC CHỌN MỘT TRONG CÁC TỪ SAU: "neutral", "happy", "sad", "surprised".
"""

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
            )
        )

        # 4. Parse kết quả trả về
        result_json = json.loads(response.text)
        reply = result_json.get("reply")

        # Bắt buộc phải có reply hợp lệ, nếu không thì báo lỗi hệ thống
        if not reply or not isinstance(reply, str) or not reply.strip():
            raise LLMUnavailableException("LLM trả về câu trả lời rỗng hoặc không hợp lệ.")

        emotion = result_json.get("emotion")
        if not isinstance(emotion, str) or emotion.lower() not in ALLOWED_EMOTIONS:
            emotion = "neutral"

        return reply.strip(), emotion.lower()

    except json.JSONDecodeError:
        logging.error("[AI Service Error] Malformed JSON response.")
        raise LLMUnavailableException("Dữ liệu LLM trả về không đúng định dạng.")
    except Exception as e:
        error_msg = str(e).lower()
        if "timeout" in error_msg or "timed out" in error_msg:
            logging.error("[AI Service Error] Request timed out.")
            raise LLMTimeoutException("Không thể kết nối AI do quá thời gian.")
        else:
            logging.error(f"[AI Service Error] API failed: {str(e)}")
            raise LLMUnavailableException("Không thể kết nối AI.")
