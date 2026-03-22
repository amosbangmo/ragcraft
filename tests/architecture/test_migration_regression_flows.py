"""
High-level regression checks for post-migration flows (composition root + HTTP wire helpers).

These are not full integration tests; they fail fast when critical wiring is accidentally removed.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from langchain_core.documents import Document

from src.application.http.wire import (
    pipeline_build_result_to_wire_dict,
    preview_summary_recall_to_wire_dict,
    rag_response_to_wire_dict,
)
from src.domain.pipeline_payloads import PipelineBuildResult
from src.domain.query_intent import QueryIntent
from src.domain.rag_response import RAGResponse
from src.domain.retrieval_strategy import RetrievalStrategy
from src.domain.summary_recall_document import SummaryRecallDocument

from tests.support.backend_container import build_backend_container_for_tests


def _require_full_backend_stack() -> None:
    """``build_backend`` pulls ingestion, which imports optional ``unstructured`` at import time."""
    pytest.importorskip("unstructured.chunking.title")


def test_composition_root_exposes_chat_ingestion_and_evaluation_use_cases() -> None:
    _require_full_backend_stack()
    c = build_backend_container_for_tests()
    assert c.chat_ask_question_use_case is not None
    assert c.chat_inspect_pipeline_use_case is not None
    assert c.chat_preview_summary_recall_use_case is not None
    assert c.ingestion_ingest_uploaded_file_use_case is not None
    assert c.ingestion_delete_document_use_case is not None
    assert c.evaluation_run_manual_evaluation_use_case is not None
    assert c.evaluation_run_gold_qa_dataset_evaluation_use_case is not None


def test_wire_helpers_normalize_chat_answer_pipeline_and_preview() -> None:
    """Ask/chat + retrieval inspection JSON shapes stay stable for the HTTP client."""
    rag = RAGResponse(
        question="q",
        answer="a",
        source_documents=[Document(page_content="s", metadata={"doc_id": "1"})],
        raw_assets=[{"doc_id": "1"}],
        prompt_sources=[{"doc_id": "1"}],
        confidence=0.5,
        latency={"total_ms": 1.0},
    )
    out = rag_response_to_wire_dict(rag)
    assert out["answer"] == "a"
    assert out["source_documents"][0]["metadata"]["doc_id"] == "1"

    preview = {
        "rewritten_question": "rw",
        "recalled_summary_docs": [SummaryRecallDocument(page_content="p", metadata={})],
        "vector_summary_docs": [],
        "bm25_summary_docs": [],
        "retrieval_mode": "faiss",
        "query_rewrite_enabled": True,
        "hybrid_retrieval_enabled": False,
        "use_adaptive_retrieval": False,
    }
    prev_out = preview_summary_recall_to_wire_dict(preview)
    assert prev_out is not None
    assert prev_out["recalled_summary_docs"][0]["page_content"] == "p"

    pipeline = PipelineBuildResult(
        question="q",
        rewritten_question="rw",
        query_intent=QueryIntent.FACTUAL,
        selected_summary_docs=[SummaryRecallDocument(page_content="c", metadata={"doc_id": "d"})],
        prompt_sources=[],
        confidence=0.1,
        latency={"total_ms": 2.0},
        latency_ms=2.0,
        retrieval_strategy=RetrievalStrategy(k=3, use_hybrid=False, apply_filters=True),
    )
    snap = pipeline_build_result_to_wire_dict(pipeline)
    assert snap["question"] == "q"
    assert snap["selected_summary_docs"][0]["metadata"]["doc_id"] == "d"


def test_ingest_wire_roundtrip_preserves_document_shape() -> None:
    from src.application.http.wire import ingest_document_result_to_wire_dict
    from src.domain.ingestion_diagnostics import IngestionDiagnostics

    result = SimpleNamespace(
        raw_assets=[{"doc_id": "x"}],
        replacement_info={"replaced": True},
        diagnostics=IngestionDiagnostics(),
    )
    d = ingest_document_result_to_wire_dict(result)
    assert d["raw_assets"][0]["doc_id"] == "x"
    assert d["replacement_info"]["replaced"] is True


def test_project_resolve_use_case_is_wired() -> None:
    c = build_backend_container_for_tests()
    assert c.projects_resolve_project_use_case is not None


def test_list_projects_use_case_is_wired() -> None:
    _require_full_backend_stack()
    c = build_backend_container_for_tests()
    assert c.projects_list_projects_use_case is not None
