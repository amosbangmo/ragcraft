from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from src.application.chat.use_cases.preview_summary_recall import PreviewSummaryRecallUseCase
from src.domain.project import Project
from src.domain.summary_recall_document import SummaryRecallDocument


def test_preview_returns_none_when_no_recall() -> None:
    svc = MagicMock()
    svc.summary_recall_stage.return_value = SimpleNamespace(
        rewritten_question="q",
        recalled_summary_docs=[],
        vector_summary_docs=[],
        bm25_summary_docs=[],
        enable_hybrid_retrieval=False,
        enable_query_rewrite=False,
        use_adaptive_retrieval=False,
    )
    uc = PreviewSummaryRecallUseCase(summary_recall_service=svc)
    project = Project(user_id="u", project_id="p")

    assert uc.execute(project, "question") is None


def test_preview_returns_dict_when_recall_present() -> None:
    doc = SummaryRecallDocument(page_content="s", metadata={"doc_id": "d1"})
    svc = MagicMock()
    svc.summary_recall_stage.return_value = SimpleNamespace(
        rewritten_question="rw",
        recalled_summary_docs=[doc],
        vector_summary_docs=[doc],
        bm25_summary_docs=[],
        enable_hybrid_retrieval=False,
        enable_query_rewrite=True,
        use_adaptive_retrieval=False,
    )
    uc = PreviewSummaryRecallUseCase(summary_recall_service=svc)
    project = Project(user_id="u", project_id="p")

    raw = uc.execute(project, "question")

    assert raw is not None
    assert raw["rewritten_question"] == "rw"
    assert raw["retrieval_mode"] == "faiss"
