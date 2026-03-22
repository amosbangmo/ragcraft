"""
Explicit wire-shape contracts for API JSON (framework-agnostic).

These :class:`typing.TypedDict` definitions document the **stable** response keys clients rely on.
Normalization uses :func:`src.application.json_wire.jsonify_value` (application wire layer) to produce
compatible ``dict`` / ``list`` trees; Pydantic response models in ``chat.py`` / ``evaluation.py``
validate those trees.

**Backward compatibility:** document snippets use ``page_content`` and ``metadata`` (legacy LangChain
document JSON shape) — unchanged from pre–boundary-cleanup behavior.
"""

from __future__ import annotations

from typing import Any, NotRequired, TypedDict


class SourceDocumentJson(TypedDict):
    """Retrieval snippet / summary doc as returned in ``source_documents`` arrays."""

    page_content: str
    metadata: dict[str, Any]


class PromptSourceJson(TypedDict, total=False):
    """One resolved prompt source (subset; extra keys may be present)."""

    source_number: int
    doc_id: str
    source_file: NotRequired[str]
    content_type: NotRequired[str]
    display_label: NotRequired[str]
    prompt_label: NotRequired[str]
    metadata: NotRequired[dict[str, Any]]


class RawAssetJson(TypedDict, total=False):
    """Asset dict in ``raw_assets`` (schema varies by modality)."""

    doc_id: str
    user_id: NotRequired[str]
    project_id: NotRequired[str]
    source_file: NotRequired[str]
    content_type: NotRequired[str]
    raw_content: NotRequired[str]
    summary: NotRequired[str]
    metadata: NotRequired[dict[str, Any]]


class SummaryRecallPreviewJson(TypedDict, total=False):
    """Keys returned by summary-recall preview (see preview router)."""

    rewritten_question: str
    recalled_summary_docs: list[SourceDocumentJson]
    vector_summary_docs: list[SourceDocumentJson]
    bm25_summary_docs: list[SourceDocumentJson]
    retrieval_mode: str
    query_rewrite_enabled: bool
    hybrid_retrieval_enabled: bool
    use_adaptive_retrieval: bool


class RAGAnswerPayloadJson(TypedDict, total=False):
    """Top-level chat ``/ask`` body (subset aligned with :class:`~src.domain.rag_response.RAGResponse`)."""

    question: str
    answer: str
    source_documents: list[SourceDocumentJson]
    raw_assets: list[RawAssetJson]
    prompt_sources: list[dict[str, Any]]
    confidence: float
    latency: dict[str, float] | None
