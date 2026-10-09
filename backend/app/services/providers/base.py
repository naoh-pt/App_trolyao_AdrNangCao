"""Base class for virtual assistant chat generation providers."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Tuple


class BaseProvider(ABC):
    """Abstract base class for LLM chat generation providers."""

    name: str

    @abstractmethod
    def generate_reply(
        self,
        history: List[Dict[str, Any]],
        message: str,
        rag_context: str | None = None,
    ) -> Tuple[str, str]:
        """Generate a reply and normalized emotion.

        Args:
            history: List of recent conversation messages (ordered oldest to newest).
            message: Current normalized user message.
            rag_context: Optional retrieved knowledge context string.

        Returns:
            Tuple[str, str]: (reply_text, normalized_emotion)
        """
        raise NotImplementedError
