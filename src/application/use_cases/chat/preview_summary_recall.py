from __future__ import annotations

from typing import Any

from src.application.use_cases.chat.orchestration.ports import SummaryRecallStagePort
from src.application.common.pipeline_query_context import RAGPipelineQueryContext
from src.application.common.summary_recall_preview import SummaryRecallPreviewDTO
from src.domain.pipeline_payloads import SummaryRecallResult
from src.domain.project import Project
from src.domain.retrieval_filters import RetrievalFilters


def _preview_from_summary_recall(bundle: SummaryRecallResult) -> SummaryRecallPreviewDTO | None:
    if not bundle.recalled_summary_docs:
        return None
    return SummaryRecallPreviewDTO(
        rewritten_question=bundle.rewritten_question,
        recalled_summary_docs=bundle.recalled_summary_docs,
        vector_summary_docs=bundle.vector_summary_docs,
        bm25_summary_docs=bundle.bm25_summary_docs,
        retrieval_mode="faiss+bm25" if bundle.enable_hybrid_retrieval else "faiss",
        query_rewrite_enabled=bundle.enable_query_rewrite,
        hybrid_retrieval_enabled=bundle.enable_hybrid_retrieval,
        use_adaptive_retrieval=bundle.use_adaptive_retrieval,
    )


class PreviewSummaryRecallUseCase:
    """Runs the summary-recall stage only and returns the legacy preview dict for the UI / API."""

    def __init__(self, *, summary_recall_service: SummaryRecallStagePort) -> None:
        self._summary_recall = summary_recall_service

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
    ) -> dict | None:
        ctx = RAGPipelineQueryContext.from_legacy(
            chat_history,
            filters=filters,
            retrieval_settings=retrieval_settings,
            enable_query_rewrite_override=enable_query_rewrite_override,
            enable_hybrid_retrieval_override=enable_hybrid_retrieval_override,
        )
        bundle = self._summary_recall.summary_recall_stage(
            project,
            question,
            list(ctx.chat_history),
            enable_query_rewrite_override=ctx.enable_query_rewrite_override,
            enable_hybrid_retrieval_override=ctx.enable_hybrid_retrieval_override,
            filters=ctx.filters,
            retrieval_settings=ctx.retrieval_settings,
        )
        preview = _preview_from_summary_recall(bundle)
        return preview.to_dict() if preview is not None else None
