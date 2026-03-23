"""High-level RAG retrieval / pipeline-build boundary (summary recall + post-recall assembly)."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from domain.projects.project import Project
from domain.rag.pipeline_payloads import PipelineBuildResult
from domain.rag.retrieval_filters import RetrievalFilters
from domain.rag.retrieval_settings_override_spec import RetrievalSettingsOverrideSpec


@runtime_checkable
class RetrievalPort(Protocol):
    """
    Build a retrieval + prompt pipeline for a question.

    Typically implemented by :class:`~application.use_cases.chat.build_rag_pipeline.BuildRagPipelineUseCase`.
    """

    def execute(
        self,
        project: Project,
        question: str,
        chat_history: list[str] | None = None,
        *,
        emit_query_log: bool = True,
        filters: RetrievalFilters | None = None,
        retrieval_overrides: RetrievalSettingsOverrideSpec | None = None,
        enable_query_rewrite_override: bool | None = None,
        enable_hybrid_retrieval_override: bool | None = None,
    ) -> PipelineBuildResult | None: ...


__all__ = ["RetrievalPort"]
