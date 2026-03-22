"""Pure selection helpers over :class:`~src.domain.summary_recall_document.SummaryRecallDocument` lists."""

from __future__ import annotations

from typing import Any


def deduplicate_summary_doc_ids(summary_docs: list[Any]) -> list[str]:
    """Return unique doc_ids from summary recall documents, preserving first-seen order."""
    seen: set[str] = set()
    ordered_doc_ids: list[str] = []

    for doc in summary_docs:
        doc_id = doc.metadata.get("doc_id")
        if not doc_id or doc_id in seen:
            continue
        seen.add(doc_id)
        ordered_doc_ids.append(doc_id)

    return ordered_doc_ids


def select_summary_documents_by_doc_ids(summary_docs: list[Any], doc_ids: list[str]) -> list[Any]:
    """Map ordered doc_ids to representative summary documents (earliest occurrence wins)."""
    docs_by_id: dict[Any, Any] = {}

    for doc in summary_docs:
        doc_id = doc.metadata.get("doc_id")
        if doc_id and doc_id not in docs_by_id:
            docs_by_id[doc_id] = doc

    return [docs_by_id[doc_id] for doc_id in doc_ids if doc_id in docs_by_id]
