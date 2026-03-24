"""Deserialize FastAPI JSON into frontend wire types (:mod:`services.contract.api_contract_models`)."""

from __future__ import annotations

import base64
from typing import Any

from services.contract.api_contract_models import (
    BenchmarkExportArtifactsPayload,
    BenchmarkExportMetadataPayload,
    DeleteDocumentPayload,
    EffectiveRetrievalSettingsPayload,
    IngestDocumentPayload,
    IngestionDiagnosticsPayload,
    ProjectSettingsPayload,
    QADatasetEntryPayload,
    RAGAnswer,
    RetrievalSettingsPayload,
    SummaryRecallDocumentView,
    SummaryRecallPreviewPayload,
    default_retrieval_settings_template,
    merge_retrieval_settings_payload,
)


def _summary_doc_view_from_api_item(item: Any) -> SummaryRecallDocumentView:
    if not isinstance(item, dict):
        return SummaryRecallDocumentView(page_content="", metadata={})
    meta = item.get("metadata")
    return SummaryRecallDocumentView(
        page_content=str(item.get("page_content") or ""),
        metadata=dict(meta) if isinstance(meta, dict) else {},
    )


def summary_recall_preview_from_api_dict(raw: dict[str, Any]) -> SummaryRecallPreviewPayload:
    """Parse the ``preview`` object from a successful preview-summary-recall response."""
    recalled = raw.get("recalled_summary_docs") or []
    vector = raw.get("vector_summary_docs") or []
    bm25 = raw.get("bm25_summary_docs") or []
    return SummaryRecallPreviewPayload(
        rewritten_question=str(raw.get("rewritten_question") or ""),
        recalled_summary_docs=tuple(_summary_doc_view_from_api_item(x) for x in recalled),
        vector_summary_docs=tuple(_summary_doc_view_from_api_item(x) for x in vector),
        bm25_summary_docs=tuple(_summary_doc_view_from_api_item(x) for x in bm25),
        retrieval_mode=str(raw.get("retrieval_mode") or ""),
        query_rewrite_enabled=bool(raw.get("query_rewrite_enabled")),
        hybrid_retrieval_enabled=bool(raw.get("hybrid_retrieval_enabled")),
        use_adaptive_retrieval=bool(raw.get("use_adaptive_retrieval")),
    )


def effective_retrieval_view_from_api_dict(data: dict[str, Any]) -> EffectiveRetrievalSettingsPayload:
    prefs = data.get("preferences") or {}
    effective = data.get("effective_retrieval") or {}
    preferences = ProjectSettingsPayload(
        user_id=str(prefs["user_id"]),
        project_id=str(prefs["project_id"]),
        retrieval_preset=str(prefs.get("retrieval_preset") or "balanced"),
        retrieval_advanced=bool(prefs.get("retrieval_advanced", False)),
        enable_query_rewrite=bool(prefs.get("enable_query_rewrite", True)),
        enable_hybrid_retrieval=bool(prefs.get("enable_hybrid_retrieval", True)),
    )
    template = default_retrieval_settings_template()
    eff = merge_retrieval_settings_template(template, effective)
    return EffectiveRetrievalSettingsPayload(preferences=preferences, effective_retrieval=eff)


def merge_retrieval_settings_template(
    template: RetrievalSettingsPayload, overrides: dict[str, Any]
) -> RetrievalSettingsPayload:
    return merge_retrieval_settings_payload(template, overrides)


def ingest_document_result_from_api_dict(data: dict[str, Any]) -> IngestDocumentPayload:
    diag_raw = data.get("diagnostics") or {}
    diagnostics = IngestionDiagnosticsPayload(
        extraction_ms=float(diag_raw.get("extraction_ms") or 0.0),
        summarization_ms=float(diag_raw.get("summarization_ms") or 0.0),
        indexing_ms=float(diag_raw.get("indexing_ms") or 0.0),
        total_ms=float(diag_raw.get("total_ms") or 0.0),
        extracted_elements=int(diag_raw.get("extracted_elements") or 0),
        generated_assets=int(diag_raw.get("generated_assets") or 0),
        errors=list(diag_raw.get("errors") or []),
    )
    return IngestDocumentPayload(
        raw_assets=list(data.get("raw_assets") or []),
        replacement_info=dict(data.get("replacement_info") or {}),
        diagnostics=diagnostics,
    )


def delete_document_result_from_api_dict(data: dict[str, Any]) -> DeleteDocumentPayload:
    return DeleteDocumentPayload(
        source_file=str(data.get("source_file") or ""),
        file_deleted=bool(data.get("file_deleted")),
        deleted_vectors=int(data.get("deleted_vectors") or 0),
        deleted_assets=int(data.get("deleted_assets") or 0),
    )


def qa_dataset_entry_from_api_dict(row: dict[str, Any]) -> QADatasetEntryPayload:
    return QADatasetEntryPayload(
        id=int(row["id"]),
        user_id=str(row["user_id"]),
        project_id=str(row["project_id"]),
        question=str(row.get("question") or ""),
        expected_answer=row.get("expected_answer"),
        expected_doc_ids=list(row.get("expected_doc_ids") or []),
        expected_sources=list(row.get("expected_sources") or []),
        created_at=row.get("created_at"),
        updated_at=row.get("updated_at"),
    )


def benchmark_export_artifacts_from_api_dict(data: dict[str, Any]) -> BenchmarkExportArtifactsPayload:
    meta_raw = data.get("metadata") or {}
    metadata = BenchmarkExportMetadataPayload(
        project_id=str(meta_raw.get("project_id") or ""),
        generated_at_utc=str(meta_raw.get("generated_at_utc") or ""),
        enable_query_rewrite=bool(meta_raw.get("enable_query_rewrite", False)),
        enable_hybrid_retrieval=bool(meta_raw.get("enable_hybrid_retrieval", False)),
    )
    return BenchmarkExportArtifactsPayload(
        metadata=metadata,
        json_bytes=base64.standard_b64decode(str(data.get("json_base64") or "")),
        json_filename=str(data.get("json_filename") or "benchmark.json"),
        csv_bytes=base64.standard_b64decode(str(data.get("csv_base64") or "")),
        csv_filename=str(data.get("csv_filename") or "benchmark.csv"),
        markdown_bytes=base64.standard_b64decode(str(data.get("markdown_base64") or "")),
        markdown_filename=str(data.get("markdown_filename") or "benchmark.md"),
        run_id=data.get("run_id"),
    )


def rag_answer_from_ask_api_dict(data: dict[str, Any]) -> RAGAnswer | None:
    if data.get("status") == "no_pipeline":
        return None
    lat_raw = data.get("latency")
    latency: dict[str, Any] | None = None
    if isinstance(lat_raw, dict):
        latency = dict(lat_raw)
    return RAGAnswer(
        question=str(data.get("question") or ""),
        answer=str(data.get("answer") or ""),
        source_documents=tuple(data.get("source_documents") or []),
        raw_assets=tuple(data.get("raw_assets") or []),
        prompt_sources=tuple(data.get("prompt_sources") or []),
        confidence=float(data.get("confidence") or 0.0),
        latency=latency,
    )


def qa_generate_result_from_api_dict(data: dict[str, Any]) -> dict[str, Any]:
    created = [qa_dataset_entry_from_api_dict(e) for e in (data.get("created_entries") or [])]
    return {
        "generation_mode": data.get("generation_mode") or "append",
        "deleted_existing_entries": int(data.get("deleted_existing_entries") or 0),
        "created_entries": created,
        "skipped_duplicates": list(data.get("skipped_duplicates") or []),
        "requested_questions": int(data.get("requested_questions") or 0),
        "raw_generated_count": int(data.get("raw_generated_count") or 0),
    }
