"""Mock AI Service for Milestone 3.

Provides a predictable Vietnamese reply and a valid emotion.
Designed behind the standard interface `generate_reply(context, message) -> (reply, emotion)`
so Member D can easily replace this implementation with a real LLM API call in subsequent milestones.
"""

from typing import Any, Dict, List, Tuple
from app.exceptions import LLMTimeoutException, LLMUnavailableException

VALID_EMOTIONS = {"neutral", "happy", "sad", "surprised"}


def generate_reply(context: List[Dict[str, Any]], message: str) -> Tuple[str, str]:
    """Generate a predictable Vietnamese assistant reply and emotion.

    Args:
        context: List of at most 10 recent messages from this conversation,
                 ordered from oldest to newest. Each item has 'role', 'text', 'emotion'.
        message: The normalized incoming user message.

    Returns:
        Tuple[str, str]: (reply_text, emotion) where emotion is one of
                         ('neutral', 'happy', 'sad', 'surprised').

    Raises:
        LLMUnavailableException: Simulated AI failure (503).
        LLMTimeoutException: Simulated AI timeout (504).
    """
    # Special hooks for automated error and timeout testing
    if "__TEST_FAIL_AI__" in message:
        raise LLMUnavailableException("Không thể kết nối AI")
    if "__TEST_TIMEOUT__" in message:
        raise LLMTimeoutException("Yêu cầu xử lý AI quá thời gian chờ")

    clean_text = message.strip()
    lower_text = clean_text.lower()

    # Rule-based predictable replies for Android UI & Character testing
    if any(k in lower_text for k in ["buồn", "khóc", "tệ", "chán", "thất vọng", "đau"]):
        return (
            "Mình rất tiếc khi nghe điều đó. Đừng buồn nhé, mình luôn ở đây lắng nghe bạn!",
            "sad",
        )
    elif any(k in lower_text for k in ["chào", "hello", "hi", "vui", "tuyệt", "cảm ơn", "thanks", "khoẻ không"]):
        return (
            "Chào bạn! Rất vui được gặp bạn hôm nay. Mình có thể giúp gì cho bạn?",
            "happy",
        )
    elif any(k in lower_text for k in ["thật sao", "bất ngờ", "sao cơ", "wow", "ngạc nhiên", "thật á"]):
        return (
            "Thật bất ngờ! Bạn có muốn tìm hiểu thêm chi tiết về vấn đề này không?",
            "surprised",
        )
    else:
        snippet = (clean_text[:25] + "...") if len(clean_text) > 25 else clean_text
        return (
            f"Mình đã nhận được tin nhắn của bạn về '{snippet}'. Mình sẵn sàng hỗ trợ bạn!",
            "neutral",
        )
