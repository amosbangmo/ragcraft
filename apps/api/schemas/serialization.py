"""
Re-exports of wire mappers for callers that still import this module (e.g. tests).

* Canonical wire types: :mod:`src.application.http.wire`.
* Response assembly from domain rows: :mod:`apps.api.schemas.mappers`.
"""

from __future__ import annotations

from typing import Any

from src.application.evaluation.benchmark_export_dtos import BenchmarkExportArtifacts
from src.application.http.wire import (
    benchmark_result_to_wire_dict,
    effective_retrieval_settings_view_to_wire_dict,
    ingest_document_result_to_wire_dict,
    pipeline_build_result_to_wire_dict,
    preview_summary_recall_to_wire_dict,
    rag_response_to_wire_dict,
)
from src.application.settings.dtos import EffectiveRetrievalSettingsView
from src.domain.benchmark_result import BenchmarkResult
from src.domain.pipeline_payloads import PipelineBuildResult
from src.domain.rag_response import RAGResponse


def pipeline_build_result_to_api_dict(result: PipelineBuildResult) -> dict[str, Any]:
    return pipeline_build_result_to_wire_dict(result)


def preview_summary_recall_to_api_dict(preview: dict[str, Any] | None) -> dict[str, Any] | None:
    return preview_summary_recall_to_wire_dict(preview)


def rag_response_to_api_dict(response: RAGResponse) -> dict[str, Any]:
    return rag_response_to_wire_dict(response)


def ingest_document_result_to_api_dict(result: Any) -> dict[str, Any]:
    return ingest_document_result_to_wire_dict(result)


def benchmark_result_to_api_dict(result: BenchmarkResult) -> dict[str, Any]:
    return benchmark_result_to_wire_dict(result)


def effective_retrieval_settings_view_to_api_dict(view: EffectiveRetrievalSettingsView) -> dict[str, Any]:
    return effective_retrieval_settings_view_to_wire_dict(view)


def benchmark_export_artifacts_to_api_dict(artifacts: BenchmarkExportArtifacts) -> dict[str, Any]:
    return artifacts.to_http_bundle_dict()
