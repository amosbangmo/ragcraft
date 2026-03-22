"""Streamlit-scoped chat message list (or equivalent) for UI transcript state."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class ChatTranscriptPort(Protocol):
    def init(self, project_key: str) -> None: ...

    def get_messages(self) -> list[dict]: ...

    def add_user_message(self, content: str) -> None: ...

    def add_assistant_message(self, content: str) -> None: ...
