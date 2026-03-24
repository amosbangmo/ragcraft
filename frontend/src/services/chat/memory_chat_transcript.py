"""In-memory chat transcript for HTTP-backed Streamlit (no domain types)."""

from __future__ import annotations


class MemoryChatTranscript:
    def __init__(self) -> None:
        self._messages: list[dict[str, str]] = []
        self._project_key: str | None = None

    def init(self, project_key: str) -> None:
        if self._project_key != project_key:
            self._messages = []
            self._project_key = project_key

    def get_messages(self) -> list[dict[str, str]]:
        return list(self._messages)

    def add_user_message(self, content: str) -> None:
        self._messages.append({"role": "user", "content": content})

    def add_assistant_message(self, content: str) -> None:
        self._messages.append({"role": "assistant", "content": content})
