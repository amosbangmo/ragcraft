"""
HTTP / JSON wire payloads: application-layer boundary between domain objects and REST clients.

Maps domain and application results into **stable, JSON-serializable** structures consumed by
``interfaces.http.schemas`` Pydantic models. LangChain ``Document`` instances and other non-JSON types
are normalized via :func:`application.json_wire.jsonify_value` here — not in FastAPI routers.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, cast

from application.common.summary_recall_preview import SummaryRecallPreviewDTO
from application.dto.benchmark_export import BenchmarkExportArtifacts
from application.dto.evaluation import GenerateQaDatasetResult
from application.dto.ingestion import IngestDocumentResult
from application.dto.retrieval_comparison import RetrievalModeComparisonResult
from application.dto.settings import EffectiveRetrievalSettingsView
from application.http.wire.json_wire import jsonify_value
from domain.common.ingestion_diagnostics import IngestionDiagnostics
from domain.evaluation.benchmark_result import BenchmarkResult
from domain.rag.pipeline_latency import PipelineLatency
from domain.rag.pipeline_payloads import PipelineBuildResult
from domain.rag.rag_response import RAGResponse


@dataclass(frozen=True)
class RagAnswerWirePayload:
    """Normalized /chat/ask answer fields (no transport ``status`` — router adds that)."""

    question: str
    answer: str
    source_documents: list[dict[str, Any]]
    raw_assets: list[dict[str, Any]]
    prompt_sources: list[dict[str, Any]]
    confidence: float
    latency: PipelineLatency | None

    @classmethod
    def from_rag_response(cls, response: RAGResponse) -> RagAnswerWirePayload:
        return cls(
            question=response.question,
            answer=response.answer,
            source_documents=cast(list[dict[str, Any]], jsonify_value(response.source_documents)),
            raw_assets=cast(list[dict[str, Any]], jsonify_value(response.raw_assets)),
            prompt_sources=cast(list[dict[str, Any]], jsonify_value(response.prompt_sources)),
            confidence=float(response.confidence),
            latency=response.latency,
        )

    def as_json_dict(self) -> dict[str, Any]:
        latency_out: dict[str, Any] | None
        if self.latency is None:
            latency_out = None
        else:
            latency_out = cast(dict[str, Any], jsonify_value(self.latency.to_dict()))
        return {
            "question": self.question,
            "answer": self.answer,
            "source_documents": list(self.source_documents),
            "raw_assets": list(self.raw_assets),
            "prompt_sources": list(self.prompt_sources),
            "confidence": self.confidence,
            "latency": latency_out,
        }


@dataclass(frozen=True)
class PipelineSnapshotWirePayload:
    """Full pipeline inspect JSON (documents as page_content + metadata dicts)."""

    pipeline: dict[str, Any]

    @classmethod
    def from_build_result(cls, result: PipelineBuildResult) -> PipelineSnapshotWirePayload:
        return cls(pipeline=cast(dict[str, Any], jsonify_value(result.to_dict())))

    def as_json_dict(self) -> dict[str, Any]:
        return {"pipeline": self.pipeline}


@dataclass(frozen=True)
class PreviewSummaryRecallWirePayload:
    """Summary-recall preview dict after JSON normalization (HTTP wire only)."""

    preview: dict[str, Any] | None

    @classmethod
    def from_preview_dto(
        cls, preview: SummaryRecallPreviewDTO | None
    ) -> PreviewSummaryRecallWirePayload:
        if preview is None:
            return cls(preview=None)
        wire: dict[str, Any] = {
            "rewritten_question": preview.rewritten_question,
            "recalled_summary_docs": cast(Any, jsonify_value(preview.recalled_summary_docs)),
            "vector_summary_docs": cast(Any, jsonify_value(preview.vector_summary_docs)),
            "bm25_summary_docs": cast(Any, jsonify_value(preview.bm25_summary_docs)),
            "retrieval_mode": preview.retrieval_mode,
            "query_rewrite_enabled": preview.query_rewrite_enabled,
            "hybrid_retrieval_enabled": preview.hybrid_retrieval_enabled,
            "use_adaptive_retrieval": preview.use_adaptive_retrieval,
        }
        return cls(preview=wire)

    def as_json_dict(self) -> dict[str, Any]:
        return {"preview": self.preview}


@dataclass(frozen=True)
class IngestDocumentWirePayload:
    raw_assets: list[dict[str, Any]]
    replacement_info: dict[str, Any]
    diagnostics: dict[str, Any]

    @classmethod
    def from_ingest_result(cls, result: IngestDocumentResult) -> IngestDocumentWirePayload:
        return cls(
            raw_assets=cast(
                list[dict[str, Any]],
                jsonify_value([a.upsert_kwargs() for a in result.raw_assets]),
            ),
            replacement_info=cast(
                dict[str, Any], jsonify_value(result.replacement_info.to_wire_dict())
            ),
            diagnostics=result.diagnostics.to_dict(),
        )

    @classmethod
    def from_duck_typed_ingest_result(cls, result: Any) -> IngestDocumentWirePayload:
        """For tests or adapters that mimic :class:`~application.dto.ingestion.IngestDocumentResult`."""
        raw_assets = getattr(result, "raw_assets", [])
        replacement_info = getattr(result, "replacement_info", None)
        diagnostics = getattr(result, "diagnostics", None)
        if not isinstance(diagnostics, IngestionDiagnostics):
            raise TypeError("result.diagnostics must be IngestionDiagnostics")
        if hasattr(replacement_info, "to_wire_dict"):
            repl_wire = replacement_info.to_wire_dict()
        else:
            repl_wire = replacement_info or {}
        if raw_assets and hasattr(raw_assets[0], "upsert_kwargs"):
            raw_wire = [a.upsert_kwargs() for a in raw_assets]  # type: ignore[union-attr]
        else:
            raw_wire = list(raw_assets)
        return cls(
            raw_assets=cast(list[dict[str, Any]], jsonify_value(raw_wire)),
            replacement_info=cast(dict[str, Any], jsonify_value(repl_wire)),
            diagnostics=diagnostics.to_dict(),
        )

    def as_json_dict(self) -> dict[str, Any]:
        return {
            "raw_assets": list(self.raw_assets),
            "replacement_info": dict(self.replacement_info),
            "diagnostics": dict(self.diagnostics),
        }


@dataclass(frozen=True)
class EffectiveRetrievalSettingsWirePayload:
    preferences: dict[str, Any]
    effective_retrieval: dict[str, Any]

    @classmethod
    def from_view(
        cls, view: EffectiveRetrievalSettingsView
    ) -> EffectiveRetrievalSettingsWirePayload:
        return cls(
            preferences=cast(dict[str, Any], asdict(view.preferences)),
            effective_retrieval=cast(dict[str, Any], asdict(view.effective_retrieval)),
        )

    def as_json_dict(self) -> dict[str, Any]:
        return {
            "preferences": dict(self.preferences),
            "effective_retrieval": dict(self.effective_retrieval),
        }


@dataclass(frozen=True)
class BenchmarkRunWirePayload:
    """Stable benchmark aggregate for :class:`~interfaces.http.schemas.evaluation.BenchmarkResultResponse`."""

    summary: dict[str, Any]
    rows: list[dict[str, Any]]
    correlations: dict[str, Any] | None
    failures: dict[str, Any] | None
    multimodal_metrics: dict[str, Any] | None
    auto_debug: list[dict[str, str]] | None
    run_id: str | None

    @classmethod
    def from_benchmark_result(cls, result: BenchmarkResult) -> BenchmarkRunWirePayload:
        normalized = cast(dict[str, Any], jsonify_value(result.to_dict()))
        return cls(
            summary=cast(dict[str, Any], normalized.get("summary") or {}),
            rows=cast(list[dict[str, Any]], normalized.get("rows") or []),
            correlations=cast(dict[str, Any] | None, normalized.get("correlations")),
            failures=cast(dict[str, Any] | None, normalized.get("failures")),
            multimodal_metrics=cast(dict[str, Any] | None, normalized.get("multimodal_metrics")),
            auto_debug=cast(list[dict[str, str]] | None, normalized.get("auto_debug")),
            run_id=cast(str | None, normalized.get("run_id")),
        )

    def as_json_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "summary": dict(self.summary),
            "rows": list(self.rows),
        }
        if self.correlations is not None:
            out["correlations"] = dict(self.correlations)
        if self.failures is not None:
            out["failures"] = dict(self.failures)
        if self.multimodal_metrics is not None:
            out["multimodal_metrics"] = dict(self.multimodal_metrics)
        if self.auto_debug is not None:
            out["auto_debug"] = list(self.auto_debug)
        if self.run_id is not None:
            out["run_id"] = self.run_id
        return out


@dataclass(frozen=True)
class RetrievalComparisonWirePayload:
    """Normalized retrieval A/B comparison table (FAISS vs hybrid)."""

    result: RetrievalModeComparisonResult

    @classmethod
    def from_comparison_result(
        cls, result: RetrievalModeComparisonResult
    ) -> RetrievalComparisonWirePayload:
        return cls(result=result)

    def as_json_dict(self) -> dict[str, Any]:
        return {
            "questions": list(self.result.questions),
            "summary": self.result.summary.to_json_summary(),
            "rows": [row.to_json_row() for row in self.result.rows],
        }


@dataclass(frozen=True)
class QaDatasetGenerateWirePayload:
    """Maps :class:`~application.evaluation.dtos.GenerateQaDatasetResult` to QA generate API JSON."""

    generation_mode: str
    deleted_existing_entries: int
    created_entries: list[dict[str, Any]]
    skipped_duplicates: list[str]
    requested_questions: int
    raw_generated_count: int

    @classmethod
    def from_result(cls, result: GenerateQaDatasetResult) -> QaDatasetGenerateWirePayload:
        return cls(
            generation_mode=result.generation_mode,
            deleted_existing_entries=result.deleted_existing_entries,
            created_entries=[e.to_dict() for e in result.created_entries],
            skipped_duplicates=list(result.skipped_duplicates),
            requested_questions=result.requested_questions,
            raw_generated_count=result.raw_generated_count,
        )

    def as_json_dict(self) -> dict[str, Any]:
        return {
            "generation_mode": self.generation_mode,
            "deleted_existing_entries": self.deleted_existing_entries,
            "created_entries": list(self.created_entries),
            "skipped_duplicates": list(self.skipped_duplicates),
            "requested_questions": self.requested_questions,
            "raw_generated_count": self.raw_generated_count,
        }


@dataclass(frozen=True)
class BenchmarkExportBundleWirePayload:
    """Wrapper for ``export_format=all`` JSON (base64 artifacts + metadata)."""

    bundle: dict[str, Any]

    @classmethod
    def from_artifacts(
        cls, artifacts: BenchmarkExportArtifacts
    ) -> BenchmarkExportBundleWirePayload:
        return cls(bundle=dict(artifacts.to_http_bundle_dict()))

    def as_json_dict(self) -> dict[str, Any]:
        return dict(self.bundle)


# --- Thin callables (stable names for ``interfaces.http.schemas.serialization`` re-exports) ---


def rag_response_to_wire_dict(response: RAGResponse) -> dict[str, Any]:
    return RagAnswerWirePayload.from_rag_response(response).as_json_dict()


def pipeline_build_result_to_wire_dict(result: PipelineBuildResult) -> dict[str, Any]:
    return PipelineSnapshotWirePayload.from_build_result(result).pipeline


def preview_summary_recall_to_wire_dict(
    preview: SummaryRecallPreviewDTO | None,
) -> dict[str, Any] | None:
    return PreviewSummaryRecallWirePayload.from_preview_dto(preview).preview


def ingest_document_result_to_wire_dict(result: Any) -> dict[str, Any]:
    if isinstance(result, IngestDocumentResult):
        return IngestDocumentWirePayload.from_ingest_result(result).as_json_dict()
    return IngestDocumentWirePayload.from_duck_typed_ingest_result(result).as_json_dict()


def effective_retrieval_settings_view_to_wire_dict(
    view: EffectiveRetrievalSettingsView,
) -> dict[str, Any]:
    return EffectiveRetrievalSettingsWirePayload.from_view(view).as_json_dict()


def benchmark_result_to_wire_dict(result: BenchmarkResult) -> dict[str, Any]:
    return BenchmarkRunWirePayload.from_benchmark_result(result).as_json_dict()


def retrieval_comparison_to_wire_dict(result: RetrievalModeComparisonResult) -> dict[str, Any]:
    return RetrievalComparisonWirePayload.from_comparison_result(result).as_json_dict()


def generate_qa_dataset_result_to_wire_dict(result: GenerateQaDatasetResult) -> dict[str, Any]:
    return QaDatasetGenerateWirePayload.from_result(result).as_json_dict()


def benchmark_export_bundle_to_wire_dict(artifacts: BenchmarkExportArtifacts) -> dict[str, Any]:
    return BenchmarkExportBundleWirePayload.from_artifacts(artifacts).as_json_dict()
