"""Convert domain objects (e.g. LangChain documents) to JSON-safe structures for API responses."""

from __future__ import annotations

from typing import Any

from langchain_core.documents import Document

from src.domain.pipeline_payloads import PipelineBuildResult
from src.domain.rag_response import RAGResponse


def jsonify_value(value: Any) -> Any:
    if isinstance(value, Document):
        return {
            "page_content": value.page_content,
            "metadata": {str(k): jsonify_value(v) for k, v in dict(value.metadata or {}).items()},
        }
    if isinstance(value, dict):
        return {str(k): jsonify_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [jsonify_value(x) for x in value]
    if isinstance(value, tuple):
        return [jsonify_value(x) for x in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if hasattr(value, "value") and not isinstance(value, type):
        inner = getattr(value, "value")
        if isinstance(inner, (str, int, float, bool)):
            return inner
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return jsonify_value(value.to_dict())
    return str(value)


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
