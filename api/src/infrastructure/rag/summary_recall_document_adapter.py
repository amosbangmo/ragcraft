"""Convert between LangChain summary chunks and domain :class:`~domain.summary_recall_document.SummaryRecallDocument`."""

from __future__ import annotations

from langchain_core.documents import Document

from domain.rag.summary_recall_document import SummaryRecallDocument


def summary_recall_document_from_langchain(doc: Document) -> SummaryRecallDocument:
    return SummaryRecallDocument(
        page_content=str(doc.page_content or ""),
        metadata=dict(doc.metadata or {}),
    )


def langchain_document_from_summary_recall(doc: SummaryRecallDocument) -> Document:
    return Document(page_content=doc.page_content, metadata=dict(doc.metadata))
