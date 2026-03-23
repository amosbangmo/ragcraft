"""
Map domain and persistence shapes to HTTP response DTOs (transport boundary).

Routers should prefer these helpers over ``model_validate(domain.to_dict())`` so the API contract
stays explicit when domain serialization evolves.
"""

from __future__ import annotations

from typing import Any

from application.dto.auth import UserProfileSummary
from application.dto.projects import ProjectDocumentDetailRow
from domain.common.retrieval_query_log_record import RetrievalQueryLogRecord
from domain.evaluation.manual_evaluation_result import ManualEvaluationResult
from domain.evaluation.qa_dataset_entry import QADatasetEntry
from domain.projects.documents.stored_multimodal_asset import StoredMultimodalAsset
from interfaces.http.schemas.evaluation import (
    ManualEvaluationResponse,
    QaDatasetEntryResponse,
    RetrievalQueryLogEntry,
)
from interfaces.http.schemas.projects import DocumentAssetRow, ProjectDocumentDetailItem
from interfaces.http.schemas.users import UserMeResponse


def user_profile_summary_to_me(user: UserProfileSummary) -> UserMeResponse:
    return UserMeResponse(
        username=user.username,
        user_id=user.user_id,
        display_name=user.display_name,
        avatar_path=user.avatar_path,
        created_at=user.created_at,
    )


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


def manual_evaluation_result_to_response(
    result: ManualEvaluationResult,
) -> ManualEvaluationResponse:
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


def retrieval_query_log_record_to_entry(record: RetrievalQueryLogRecord) -> RetrievalQueryLogEntry:
    rs = record.retrieval_strategy
    rs_out: dict[str, Any] | None = None
    if rs is not None:
        rs_out = {}
        if rs.k is not None:
            rs_out["k"] = rs.k
        if rs.use_hybrid is not None:
            rs_out["use_hybrid"] = rs.use_hybrid
        if rs.apply_filters is not None:
            rs_out["apply_filters"] = rs.apply_filters
        if not rs_out:
            rs_out = None
    return RetrievalQueryLogEntry(
        question=record.question,
        rewritten_query=record.rewritten_query,
        project_id=record.project_id,
        user_id=record.user_id,
        retrieval_mode=record.retrieval_mode,
        confidence=record.confidence,
        timestamp=record.timestamp,
        selected_doc_ids=record.selected_doc_ids,
        retrieved_doc_ids=record.retrieved_doc_ids,
        answer=record.answer,
        hybrid_retrieval_enabled=record.hybrid_retrieval_enabled,
        query_intent=record.query_intent,
        retrieval_strategy=rs_out,
        latency_ms=record.latency_ms,
        query_rewrite_ms=record.query_rewrite_ms,
        retrieval_ms=record.retrieval_ms,
        reranking_ms=record.reranking_ms,
        prompt_build_ms=record.prompt_build_ms,
        answer_generation_ms=record.answer_generation_ms,
        total_latency_ms=record.total_latency_ms,
        context_compression_chars_before=record.context_compression_chars_before,
        context_compression_chars_after=record.context_compression_chars_after,
        context_compression_ratio=record.context_compression_ratio,
        section_expansion_count=record.section_expansion_count,
        expanded_assets_count=record.expanded_assets_count,
        table_aware_qa_enabled=record.table_aware_qa_enabled,
    )


def document_asset_row_from_stored(asset: StoredMultimodalAsset) -> DocumentAssetRow:
    return DocumentAssetRow(
        doc_id=asset.doc_id,
        user_id=asset.user_id,
        project_id=asset.project_id,
        source_file=asset.source_file,
        content_type=asset.content_type,
        raw_content=asset.raw_content,
        summary=asset.summary,
        metadata=dict(asset.metadata),
        created_at=asset.created_at,
    )


def document_asset_row_from_store(raw: dict[str, Any]) -> DocumentAssetRow:
    return document_asset_row_from_stored(StoredMultimodalAsset.from_mapping(raw))


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


def project_document_detail_row_to_item(row: ProjectDocumentDetailRow) -> ProjectDocumentDetailItem:
    return project_document_detail_item(
        name=row.name,
        project_id=row.project_id,
        path=row.path,
        size_bytes=row.size_bytes,
        asset_count=row.asset_count,
        text_count=row.text_count,
        table_count=row.table_count,
        image_count=row.image_count,
        latest_ingested_at=row.latest_ingested_at,
    )
