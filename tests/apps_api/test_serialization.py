from __future__ import annotations

from types import SimpleNamespace
from langchain_core.documents import Document

from apps.api.schemas.serialization import (
    benchmark_result_to_api_dict,
    effective_retrieval_settings_view_to_api_dict,
    ingest_document_result_to_api_dict,
    pipeline_build_result_to_api_dict,
    preview_summary_recall_to_api_dict,
    rag_response_to_api_dict,
)
from src.application.settings.dtos import EffectiveRetrievalSettingsView
from src.core.config import RETRIEVAL_CONFIG
from src.domain.project_settings import ProjectSettings
from src.domain.retrieval_settings import RetrievalSettings
from src.domain.benchmark_result import BenchmarkResult, BenchmarkRow, BenchmarkSummary
from src.domain.ingestion_diagnostics import IngestionDiagnostics
from src.domain.pipeline_payloads import PipelineBuildResult
from src.domain.query_intent import QueryIntent
from src.domain.rag_response import RAGResponse
from src.domain.retrieval_strategy import RetrievalStrategy


def test_rag_response_to_api_dict_normalizes_documents() -> None:
    doc = Document(page_content="s", metadata={"doc_id": "1"})
    r = RAGResponse(
        question="q",
        answer="a",
        source_documents=[doc],
        raw_assets=[{"doc_id": "1", "raw_content": "x"}],
        prompt_sources=[{"doc_id": "1"}],
        confidence=0.5,
        latency={"total_ms": 1.0},
    )
    d = rag_response_to_api_dict(r)
    assert d["source_documents"] == [{"page_content": "s", "metadata": {"doc_id": "1"}}]
    assert d["raw_assets"] == [{"doc_id": "1", "raw_content": "x"}]
    assert d["prompt_sources"] == [{"doc_id": "1"}]
    assert d["confidence"] == 0.5
    assert d["latency"] == {"total_ms": 1.0}


def test_pipeline_build_result_to_api_dict() -> None:
    p = PipelineBuildResult(
        question="q",
        rewritten_question="rw",
        query_intent=QueryIntent.FACTUAL,
        selected_summary_docs=[Document(page_content="c", metadata={"doc_id": "d"})],
        prompt_sources=[],
        confidence=0.1,
        latency={"total_ms": 2.0},
        latency_ms=2.0,
        retrieval_strategy=RetrievalStrategy(k=3, use_hybrid=False, apply_filters=True),
    )
    d = pipeline_build_result_to_api_dict(p)
    assert d["question"] == "q"
    assert d["selected_summary_docs"] == [{"page_content": "c", "metadata": {"doc_id": "d"}}]


def test_preview_summary_recall_to_api_dict_none() -> None:
    assert preview_summary_recall_to_api_dict(None) is None


def test_preview_summary_recall_to_api_dict_pass_through() -> None:
    doc = Document(page_content="p", metadata={})
    prev = {"rewritten_question": "r", "recalled_summary_docs": [doc]}
    d = preview_summary_recall_to_api_dict(prev)
    assert d["recalled_summary_docs"] == [{"page_content": "p", "metadata": {}}]


def test_ingest_document_result_to_api_dict() -> None:
    diag = IngestionDiagnostics()
    result = SimpleNamespace(
        raw_assets=[{"doc_id": "x"}],
        replacement_info={"replaced": True},
        diagnostics=diag,
    )
    d = ingest_document_result_to_api_dict(result)
    assert d["raw_assets"] == [{"doc_id": "x"}]
    assert d["replacement_info"] == {"replaced": True}
    assert d["diagnostics"] == diag.to_dict()


def test_effective_retrieval_settings_view_to_api_dict() -> None:
    view = EffectiveRetrievalSettingsView(
        preferences=ProjectSettings(
            user_id="u1",
            project_id="p1",
            retrieval_preset="balanced",
            retrieval_advanced=True,
        ),
        effective_retrieval=RetrievalSettings.from_retrieval_config(RETRIEVAL_CONFIG),
    )
    d = effective_retrieval_settings_view_to_api_dict(view)
    assert d["preferences"]["user_id"] == "u1"
    assert d["preferences"]["project_id"] == "p1"
    assert d["preferences"]["retrieval_preset"] == "balanced"
    assert "similarity_search_k" in d["effective_retrieval"]


def test_benchmark_result_to_api_dict_nested_document() -> None:
    doc = Document(page_content="bench", metadata={"k": "v"})
    row = BenchmarkRow(entry_id=1, question="q1", data={"pipeline_docs": [doc]})
    summary = BenchmarkSummary(data={"rows": 1})
    br = BenchmarkResult(summary=summary, rows=[row])
    d = benchmark_result_to_api_dict(br)
    assert d["rows"][0]["pipeline_docs"] == [{"page_content": "bench", "metadata": {"k": "v"}}]
