"""
Map domain / application results to JSON-safe dicts for FastAPI response models.

**Backward compatibility:** response key names and nested document shape (``page_content``,
``metadata``) are unchanged from earlier releases. Framework-specific handling lives in
:mod:`src.infrastructure.web.json_normalization` — this module stays free of LangChain imports.
"""

from __future__ import annotations

import base64
from typing import Any

from dataclasses import asdict

from src.application.evaluation.benchmark_export_dtos import BenchmarkExportArtifacts
from src.application.settings.dtos import EffectiveRetrievalSettingsView
from src.domain.benchmark_result import BenchmarkResult
from src.domain.pipeline_payloads import PipelineBuildResult
from src.domain.rag_response import RAGResponse
from src.infrastructure.web.json_normalization import jsonify_value


def pipeline_build_result_to_api_dict(result: PipelineBuildResult) -> dict[str, Any]:
    return jsonify_value(result.to_dict())


def preview_summary_recall_to_api_dict(preview: dict[str, Any] | None) -> dict[str, Any] | None:
    if preview is None:
        return None
    return jsonify_value(preview)


def rag_response_to_api_dict(response: RAGResponse) -> dict[str, Any]:
    return {
        "question": response.question,
        "answer": response.answer,
        "source_documents": jsonify_value(response.source_documents),
        "raw_assets": jsonify_value(response.raw_assets),
        "prompt_sources": jsonify_value(response.prompt_sources),
        "confidence": float(response.confidence),
        "latency": jsonify_value(response.latency) if response.latency is not None else None,
    }


def ingest_document_result_to_api_dict(result: Any) -> dict[str, Any]:
    return {
        "raw_assets": jsonify_value(result.raw_assets),
        "replacement_info": jsonify_value(result.replacement_info),
        "diagnostics": result.diagnostics.to_dict(),
    }


def benchmark_result_to_api_dict(result: BenchmarkResult) -> dict[str, Any]:
    """Normalize benchmark payloads so row ``data`` cannot leak non-JSON types."""
    return jsonify_value(result.to_dict())


def effective_retrieval_settings_view_to_api_dict(view: EffectiveRetrievalSettingsView) -> dict[str, Any]:
    return {
        "preferences": asdict(view.preferences),
        "effective_retrieval": asdict(view.effective_retrieval),
    }


def benchmark_export_artifacts_to_api_dict(artifacts: BenchmarkExportArtifacts) -> dict[str, Any]:
    """Map export bytes to JSON-safe fields for :class:`~apps.api.schemas.evaluation.BenchmarkExportResponse`."""
    return {
        "metadata": artifacts.metadata.to_dict(),
        "json_base64": base64.standard_b64encode(artifacts.json_bytes).decode("ascii"),
        "json_filename": artifacts.json_filename,
        "csv_base64": base64.standard_b64encode(artifacts.csv_bytes).decode("ascii"),
        "csv_filename": artifacts.csv_filename,
        "markdown_base64": base64.standard_b64encode(artifacts.markdown_bytes).decode("ascii"),
        "markdown_filename": artifacts.markdown_filename,
        "run_id": artifacts.run_id,
    }
