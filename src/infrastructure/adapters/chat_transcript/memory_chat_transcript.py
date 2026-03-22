"""Process-local in-memory chat transcript (API / tests; no Streamlit)."""

from __future__ import annotations

from src.domain.chat_message import ChatMessage


class MemoryChatTranscript:
    """Implements :class:`~src.domain.ports.chat_transcript_port.ChatTranscriptPort` without UI dependencies."""

    def __init__(self) -> None:
        self._messages: list[dict] = []
        self._project_key: str | None = None

    def init(self, project_key: str) -> None:
        if self._project_key != project_key:
            self._messages = []
            self._project_key = project_key

    def get_messages(self) -> list[dict]:
        return list(self._messages)

    def add_user_message(self, content: str) -> None:
        self._messages.append(ChatMessage(role="user", content=content).__dict__)

    def add_assistant_message(self, content: str) -> None:
        self._messages.append(ChatMessage(role="assistant", content=content).__dict__)
