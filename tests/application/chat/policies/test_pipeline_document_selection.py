"""Unit tests for post-recall document id selection helpers."""

from __future__ import annotations

from langchain_core.documents import Document

from src.application.chat.policies.pipeline_document_selection import (
    deduplicate_summary_doc_ids,
    select_summary_documents_by_doc_ids,
)


def test_deduplicate_preserves_first_seen_order() -> None:
    docs = [
        Document(page_content="a", metadata={"doc_id": "d1"}),
        Document(page_content="b", metadata={"doc_id": "d2"}),
        Document(page_content="c", metadata={"doc_id": "d1"}),
        Document(page_content="d", metadata={}),
    ]

    assert deduplicate_summary_doc_ids(docs) == ["d1", "d2"]


def test_select_by_doc_ids_maps_to_first_summary_per_id() -> None:
    docs = [
        Document(page_content="first", metadata={"doc_id": "a"}),
        Document(page_content="dup", metadata={"doc_id": "a"}),
        Document(page_content="bdoc", metadata={"doc_id": "b"}),
    ]

    selected = select_summary_documents_by_doc_ids(docs, ["b", "a", "missing"])

    assert [d.page_content for d in selected] == ["bdoc", "first"]
