import os
import json
import time
from typing import List, Dict, Tuple
from openai import OpenAI

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")

client = OpenAI(api_key=OPENAI_API_KEY, timeout=30.0) if OPENAI_API_KEY else None
ALLOWED_EMOTIONS = ["neutral", "happy", "sad", "surprised"]

SYSTEM_PROMPT = """Bạn là một trợ lý ảo trên điện thoại Android, có hình dáng một nhân vật anime.
Hãy trả lời bằng tiếng Việt một cách tự nhiên, ngắn gọn và rõ ràng.
Tuyệt đối không tự nhận là đã thực hiện các thao tác trên điện thoại hay laptop vì bạn chưa được cung cấp công cụ (tool) để làm việc đó.
Phản hồi của bạn BẮT BUỘC phải là một JSON hợp lệ với 2 trường:
- "reply": Nội dung câu trả lời.
- "emotion": Cảm xúc của bạn, CHỈ ĐƯỢC CHỌN MỘT TRONG CÁC TỪ SAU: "neutral", "happy", "sad", "surprised".
"""

def generate_reply(context: List[Dict[str, str]], message: str) -> Tuple[str, str]:
    if not client:
        time.sleep(1)
        print("[AI Service] CẢNH BÁO: Đang chạy Mock AI vì không tìm thấy OPENAI_API_KEY.")
        return "Xin chào, đây là tin nhắn từ chế độ Mock AI.", "happy"

    try:
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        for msg in context:
            messages.append({"role": msg.get("role", "user"), "content": msg.get("content", "")})
        messages.append({"role": "user", "content": message})

        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=messages,
            response_format={ "type": "json_object" }, 
            timeout=30.0
        )

        result_json = json.loads(response.choices[0].message.content)
        reply = result_json.get("reply", "Tôi không có câu trả lời.")
        emotion = result_json.get("emotion", "neutral").lower()

        if emotion not in ALLOWED_EMOTIONS:
            emotion = "neutral"

        return reply, emotion

    except Exception as e:
        print(f"[AI Service Error] Lỗi kết nối LLM: {str(e)}")
        raise Exception("LLM_UNAVAILABLE")

if __name__ == "__main__":
    r, e = generate_reply([], "Xin chào!")
    print(f"Reply: {r}\nEmotion: {e}")