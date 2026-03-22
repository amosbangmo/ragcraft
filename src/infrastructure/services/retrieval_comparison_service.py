"""Thin adapter: delegates to application retrieval comparison (kept for tests and ``RAGService.inspect_pipeline`` wiring)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from src.application.use_cases.retrieval.retrieval_mode_comparison import compare_retrieval_modes_for_project
from src.domain.project import Project

if TYPE_CHECKING:
    from src.infrastructure.services.rag_service import RAGService


class RetrievalComparisonService:
    """
    Compare FAISS-only vs hybrid retrieval using ``rag_service.inspect_pipeline``.

    Orchestration lives in :mod:`src.application.use_cases.retrieval.retrieval_mode_comparison`.
    """

    def __init__(self, rag_service: RAGService) -> None:
        self.rag_service = rag_service

    def compare(
        self,
        *,
        project: Project,
        questions: list[str],
        enable_query_rewrite: bool,
    ) -> dict[str, Any]:
        return compare_retrieval_modes_for_project(
            inspect_pipeline=self.rag_service.inspect_pipeline,
            project=project,
            questions=questions,
            enable_query_rewrite=enable_query_rewrite,
        )
