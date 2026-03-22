"""Thin adapter: delegates to application retrieval comparison (tests and legacy callers)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from src.application.use_cases.retrieval.retrieval_mode_comparison import compare_retrieval_modes_for_project
from src.domain.pipeline_payloads import PipelineBuildResult
from src.domain.project import Project


class RetrievalComparisonService:
    """
    Compare FAISS-only vs hybrid retrieval using an ``inspect_pipeline`` callable.

    Orchestration lives in :mod:`src.application.use_cases.retrieval.retrieval_mode_comparison`.
    """

    def __init__(self, *, inspect_pipeline: Callable[..., PipelineBuildResult | None]) -> None:
        self._inspect_pipeline = inspect_pipeline

    def compare(
        self,
        *,
        project: Project,
        questions: list[str],
        enable_query_rewrite: bool,
    ) -> dict[str, Any]:
        return compare_retrieval_modes_for_project(
            inspect_pipeline=self._inspect_pipeline,
            project=project,
            questions=questions,
            enable_query_rewrite=enable_query_rewrite,
        )
