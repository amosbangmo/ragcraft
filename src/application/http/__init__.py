"""Application → HTTP/JSON wire boundary (stable payloads for REST clients)."""

from src.application.http.wire import (
    BenchmarkRunWirePayload,
    EffectiveRetrievalSettingsWirePayload,
    IngestDocumentWirePayload,
    PipelineSnapshotWirePayload,
    PreviewSummaryRecallWirePayload,
    RagAnswerWirePayload,
    RetrievalComparisonWirePayload,
    benchmark_result_to_wire_dict,
    effective_retrieval_settings_view_to_wire_dict,
    ingest_document_result_to_wire_dict,
    pipeline_build_result_to_wire_dict,
    preview_summary_recall_to_wire_dict,
    rag_response_to_wire_dict,
    retrieval_comparison_to_wire_dict,
)

__all__ = [
    "BenchmarkRunWirePayload",
    "EffectiveRetrievalSettingsWirePayload",
    "IngestDocumentWirePayload",
    "PipelineSnapshotWirePayload",
    "PreviewSummaryRecallWirePayload",
    "RagAnswerWirePayload",
    "RetrievalComparisonWirePayload",
    "benchmark_result_to_wire_dict",
    "effective_retrieval_settings_view_to_wire_dict",
    "ingest_document_result_to_wire_dict",
    "pipeline_build_result_to_wire_dict",
    "preview_summary_recall_to_wire_dict",
    "rag_response_to_wire_dict",
    "retrieval_comparison_to_wire_dict",
]
