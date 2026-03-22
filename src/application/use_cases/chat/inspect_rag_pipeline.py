from __future__ import annotations

from collections.abc import Callable
from typing import Any

from src.domain.pipeline_payloads import PipelineBuildResult
from src.domain.project import Project
from src.domain.retrieval_filters import RetrievalFilters


class InspectRagPipelineUseCase:
    """
    Same pipeline build as the build use case but never writes query logs
    (inspector / debug flows).

    ``build_pipeline`` is typically ``functools.partial(build_rag_pipeline.execute, emit_query_log=False)``.
    """

    def __init__(
        self,
        *,
        build_pipeline: Callable[..., PipelineBuildResult | None],
    ) -> None:
        self._build_pipeline = build_pipeline

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
    ) -> PipelineBuildResult | None:
        return self._build_pipeline(
            project,
            question,
            chat_history,
            filters=filters,
            retrieval_settings=retrieval_settings,
            enable_query_rewrite_override=enable_query_rewrite_override,
            enable_hybrid_retrieval_override=enable_hybrid_retrieval_override,
        )
