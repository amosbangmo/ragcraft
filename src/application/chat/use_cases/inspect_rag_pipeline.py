from __future__ import annotations

from typing import Any

from src.application.chat.use_cases.build_rag_pipeline import BuildRagPipelineUseCase
from src.domain.pipeline_payloads import PipelineBuildResult
from src.domain.project import Project
from src.domain.retrieval_filters import RetrievalFilters


class InspectRagPipelineUseCase:
    """
    Same pipeline build as :class:`BuildRagPipelineUseCase` but never writes query logs
    (inspector / debug flows).
    """

    def __init__(self, *, build_rag_pipeline: BuildRagPipelineUseCase) -> None:
        self._build_rag_pipeline = build_rag_pipeline

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
        return self._build_rag_pipeline.execute(
            project,
            question,
            chat_history,
            emit_query_log=False,
            filters=filters,
            retrieval_settings=retrieval_settings,
            enable_query_rewrite_override=enable_query_rewrite_override,
            enable_hybrid_retrieval_override=enable_hybrid_retrieval_override,
        )
