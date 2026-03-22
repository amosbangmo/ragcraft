"""Unit tests for weighted RRF fusion (summary recall merge)."""

from __future__ import annotations

from dataclasses import replace

from src.core.config import RETRIEVAL_CONFIG
from src.domain.retrieval_settings import RetrievalSettings
from src.domain.summary_document_fusion import merge_summary_documents_weighted_rrf
from src.domain.summary_recall_document import SummaryRecallDocument


def _settings(*, hybrid_beta: float = 0.5, rrf_k: int = 60) -> RetrievalSettings:
    base = RetrievalSettings.from_retrieval_config(RETRIEVAL_CONFIG)
    return replace(base, hybrid_beta=hybrid_beta, rrf_k=rrf_k)


def test_rrf_prioritizes_docs_that_rank_well_in_both_lists() -> None:
    settings = _settings()
    primary_docs = [
        SummaryRecallDocument(page_content="p1", metadata={"doc_id": "d1"}),
        SummaryRecallDocument(page_content="p2", metadata={"doc_id": "d2"}),
    ]
    secondary_docs = [
        SummaryRecallDocument(page_content="s1", metadata={"doc_id": "d2"}),
        SummaryRecallDocument(page_content="s2", metadata={"doc_id": "d3"}),
    ]

    merged = merge_summary_documents_weighted_rrf(
        settings=settings,
        primary_docs=primary_docs,
        secondary_docs=secondary_docs,
    )
    merged_ids = [doc.metadata["doc_id"] for doc in merged]

    assert merged_ids[:2] == ["d2", "d1"]


def test_rrf_respects_max_docs() -> None:
    settings = _settings()
    primary_docs = [
        SummaryRecallDocument(page_content="p1", metadata={"doc_id": "d1"}),
        SummaryRecallDocument(page_content="p2", metadata={"doc_id": "d2"}),
    ]
    secondary_docs = [
        SummaryRecallDocument(page_content="s1", metadata={"doc_id": "d2"}),
        SummaryRecallDocument(page_content="s2", metadata={"doc_id": "d3"}),
    ]

    merged = merge_summary_documents_weighted_rrf(
        settings=settings,
        primary_docs=primary_docs,
        secondary_docs=secondary_docs,
        max_docs=2,
    )
    merged_ids = [doc.metadata["doc_id"] for doc in merged]

    assert merged_ids == ["d2", "d1"]


def test_beta_one_weights_semantic_list_only() -> None:
    settings = _settings(hybrid_beta=1.0)
    primary_docs = [
        SummaryRecallDocument(page_content="p1", metadata={"doc_id": "d1"}),
        SummaryRecallDocument(page_content="p2", metadata={"doc_id": "d2"}),
    ]
    secondary_docs = [
        SummaryRecallDocument(page_content="s1", metadata={"doc_id": "d2"}),
        SummaryRecallDocument(page_content="s2", metadata={"doc_id": "d3"}),
    ]

    merged = merge_summary_documents_weighted_rrf(
        settings=settings,
        primary_docs=primary_docs,
        secondary_docs=secondary_docs,
    )
    merged_ids = [doc.metadata["doc_id"] for doc in merged]

    assert merged_ids == ["d1", "d2", "d3"]


def test_beta_zero_weights_lexical_list_only() -> None:
    settings = _settings(hybrid_beta=0.0)
    primary_docs = [
        SummaryRecallDocument(page_content="p1", metadata={"doc_id": "d1"}),
        SummaryRecallDocument(page_content="p2", metadata={"doc_id": "d2"}),
    ]
    secondary_docs = [
        SummaryRecallDocument(page_content="s1", metadata={"doc_id": "d2"}),
        SummaryRecallDocument(page_content="s2", metadata={"doc_id": "d3"}),
    ]

    merged = merge_summary_documents_weighted_rrf(
        settings=settings,
        primary_docs=primary_docs,
        secondary_docs=secondary_docs,
    )
    merged_ids = [doc.metadata["doc_id"] for doc in merged]

    assert merged_ids == ["d2", "d3", "d1"]
