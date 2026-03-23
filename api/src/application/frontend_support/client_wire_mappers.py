"""Map domain/application objects to frontend wire types at the in-process client boundary."""

from __future__ import annotations

from typing import Any

from application.dto.settings import EffectiveRetrievalSettingsView
from domain.evaluation.benchmark_result import BenchmarkResult as DomainBenchmarkResult
from domain.evaluation.manual_evaluation_result import (
    ManualEvaluationResult as DomainManualEvaluationResult,
)
from domain.evaluation.qa_dataset_entry import QADatasetEntry
from domain.projects.project_settings import ProjectSettings
from domain.rag.retrieval_filters import RetrievalFilters as DomainRetrievalFilters
from services.api_contract_models import (
    DeleteDocumentPayload,
    EffectiveRetrievalSettingsPayload,
    IngestDocumentPayload,
    IngestionDiagnosticsPayload,
    ProjectSettingsPayload,
    QADatasetEntryPayload,
    RetrievalSettingsPayload,
)
from services.evaluation_wire_models import BenchmarkResult as WireBenchmarkResult
from services.evaluation_wire_parse import manual_evaluation_result_from_plain_dict


def retrieval_filters_to_domain(filters: Any) -> DomainRetrievalFilters | None:
    if filters is None:
        return None
    if isinstance(filters, DomainRetrievalFilters):
        return filters
    return DomainRetrievalFilters(
        source_files=list(filters.source_files),
        content_types=list(filters.content_types),
        page_numbers=list(filters.page_numbers),
        page_start=filters.page_start,
        page_end=filters.page_end,
    )


def effective_retrieval_view_to_wire(view: EffectiveRetrievalSettingsView) -> EffectiveRetrievalSettingsPayload:
    p = view.preferences
    er = view.effective_retrieval
    preferences = ProjectSettingsPayload(
        user_id=p.user_id,
        project_id=p.project_id,
        retrieval_preset=p.retrieval_preset,
        retrieval_advanced=p.retrieval_advanced,
        enable_query_rewrite=p.enable_query_rewrite,
        enable_hybrid_retrieval=p.enable_hybrid_retrieval,
    )
    eff = RetrievalSettingsPayload(
        enable_query_rewrite=er.enable_query_rewrite,
        enable_hybrid_retrieval=er.enable_hybrid_retrieval,
        similarity_search_k=er.similarity_search_k,
        bm25_search_k=er.bm25_search_k,
        hybrid_search_k=er.hybrid_search_k,
        max_prompt_assets=er.max_prompt_assets,
        bm25_k1=er.bm25_k1,
        bm25_b=er.bm25_b,
        bm25_epsilon=er.bm25_epsilon,
        rrf_k=er.rrf_k,
        hybrid_beta=er.hybrid_beta,
        max_text_chars_per_asset=er.max_text_chars_per_asset,
        max_table_chars_per_asset=er.max_table_chars_per_asset,
        query_rewrite_max_history_messages=er.query_rewrite_max_history_messages,
        enable_contextual_compression=er.enable_contextual_compression,
        enable_section_expansion=er.enable_section_expansion,
        section_expansion_neighbor_window=er.section_expansion_neighbor_window,
        section_expansion_max_per_section=er.section_expansion_max_per_section,
        section_expansion_global_max=er.section_expansion_global_max,
    )
    return EffectiveRetrievalSettingsPayload(preferences=preferences, effective_retrieval=eff)


def project_settings_to_payload(ps: ProjectSettings) -> ProjectSettingsPayload:
    return ProjectSettingsPayload(
        user_id=ps.user_id,
        project_id=ps.project_id,
        retrieval_preset=ps.retrieval_preset,
        retrieval_advanced=ps.retrieval_advanced,
        enable_query_rewrite=ps.enable_query_rewrite,
        enable_hybrid_retrieval=ps.enable_hybrid_retrieval,
    )


def _raw_assets_to_wire_list(assets: Any) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for a in assets or []:
        if hasattr(a, "upsert_kwargs") and callable(a.upsert_kwargs):
            out.append(a.upsert_kwargs())
        elif isinstance(a, dict):
            out.append(dict(a))
        else:
            out.append(dict(a))
    return out


def ingest_document_result_to_wire(result: Any) -> IngestDocumentPayload:
    diag = result.diagnostics
    diagnostics = IngestionDiagnosticsPayload(
        extraction_ms=float(diag.extraction_ms),
        summarization_ms=float(diag.summarization_ms),
        indexing_ms=float(diag.indexing_ms),
        total_ms=float(diag.total_ms),
        extracted_elements=int(diag.extracted_elements),
        generated_assets=int(diag.generated_assets),
        errors=list(diag.errors or []),
    )
    ri = result.replacement_info
    if ri is None:
        replacement_wire: dict[str, Any] = {}
    elif hasattr(ri, "to_wire_dict"):
        replacement_wire = dict(ri.to_wire_dict())
    else:
        replacement_wire = dict(ri or {})
    return IngestDocumentPayload(
        raw_assets=_raw_assets_to_wire_list(result.raw_assets),
        replacement_info=replacement_wire,
        diagnostics=diagnostics,
    )


def delete_document_result_to_wire(result: Any) -> DeleteDocumentPayload:
    return DeleteDocumentPayload(
        source_file=str(result.source_file),
        file_deleted=bool(result.file_deleted),
        deleted_vectors=int(result.deleted_vectors),
        deleted_assets=int(result.deleted_assets),
    )


def qa_dataset_entry_to_wire(entry: QADatasetEntry) -> QADatasetEntryPayload:
    return QADatasetEntryPayload(
        id=int(entry.id),
        user_id=str(entry.user_id),
        project_id=str(entry.project_id),
        question=str(entry.question or ""),
        expected_answer=entry.expected_answer,
        expected_doc_ids=list(entry.expected_doc_ids or []),
        expected_sources=list(entry.expected_sources or []),
        created_at=entry.created_at,
        updated_at=entry.updated_at,
    )


def manual_evaluation_to_wire(result: DomainManualEvaluationResult) -> Any:
    return manual_evaluation_result_from_plain_dict(result.to_dict())


def benchmark_result_to_wire(result: DomainBenchmarkResult) -> WireBenchmarkResult:
    return WireBenchmarkResult.from_plain_dict(result.to_dict())


def wire_benchmark_to_domain(result: WireBenchmarkResult) -> DomainBenchmarkResult:
    return DomainBenchmarkResult.from_plain_dict(result.to_dict())


def rag_response_to_rag_answer(result: Any) -> Any:
    from services.api_contract_models import RAGAnswer

    lat = getattr(result, "latency", None)
    latency_dict: dict[str, Any] | None = None
    if lat is not None:
        if hasattr(lat, "to_dict") and callable(lat.to_dict):
            latency_dict = dict(lat.to_dict())
        elif isinstance(lat, dict):
            latency_dict = dict(lat)
    return RAGAnswer(
        question=str(result.question),
        answer=str(result.answer),
        source_documents=tuple(result.source_documents or []),
        raw_assets=tuple(result.raw_assets or []),
        prompt_sources=tuple(result.prompt_sources or []),
        confidence=float(result.confidence or 0.0),
        latency=latency_dict,
    )
