"""
Map domain and persistence shapes to HTTP response DTOs (transport boundary).

Routers should prefer these helpers over ``model_validate(domain.to_dict())`` so the API contract
stays explicit when domain serialization evolves.
"""

from __future__ import annotations

from typing import Any

from src.domain.manual_evaluation_result import ManualEvaluationResult
from src.domain.qa_dataset_entry import QADatasetEntry

from apps.api.schemas.evaluation import (
    ManualEvaluationResponse,
    QaDatasetEntryResponse,
    RetrievalQueryLogEntry,
)
from apps.api.schemas.projects import DocumentAssetRow, ProjectDocumentDetailItem


def qa_dataset_entry_to_response(entry: QADatasetEntry) -> QaDatasetEntryResponse:
    return QaDatasetEntryResponse(
        id=entry.id,
        user_id=entry.user_id,
        project_id=entry.project_id,
        question=entry.question,
        expected_answer=entry.expected_answer,
        expected_doc_ids=list(entry.expected_doc_ids),
        expected_sources=list(entry.expected_sources),
        created_at=entry.created_at,
        updated_at=entry.updated_at,
    )


def manual_evaluation_result_to_response(result: ManualEvaluationResult) -> ManualEvaluationResponse:
    return ManualEvaluationResponse(
        question=result.question,
        answer=result.answer,
        expected_answer=result.expected_answer,
        confidence=result.confidence,
        pipeline_failed=result.pipeline_failed,
        judge_failed=result.judge_failed,
        judge_failure_reason=result.judge_failure_reason,
        prompt_sources=list(result.prompt_sources),
        raw_assets=list(result.raw_assets),
        answer_quality=result.answer_quality.to_dict() if result.answer_quality else None,
        answer_citation_quality=result.answer_citation_quality.to_dict()
        if result.answer_citation_quality
        else None,
        prompt_source_quality=result.prompt_source_quality.to_dict()
        if result.prompt_source_quality
        else None,
        retrieval_quality=result.retrieval_quality.to_dict() if result.retrieval_quality else None,
        pipeline_signals=result.pipeline_signals.to_dict() if result.pipeline_signals else None,
        expectation_comparison=result.expectation_comparison.to_dict()
        if result.expectation_comparison
        else None,
        detected_issues=list(result.detected_issues),
    )


def retrieval_query_log_rows_to_entries(rows: list[dict[str, Any]]) -> list[RetrievalQueryLogEntry]:
    return [RetrievalQueryLogEntry.model_validate(row) for row in rows]


def document_asset_row_from_store(raw: dict[str, Any]) -> DocumentAssetRow:
    md = raw.get("metadata")
    return DocumentAssetRow(
        doc_id=str(raw.get("doc_id") or ""),
        user_id=str(raw.get("user_id") or ""),
        project_id=str(raw.get("project_id") or ""),
        source_file=str(raw.get("source_file") or ""),
        content_type=str(raw.get("content_type") or "unknown"),
        raw_content="" if raw.get("raw_content") is None else str(raw.get("raw_content")),
        summary="" if raw.get("summary") is None else str(raw.get("summary")),
        metadata=dict(md) if isinstance(md, dict) else {},
        created_at=None if raw.get("created_at") is None else str(raw.get("created_at")),
    )


def project_document_detail_item(
    *,
    name: str,
    project_id: str,
    path: str,
    size_bytes: int,
    asset_count: int,
    text_count: int,
    table_count: int,
    image_count: int,
    latest_ingested_at: str | None,
) -> ProjectDocumentDetailItem:
    return ProjectDocumentDetailItem(
        name=name,
        project_id=project_id,
        path=path,
        size_bytes=size_bytes,
        asset_count=asset_count,
        text_count=text_count,
        table_count=table_count,
        image_count=image_count,
        latest_ingested_at=latest_ingested_at,
    )
