"""Unit tests for post-recall document id selection helpers."""

from __future__ import annotations

from application.policies.pipeline_document_selection import (
    deduplicate_summary_doc_ids,
    select_summary_documents_by_doc_ids,
)
from domain.rag.summary_recall_document import SummaryRecallDocument


def test_deduplicate_preserves_first_seen_order() -> None:
    docs = [
        SummaryRecallDocument(page_content="a", metadata={"doc_id": "d1"}),
        SummaryRecallDocument(page_content="b", metadata={"doc_id": "d2"}),
        SummaryRecallDocument(page_content="c", metadata={"doc_id": "d1"}),
        SummaryRecallDocument(page_content="d", metadata={}),
    ]

    assert deduplicate_summary_doc_ids(docs) == ["d1", "d2"]


def test_select_by_doc_ids_maps_to_first_summary_per_id() -> None:
    docs = [
        SummaryRecallDocument(page_content="first", metadata={"doc_id": "a"}),
        SummaryRecallDocument(page_content="dup", metadata={"doc_id": "a"}),
        SummaryRecallDocument(page_content="bdoc", metadata={"doc_id": "b"}),
    ]

    selected = select_summary_documents_by_doc_ids(docs, ["b", "a", "missing"])

    assert [d.page_content for d in selected] == ["bdoc", "first"]
