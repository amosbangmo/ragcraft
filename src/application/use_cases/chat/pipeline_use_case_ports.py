"""Protocols for chat/RAG use cases used by evaluation and retrieval comparison (avoid concrete imports)."""

from __future__ import annotations

from typing import Any, Protocol

from src.domain.pipeline_payloads import PipelineBuildResult
from src.domain.project import Project
from src.domain.retrieval_filters import RetrievalFilters


class InspectRagPipelinePort(Protocol):
    """Read-only pipeline build for inspect, compare, and evaluation paths (no query log)."""

    def execute(
        self,
        project: Project,
        question: str,
        chat_history: list[str] | None = None,
        *,
        filters: RetrievalFilters | None = None,
        retrieval_settings: dict[str, Any] | None = None,
        enable_query_rewrite_override: bool | None = None,
        enable_hybrid_retrieval_override: bool | None = None,
    ) -> PipelineBuildResult | None: ...


class GenerateAnswerFromPipelinePort(Protocol):
    """LLM answer from an already-built pipeline."""

    def execute(self, *, project: Project, pipeline: PipelineBuildResult) -> str: ...
