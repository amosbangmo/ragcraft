"""Deserialize API JSON into domain/application types used by Streamlit."""

from __future__ import annotations

import base64
from dataclasses import asdict
from typing import Any

from application.dto.benchmark_export import BenchmarkExportArtifacts
from application.dto.ingestion import DeleteDocumentResult, IngestDocumentResult
from application.dto.settings import EffectiveRetrievalSettingsView
from domain.evaluation.benchmark_result import BenchmarkRunMetadata
from domain.common.ingestion_diagnostics import IngestionDiagnostics
from domain.projects.project_settings import ProjectSettings
from domain.evaluation.qa_dataset_entry import QADatasetEntry
from domain.rag.retrieval_settings import RetrievalSettings
from infrastructure.config.config import RETRIEVAL_CONFIG


def effective_retrieval_view_from_api_dict(data: dict[str, Any]) -> EffectiveRetrievalSettingsView:
    prefs = data.get("preferences") or {}
    effective = data.get("effective_retrieval") or {}
    preferences = ProjectSettings(
        user_id=str(prefs["user_id"]),
        project_id=str(prefs["project_id"]),
        retrieval_preset=str(prefs.get("retrieval_preset") or "balanced"),
        retrieval_advanced=bool(prefs.get("retrieval_advanced", False)),
        enable_query_rewrite=bool(prefs.get("enable_query_rewrite", True)),
        enable_hybrid_retrieval=bool(prefs.get("enable_hybrid_retrieval", True)),
    )
    template = RetrievalSettings.from_retrieval_config(RETRIEVAL_CONFIG)
    merged = {**asdict(template), **effective}
    eff = RetrievalSettings(**merged)
    return EffectiveRetrievalSettingsView(preferences=preferences, effective_retrieval=eff)


def ingest_document_result_from_api_dict(data: dict[str, Any]) -> IngestDocumentResult:
    diag_raw = data.get("diagnostics") or {}
    diagnostics = IngestionDiagnostics(
        extraction_ms=float(diag_raw.get("extraction_ms") or 0.0),
        summarization_ms=float(diag_raw.get("summarization_ms") or 0.0),
        indexing_ms=float(diag_raw.get("indexing_ms") or 0.0),
        total_ms=float(diag_raw.get("total_ms") or 0.0),
        extracted_elements=int(diag_raw.get("extracted_elements") or 0),
        generated_assets=int(diag_raw.get("generated_assets") or 0),
        errors=list(diag_raw.get("errors") or []),
    )
    return IngestDocumentResult(
        raw_assets=list(data.get("raw_assets") or []),
        replacement_info=dict(data.get("replacement_info") or {}),
        diagnostics=diagnostics,
    )


def delete_document_result_from_api_dict(data: dict[str, Any]) -> DeleteDocumentResult:
    return DeleteDocumentResult(
        source_file=str(data.get("source_file") or ""),
        file_deleted=bool(data.get("file_deleted")),
        deleted_vectors=int(data.get("deleted_vectors") or 0),
        deleted_assets=int(data.get("deleted_assets") or 0),
    )


def qa_dataset_entry_from_api_dict(row: dict[str, Any]) -> QADatasetEntry:
    return QADatasetEntry(
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


def benchmark_export_artifacts_from_api_dict(data: dict[str, Any]) -> BenchmarkExportArtifacts:
    meta_raw = data.get("metadata") or {}
    metadata = BenchmarkRunMetadata(
        project_id=str(meta_raw.get("project_id") or ""),
        generated_at_utc=str(meta_raw.get("generated_at_utc") or ""),
        enable_query_rewrite=bool(meta_raw.get("enable_query_rewrite", False)),
        enable_hybrid_retrieval=bool(meta_raw.get("enable_hybrid_retrieval", False)),
    )
    return BenchmarkExportArtifacts(
        metadata=metadata,
        json_bytes=base64.standard_b64decode(str(data.get("json_base64") or "")),
        json_filename=str(data.get("json_filename") or "benchmark.json"),
        csv_bytes=base64.standard_b64decode(str(data.get("csv_base64") or "")),
        csv_filename=str(data.get("csv_filename") or "benchmark.csv"),
        markdown_bytes=base64.standard_b64decode(str(data.get("markdown_base64") or "")),
        markdown_filename=str(data.get("markdown_filename") or "benchmark.md"),
        run_id=data.get("run_id"),
    )


def qa_generate_result_from_api_dict(data: dict[str, Any]) -> dict[str, Any]:
    """Shape expected by :func:`src.ui.evaluation_gold_qa_tab._render_dataset_generation_result`."""
    created = [qa_dataset_entry_from_api_dict(e) for e in (data.get("created_entries") or [])]
    return {
        "generation_mode": data.get("generation_mode") or "append",
        "deleted_existing_entries": int(data.get("deleted_existing_entries") or 0),
        "created_entries": created,
        "skipped_duplicates": list(data.get("skipped_duplicates") or []),
    }
