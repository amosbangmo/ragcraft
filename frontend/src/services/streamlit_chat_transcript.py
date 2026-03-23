"""Streamlit session–backed chat transcript (UI delivery; not an infrastructure adapter)."""

from __future__ import annotations

import streamlit as st

from domain.rag.chat_message import ChatMessage


class StreamlitChatTranscript:
    """Implements :class:`~domain.common.ports.chat_transcript_port.ChatTranscriptPort` via Streamlit session state."""

    MESSAGE_KEY = "messages"
    PROJECT_KEY = "chat_project_key"

    def init(self, project_key: str) -> None:
        if self.MESSAGE_KEY not in st.session_state:
            st.session_state[self.MESSAGE_KEY] = []

        if self.PROJECT_KEY not in st.session_state:
            st.session_state[self.PROJECT_KEY] = project_key

        if st.session_state[self.PROJECT_KEY] != project_key:
            st.session_state[self.MESSAGE_KEY] = []
            st.session_state[self.PROJECT_KEY] = project_key

    def get_messages(self) -> list[dict]:
        return st.session_state.get(self.MESSAGE_KEY, [])

    def add_user_message(self, content: str) -> None:
        st.session_state[self.MESSAGE_KEY].append(
            ChatMessage(role="user", content=content).__dict__
        )

    def add_assistant_message(self, content: str) -> None:
        st.session_state[self.MESSAGE_KEY].append(
            ChatMessage(role="assistant", content=content).__dict__
        )
