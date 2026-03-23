from __future__ import annotations

from src.application.use_cases.chat.orchestration.ports import SummaryRecallStagePort
from src.application.use_cases.chat.orchestration.summary_recall_from_request import (
    run_summary_recall_from_chat_request,
)
from src.application.common.summary_recall_preview import SummaryRecallPreviewDTO
from src.domain.pipeline_payloads import SummaryRecallResult
from src.domain.project import Project
from src.domain.retrieval_filters import RetrievalFilters
from src.domain.retrieval_settings_override_spec import RetrievalSettingsOverrideSpec


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
    """Runs the summary-recall stage only and returns a typed preview DTO for wire/transport mappers."""

    def __init__(self, *, summary_recall_service: SummaryRecallStagePort) -> None:
        self._summary_recall = summary_recall_service

    def execute(
        self,
        project: Project,
        question: str,
        chat_history: list[str] | None = None,
        *,
        filters: RetrievalFilters | None = None,
        retrieval_overrides: RetrievalSettingsOverrideSpec | None = None,
        enable_query_rewrite_override: bool | None = None,
        enable_hybrid_retrieval_override: bool | None = None,
    ) -> SummaryRecallPreviewDTO | None:
        bundle = run_summary_recall_from_chat_request(
            summary_recall_service=self._summary_recall,
            project=project,
            question=question,
            chat_history=chat_history,
            filters=filters,
            retrieval_overrides=retrieval_overrides,
            enable_query_rewrite_override=enable_query_rewrite_override,
            enable_hybrid_retrieval_override=enable_hybrid_retrieval_override,
        )
        return _preview_from_summary_recall(bundle)
