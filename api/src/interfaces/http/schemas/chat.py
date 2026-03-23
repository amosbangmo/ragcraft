"""
Pydantic models for chat and retrieval-debug endpoints.

Response field shapes are produced by :mod:`application.http.wire` wire DTOs
(:class:`~domain.rag_response.RAGResponse`, pipeline snapshots, preview dicts).
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from domain.rag.retrieval_filters import RetrievalFilters


class RetrievalFiltersPayload(BaseModel):
    """Optional scope for retrieval (source files, content types, page span)."""

    model_config = {"extra": "forbid"}

    source_files: list[str] = Field(default_factory=list, description="Restrict to these source filenames.")
    content_types: list[str] = Field(
        default_factory=list,
        description='e.g. ["text","table","image"]',
    )
    page_numbers: list[int] = Field(default_factory=list)
    page_start: int | None = None
    page_end: int | None = None

    def to_domain(self) -> RetrievalFilters:
        return RetrievalFilters(
            source_files=list(self.source_files),
            content_types=list(self.content_types),
            page_numbers=list(self.page_numbers),
            page_start=self.page_start,
            page_end=self.page_end,
        )


class ChatPipelineRequestBase(BaseModel):
    """
    Shared JSON body for chat and pipeline calls.

    The authenticated user comes from ``Authorization: Bearer`` (see
    :func:`apps.api.dependencies.get_authenticated_principal`); do not send ``user_id`` in the body.
    """

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "project_id": "my-rag-project",
                    "question": "What is the refund policy?",
                    "chat_history": [],
                }
            ]
        },
    )

    project_id: str = Field(
        ...,
        min_length=1,
        description="Project directory name under the authenticated workspace user.",
        examples=["demo"],
    )
    question: str = Field(..., min_length=1, description="User question for this turn.")
    chat_history: list[str] = Field(
        default_factory=list,
        description="Prior user/assistant strings in order (alternating turns).",
    )
    filters: RetrievalFiltersPayload | None = Field(
        default=None,
        description="Optional retrieval scope; omit for project-wide search.",
    )
    retrieval_settings: dict[str, Any] | None = Field(
        default=None,
        description=(
            "Optional partial overrides merged onto effective project retrieval settings. "
            "Keys must match :class:`~domain.retrieval_settings.RetrievalSettings` field names; "
            "the API maps this to :class:`~domain.retrieval_settings_override_spec.RetrievalSettingsOverrideSpec`."
        ),
    )
    enable_query_rewrite_override: bool | None = Field(
        default=None,
        description="If set, overrides project default for query rewrite.",
    )
    enable_hybrid_retrieval_override: bool | None = Field(
        default=None,
        description="If set, overrides project default for hybrid retrieval.",
    )


class ChatAskRequest(ChatPipelineRequestBase):
    """Full RAG ask: retrieve, assemble prompt, generate answer, optional query log."""

    pass


class PipelineInspectRequest(ChatPipelineRequestBase):
    """Build the full pipeline for inspection without emitting a final answer (no query log write)."""

    pass


class PreviewSummaryRecallRequest(ChatPipelineRequestBase):
    """Run summary-recall stage only (vector + optional BM25) for debugging retrieval."""

    pass


class ChatAskResponse(BaseModel):
    """Answer payload for full RAG responses (stable JSON-serializable fields)."""

    model_config = {"extra": "forbid"}

    status: Literal["answered", "no_pipeline"] = Field(
        description="answered when a pipeline ran; no_pipeline when retrieval returned nothing.",
    )
    question: str
    answer: str = ""
    source_documents: list[dict[str, Any]] = Field(default_factory=list)
    raw_assets: list[dict[str, Any]] = Field(default_factory=list)
    prompt_sources: list[dict[str, Any]] = Field(default_factory=list)
    confidence: float = 0.0
    latency: dict[str, Any] | None = None


class PipelineInspectResponse(BaseModel):
    model_config = {"extra": "forbid"}

    status: Literal["ok", "no_pipeline"] = "ok"
    question: str
    pipeline: dict[str, Any] | None = Field(
        default=None,
        description="Full pipeline state (documents serialized as page_content + metadata dicts).",
    )


class RetrievalCompareRequest(BaseModel):
    """Compare FAISS-only vs hybrid retrieval; identity comes from the bearer token."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "project_id": "demo",
                    "questions": ["What are the payment terms?", "Who is the counterparty?"],
                    "enable_query_rewrite": True,
                }
            ]
        },
    )

    project_id: str = Field(..., min_length=1, description="Project under the authenticated user.")
    questions: list[str] = Field(
        default_factory=list,
        description="Questions to run under both retrieval modes.",
    )
    enable_query_rewrite: bool = Field(
        default=True,
        description="Whether to rewrite each question before retrieval.",
    )


class RetrievalCompareResponse(BaseModel):
    model_config = {"extra": "forbid"}

    questions: list[str] = Field(default_factory=list)
    summary: dict[str, Any] = Field(default_factory=dict)
    rows: list[dict[str, Any]] = Field(default_factory=list)


class PreviewSummaryRecallResponse(BaseModel):
    model_config = {"extra": "forbid"}

    status: Literal["ok", "no_recall"] = "ok"
    question: str
    preview: dict[str, Any] | None = Field(
        default=None,
        description="Rewritten question, recalled_summary_docs, vector/bm25 splits, mode flags.",
    )

