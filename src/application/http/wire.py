"""
HTTP / JSON wire payloads: application-layer boundary between domain objects and REST clients.

Maps domain and application results into **stable, JSON-serializable** structures consumed by
``apps.api.schemas`` Pydantic models. LangChain ``Document`` instances and other non-JSON types
are normalized via :func:`src.application.json_wire.jsonify_value` here — not in FastAPI routers.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, cast

from src.application.ingestion.dtos import IngestDocumentResult
from src.application.settings.dtos import EffectiveRetrievalSettingsView
from src.domain.benchmark_result import BenchmarkResult
from src.domain.ingestion_diagnostics import IngestionDiagnostics
from src.domain.pipeline_payloads import PipelineBuildResult
from src.domain.rag_response import RAGResponse
from src.application.json_wire import jsonify_value


@dataclass(frozen=True)
class RagAnswerWirePayload:
    """Normalized /chat/ask answer fields (no transport ``status`` — router adds that)."""

    question: str
    answer: str
    source_documents: list[dict[str, Any]]
    raw_assets: list[dict[str, Any]]
    prompt_sources: list[dict[str, Any]]
    confidence: float
    latency: dict[str, Any] | None

    @classmethod
    def from_rag_response(cls, response: RAGResponse) -> RagAnswerWirePayload:
        return cls(
            question=response.question,
            answer=response.answer,
            source_documents=cast(list[dict[str, Any]], jsonify_value(response.source_documents)),
            raw_assets=cast(list[dict[str, Any]], jsonify_value(response.raw_assets)),
            prompt_sources=cast(list[dict[str, Any]], jsonify_value(response.prompt_sources)),
            confidence=float(response.confidence),
            latency=cast(dict[str, Any] | None, jsonify_value(response.latency))
            if response.latency is not None
            else None,
        )

    def as_json_dict(self) -> dict[str, Any]:
        return {
            "question": self.question,
            "answer": self.answer,
            "source_documents": list(self.source_documents),
            "raw_assets": list(self.raw_assets),
            "prompt_sources": list(self.prompt_sources),
            "confidence": self.confidence,
            "latency": self.latency,
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
    """Summary-recall preview dict after JSON normalization."""

    preview: dict[str, Any] | None

    @classmethod
    def from_preview_dict(cls, preview: dict[str, Any] | None) -> PreviewSummaryRecallWirePayload:
        if preview is None:
            return cls(preview=None)
        return cls(preview=cast(dict[str, Any], jsonify_value(preview)))

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
            raw_assets=cast(list[dict[str, Any]], jsonify_value(result.raw_assets)),
            replacement_info=cast(dict[str, Any], jsonify_value(result.replacement_info or {})),
            diagnostics=result.diagnostics.to_dict(),
        )

    @classmethod
    def from_duck_typed_ingest_result(cls, result: Any) -> IngestDocumentWirePayload:
        """For tests or adapters that mimic :class:`~src.application.ingestion.dtos.IngestDocumentResult`."""
        raw_assets = getattr(result, "raw_assets", [])
        replacement_info = getattr(result, "replacement_info", {}) or {}
        diagnostics = getattr(result, "diagnostics", None)
        if not isinstance(diagnostics, IngestionDiagnostics):
            raise TypeError("result.diagnostics must be IngestionDiagnostics")
        return cls(
            raw_assets=cast(list[dict[str, Any]], jsonify_value(raw_assets)),
            replacement_info=cast(dict[str, Any], jsonify_value(replacement_info)),
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
    def from_view(cls, view: EffectiveRetrievalSettingsView) -> EffectiveRetrievalSettingsWirePayload:
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
    """Stable benchmark aggregate for :class:`~apps.api.schemas.evaluation.BenchmarkResultResponse`."""

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

    questions: list[str]
    summary: dict[str, Any]
    rows: list[dict[str, Any]]

    @classmethod
    def from_service_dict(cls, raw: dict[str, Any]) -> RetrievalComparisonWirePayload:
        normalized = cast(dict[str, Any], jsonify_value(dict(raw)))
        return cls(
            questions=list(normalized.get("questions") or []),
            summary=cast(dict[str, Any], normalized.get("summary") or {}),
            rows=cast(list[dict[str, Any]], normalized.get("rows") or []),
        )

    def as_json_dict(self) -> dict[str, Any]:
        return {
            "questions": list(self.questions),
            "summary": dict(self.summary),
            "rows": list(self.rows),
        }


# --- Thin callables (stable names for ``apps.api.schemas.serialization`` re-exports) ---


def rag_response_to_wire_dict(response: RAGResponse) -> dict[str, Any]:
    return RagAnswerWirePayload.from_rag_response(response).as_json_dict()


def pipeline_build_result_to_wire_dict(result: PipelineBuildResult) -> dict[str, Any]:
    return PipelineSnapshotWirePayload.from_build_result(result).pipeline


def preview_summary_recall_to_wire_dict(preview: dict[str, Any] | None) -> dict[str, Any] | None:
    payload = PreviewSummaryRecallWirePayload.from_preview_dict(preview)
    return payload.preview


def ingest_document_result_to_wire_dict(result: Any) -> dict[str, Any]:
    if isinstance(result, IngestDocumentResult):
        return IngestDocumentWirePayload.from_ingest_result(result).as_json_dict()
    return IngestDocumentWirePayload.from_duck_typed_ingest_result(result).as_json_dict()


def effective_retrieval_settings_view_to_wire_dict(view: EffectiveRetrievalSettingsView) -> dict[str, Any]:
    return EffectiveRetrievalSettingsWirePayload.from_view(view).as_json_dict()


def benchmark_result_to_wire_dict(result: BenchmarkResult) -> dict[str, Any]:
    return BenchmarkRunWirePayload.from_benchmark_result(result).as_json_dict()


def retrieval_comparison_to_wire_dict(raw: dict[str, Any]) -> dict[str, Any]:
    return RetrievalComparisonWirePayload.from_service_dict(raw).as_json_dict()
