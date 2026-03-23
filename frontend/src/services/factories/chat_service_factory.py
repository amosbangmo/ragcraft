"""Construct Streamlit session–backed chat transcript for in-process backend wiring."""

from __future__ import annotations

from typing import TypeAlias

from domain.common.ports.chat_transcript_port import ChatTranscriptPort
from services.streamlit_chat_transcript import StreamlitChatTranscript

ChatService: TypeAlias = StreamlitChatTranscript


def build_chat_service() -> ChatService:
    """Return the Streamlit-backed transcript implementation (``ChatTranscriptPort``)."""
    return StreamlitChatTranscript()


__all__ = ["ChatService", "build_chat_service"]
