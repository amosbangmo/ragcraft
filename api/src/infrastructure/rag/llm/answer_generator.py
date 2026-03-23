"""
LangChain chat model adapter for answer text generation.

Compatible with :class:`domain.common.shared.language_model_gateway.LanguageModelGateway` (``invoke``).
"""

from __future__ import annotations

from typing import Any


class LLMAnswerGenerator:
    def __init__(self, chat_model: Any) -> None:
        self._chat = chat_model

    def invoke(self, prompt: str) -> Any:
        return self._chat.invoke(prompt)

    def generate_answer_text(self, prompt: str) -> str:
        response = self.invoke(prompt)
        return getattr(response, "content", str(response)).strip()
