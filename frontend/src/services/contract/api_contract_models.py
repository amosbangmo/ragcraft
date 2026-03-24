"""
Frontend-local wire types for the FastAPI JSON contract.

HTTP integration code (:mod:`services.backend.http_backend_client`, :mod:`services.backend.http_payloads`) uses **only**
these models plus stdlib / :mod:`infrastructure.config` — not ``domain`` or ``application``.
"""

from __future__ import annotations

import base64
from dataclasses import asdict, dataclass, field
from typing import Any

from infrastructure.config.config import RETRIEVAL_CONFIG, RetrievalConfig


@dataclass
class RetrievalFilters:
    """Mirrors FastAPI ``RetrievalFiltersPayload`` / domain recall scope (frontend-owned)."""

    source_files: list[str] = field(default_factory=list)
    content_types: list[str] = field(default_factory=list)
    page_numbers: list[int] = field(default_factory=list)
    page_start: int | None = None
    page_end: int | None = None

    def is_empty(self) -> bool:
        return (
            not self.source_files
            and not self.content_types
            and not self.page_numbers
            and self.page_start is None
            and self.page_end is None
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_files": list(self.source_files),
            "content_types": list(self.content_types),
            "page_numbers": list(self.page_numbers),
            "page_start": self.page_start,
            "page_end": self.page_end,
        }


@dataclass(frozen=True)
class WorkspaceProject:
    user_id: str
    project_id: str


@dataclass(frozen=True)
class RAGAnswer:
    question: str
    answer: str
    source_documents: tuple[dict[str, Any], ...] = ()
    raw_assets: tuple[dict[str, Any], ...] = ()
    prompt_sources: tuple[dict[str, Any], ...] = ()
    confidence: float = 0.0
    latency: dict[str, Any] | None = None


@dataclass(frozen=True)
class SummaryRecallDocumentView:
    """One recalled summary chunk from ``POST /chat/pipeline/preview-summary-recall``."""

    page_content: str
    metadata: dict[str, Any]


@dataclass(frozen=True)
class SummaryRecallPreviewPayload:
    """Wire view of the preview-summary-recall response body (``preview`` field)."""

    rewritten_question: str
    recalled_summary_docs: tuple[SummaryRecallDocumentView, ...]
    vector_summary_docs: tuple[SummaryRecallDocumentView, ...]
    bm25_summary_docs: tuple[SummaryRecallDocumentView, ...]
    retrieval_mode: str
    query_rewrite_enabled: bool
    hybrid_retrieval_enabled: bool
    use_adaptive_retrieval: bool


@dataclass(frozen=True)
class ProjectSettingsPayload:
    user_id: str
    project_id: str
    retrieval_preset: str
    retrieval_advanced: bool = False
    enable_query_rewrite: bool = True
    enable_hybrid_retrieval: bool = True


@dataclass(frozen=True)
class RetrievalSettingsPayload:
    enable_query_rewrite: bool
    enable_hybrid_retrieval: bool
    similarity_search_k: int
    bm25_search_k: int
    hybrid_search_k: int
    max_prompt_assets: int
    bm25_k1: float
    bm25_b: float
    bm25_epsilon: float
    rrf_k: int
    hybrid_beta: float
    max_text_chars_per_asset: int
    max_table_chars_per_asset: int
    query_rewrite_max_history_messages: int
    enable_contextual_compression: bool
    enable_section_expansion: bool
    section_expansion_neighbor_window: int
    section_expansion_max_per_section: int
    section_expansion_global_max: int

    @classmethod
    def from_retrieval_config(cls, cfg: RetrievalConfig) -> RetrievalSettingsPayload:
        return cls(
            enable_query_rewrite=bool(cfg.enable_query_rewrite),
            enable_hybrid_retrieval=bool(cfg.enable_hybrid_retrieval),
            similarity_search_k=int(cfg.similarity_search_k),
            bm25_search_k=int(cfg.bm25_search_k),
            hybrid_search_k=int(cfg.hybrid_search_k),
            max_prompt_assets=int(cfg.max_prompt_assets),
            bm25_k1=float(cfg.bm25_k1),
            bm25_b=float(cfg.bm25_b),
            bm25_epsilon=float(cfg.bm25_epsilon),
            rrf_k=int(cfg.rrf_k),
            hybrid_beta=float(cfg.hybrid_beta),
            max_text_chars_per_asset=int(cfg.max_text_chars_per_asset),
            max_table_chars_per_asset=int(cfg.max_table_chars_per_asset),
            query_rewrite_max_history_messages=int(cfg.query_rewrite_max_history_messages),
            enable_contextual_compression=bool(cfg.enable_contextual_compression),
            enable_section_expansion=bool(cfg.enable_section_expansion),
            section_expansion_neighbor_window=int(cfg.section_expansion_neighbor_window),
            section_expansion_max_per_section=int(cfg.section_expansion_max_per_section),
            section_expansion_global_max=int(cfg.section_expansion_global_max),
        )


@dataclass(frozen=True)
class EffectiveRetrievalSettingsPayload:
    preferences: ProjectSettingsPayload
    effective_retrieval: RetrievalSettingsPayload


@dataclass(frozen=True)
class UpdateProjectRetrievalSettingsCommand:
    user_id: str
    project_id: str
    retrieval_preset: str
    retrieval_advanced: bool
    enable_query_rewrite: bool
    enable_hybrid_retrieval: bool


@dataclass
class IngestionDiagnosticsPayload:
    extraction_ms: float = 0.0
    summarization_ms: float = 0.0
    indexing_ms: float = 0.0
    total_ms: float = 0.0
    extracted_elements: int = 0
    generated_assets: int = 0
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "extraction_ms": self.extraction_ms,
            "summarization_ms": self.summarization_ms,
            "indexing_ms": self.indexing_ms,
            "total_ms": self.total_ms,
            "extracted_elements": self.extracted_elements,
            "generated_assets": self.generated_assets,
            "errors": list(self.errors),
        }


@dataclass
class IngestDocumentPayload:
    raw_assets: list[dict[str, Any]] = field(default_factory=list)
    replacement_info: dict[str, Any] = field(default_factory=dict)
    diagnostics: IngestionDiagnosticsPayload = field(default_factory=IngestionDiagnosticsPayload)

    def content_type_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for asset in self.raw_assets:
            ct = asset.get("content_type") or "unknown"
            counts[ct] = counts.get(ct, 0) + 1
        return counts

    def _replacement_deleted_assets(self) -> int:
        return int((self.replacement_info or {}).get("deleted_assets", 0) or 0)

    def _replacement_deleted_vectors(self) -> int:
        return int((self.replacement_info or {}).get("deleted_vectors", 0) or 0)

    def format_ingestion_success_message(self, file_name: str) -> str:
        type_counts = self.content_type_counts()
        asset_count = len(self.raw_assets)
        da = self._replacement_deleted_assets()
        dv = self._replacement_deleted_vectors()
        if da or dv:
            return (
                f"{file_name}: replaced previous ingestion "
                f"({da} SQLite asset(s) removed, {dv} FAISS vector(s) removed), "
                f"then processed {asset_count} multimodal asset(s) {type_counts}"
            )
        return f"{file_name}: processed {asset_count} multimodal asset(s) {type_counts}"

    def format_reindex_success_message(self, file_name: str) -> str:
        type_counts = self.content_type_counts()
        da = self._replacement_deleted_assets()
        dv = self._replacement_deleted_vectors()
        return (
            f"{file_name}: reindexed successfully "
            f"({da} SQLite asset(s) replaced, {dv} FAISS vector(s) replaced), "
            f"generated {len(self.raw_assets)} multimodal asset(s) {type_counts}."
        )


@dataclass
class DeleteDocumentPayload:
    source_file: str = ""
    file_deleted: bool = False
    deleted_vectors: int = 0
    deleted_assets: int = 0

    def format_delete_summary(self, doc_name: str) -> str:
        return (
            f"{doc_name}: file deleted={self.file_deleted}, "
            f"SQLite assets removed={self.deleted_assets}, "
            f"FAISS vectors removed={self.deleted_vectors}."
        )


@dataclass
class QADatasetEntryPayload:
    id: int
    user_id: str
    project_id: str
    question: str
    expected_answer: str | None
    expected_doc_ids: list[str] = field(default_factory=list)
    expected_sources: list[str] = field(default_factory=list)
    created_at: Any = None
    updated_at: Any = None


@dataclass(frozen=True)
class BenchmarkExportMetadataPayload:
    project_id: str
    generated_at_utc: str
    enable_query_rewrite: bool
    enable_hybrid_retrieval: bool


@dataclass
class BenchmarkExportArtifactsPayload:
    metadata: BenchmarkExportMetadataPayload
    json_bytes: bytes
    json_filename: str
    csv_bytes: bytes
    csv_filename: str
    markdown_bytes: bytes
    markdown_filename: str
    run_id: str | None = None


def merge_retrieval_settings_payload(
    base: RetrievalSettingsPayload, overrides: dict[str, Any]
) -> RetrievalSettingsPayload:
    merged = {**asdict(base), **overrides}
    return RetrievalSettingsPayload(**merged)


def default_retrieval_settings_template() -> RetrievalSettingsPayload:
    return RetrievalSettingsPayload.from_retrieval_config(RETRIEVAL_CONFIG)
