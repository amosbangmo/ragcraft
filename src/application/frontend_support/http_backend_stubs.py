"""
Placeholders attached to :class:`~src.frontend_gateway.http_client.HttpBackendClient` when the UI
runs against the API: chat transcripts stay in Streamlit while RAG hits REST.

Kept under ``src.application`` so ``src.frontend_gateway`` does not import
``src.infrastructure`` directly (architecture guardrails).
"""

from __future__ import annotations

from typing import Any

from src.domain.project_settings import ProjectSettings
from src.domain.ports.chat_transcript_port import ChatTranscriptPort
from src.domain.ports.retrieval_preset_merge_port import RetrievalPresetMergePort
from src.domain.shared.project_settings_repository_port import ProjectSettingsRepositoryPort


class _UnsupportedBackendAttribute:
    __slots__ = ("_name",)

    def __init__(self, name: str) -> None:
        self._name = name

    def __getattr__(self, item: str) -> Any:
        raise NotImplementedError(
            f"{self._name}.{item} is not available when using the HTTP backend client. "
            "Use the corresponding REST endpoint via HttpBackendClient methods."
        )


class _UnsupportedProjectSettingsRepository:
    def load(self, user_id: str, project_id: str) -> ProjectSettings:
        raise NotImplementedError(
            "project_settings_repository.load is not available over HTTP; use GET /projects/.../retrieval-settings."
        )

    def save(self, settings: ProjectSettings) -> None:
        raise NotImplementedError(
            "project_settings_repository.save is not available over HTTP; use PUT /projects/.../retrieval-settings."
        )


def http_client_chat_service() -> ChatTranscriptPort:
    """Chat transcript lives in Streamlit ``session_state`` even when RAG runs on the API."""
    from src.frontend_gateway.streamlit_chat_transcript import ChatService

    return ChatService()


def http_client_retrieval_settings_service() -> RetrievalPresetMergePort:
    """Pure preset/merge helpers without persisting (persistence goes through the API)."""
    from src.application.settings.retrieval_settings_tuner import RetrievalSettingsTuner

    return RetrievalSettingsTuner()


def http_client_project_settings_repository() -> ProjectSettingsRepositoryPort:
    return _UnsupportedProjectSettingsRepository()  # type: ignore[return-value]


def http_client_rag_service() -> Any:
    return _UnsupportedBackendAttribute("rag_service")


def http_client_evaluation_service() -> Any:
    return _UnsupportedBackendAttribute("evaluation_service")
