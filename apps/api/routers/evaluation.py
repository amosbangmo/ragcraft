"""
Evaluation, QA dataset, and retrieval log HTTP API.

Handlers call application use cases only; bodies use explicit Pydantic models.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query

from apps.api.dependencies import (
    get_create_qa_dataset_entry_use_case,
    get_delete_qa_dataset_entry_use_case,
    get_generate_qa_dataset_use_case,
    get_list_qa_dataset_entries_use_case,
    get_list_retrieval_query_logs_use_case,
    get_request_user_id,
    get_run_gold_qa_dataset_evaluation_use_case,
    get_run_manual_evaluation_use_case,
    get_update_qa_dataset_entry_use_case,
)
from apps.api.schemas.serialization import benchmark_result_to_api_dict
from apps.api.schemas.evaluation import (
    BenchmarkExportStubResponse,
    BenchmarkResultResponse,
    DatasetBenchmarkRunRequest,
    ManualEvaluationRequest,
    ManualEvaluationResponse,
    QaDatasetEntryCreateRequest,
    QaDatasetEntryDeleteResponse,
    QaDatasetEntryListResponse,
    QaDatasetEntryResponse,
    QaDatasetEntryUpdateRequest,
    QaDatasetGenerateRequest,
    QaDatasetGenerateResponse,
    RetrievalLogsResponse,
)
from src.application.evaluation.dtos import GenerateQaDatasetCommand
from src.domain.qa_dataset_entry import QADatasetEntry

router = APIRouter(prefix="/evaluation", tags=["evaluation"])


def _entry_to_response(entry: QADatasetEntry) -> QaDatasetEntryResponse:
    return QaDatasetEntryResponse.model_validate(entry.to_dict())


@router.post(
    "/manual",
    response_model=ManualEvaluationResponse,
    summary="Run manual evaluation for one question",
    responses={
        502: {"description": "LLM judge or model failure"},
        503: {"description": "Retrieval or infrastructure failure"},
    },
)
def post_manual_evaluation(
    body: ManualEvaluationRequest,
    user_id: Annotated[str, Depends(get_request_user_id)],
    use_case: Annotated[Any, Depends(get_run_manual_evaluation_use_case)],
) -> ManualEvaluationResponse:
    """
    Evaluate a single question with optional gold fields (parity with Streamlit manual eval).

    Example::

        {"project_id": "demo", "question": "What is the refund policy?"}
    """
    result = use_case.execute(
        user_id=user_id,
        project_id=body.project_id,
        question=body.question,
        expected_answer=body.expected_answer,
        expected_doc_ids=body.expected_doc_ids or None,
        expected_sources=body.expected_sources or None,
        enable_query_rewrite_override=body.enable_query_rewrite_override,
        enable_hybrid_retrieval_override=body.enable_hybrid_retrieval_override,
    )
    return ManualEvaluationResponse.model_validate(result.to_dict())


@router.post(
    "/dataset/run",
    response_model=BenchmarkResultResponse,
    summary="Run gold QA dataset benchmark",
    responses={
        502: {"description": "LLM judge or model failure"},
        503: {"description": "Retrieval or infrastructure failure"},
    },
)
def post_dataset_benchmark_run(
    body: DatasetBenchmarkRunRequest,
    user_id: Annotated[str, Depends(get_request_user_id)],
    use_case: Annotated[Any, Depends(get_run_gold_qa_dataset_evaluation_use_case)],
) -> BenchmarkResultResponse:
    """Runs the full saved QA dataset for the project with fixed retrieval flags per row."""
    result = use_case.execute(
        user_id=user_id,
        project_id=body.project_id,
        enable_query_rewrite=body.enable_query_rewrite,
        enable_hybrid_retrieval=body.enable_hybrid_retrieval,
    )
    return BenchmarkResultResponse.model_validate(benchmark_result_to_api_dict(result))


@router.get(
    "/dataset/entries",
    response_model=QaDatasetEntryListResponse,
    summary="List QA dataset entries",
)
def get_dataset_entries(
    user_id: Annotated[str, Depends(get_request_user_id)],
    project_id: Annotated[str, Query(min_length=1)],
    use_case: Annotated[Any, Depends(get_list_qa_dataset_entries_use_case)],
) -> QaDatasetEntryListResponse:
    rows = use_case.execute(user_id=user_id, project_id=project_id)
    return QaDatasetEntryListResponse(entries=[_entry_to_response(e) for e in rows])


@router.post(
    "/dataset/entries",
    response_model=QaDatasetEntryResponse,
    status_code=201,
    summary="Create QA dataset entry",
)
def post_dataset_entry(
    body: QaDatasetEntryCreateRequest,
    user_id: Annotated[str, Depends(get_request_user_id)],
    use_case: Annotated[Any, Depends(get_create_qa_dataset_entry_use_case)],
) -> QaDatasetEntryResponse:
    entry = use_case.execute(
        user_id=user_id,
        project_id=body.project_id,
        question=body.question,
        expected_answer=body.expected_answer,
        expected_doc_ids=body.expected_doc_ids or None,
        expected_sources=body.expected_sources or None,
    )
    return _entry_to_response(entry)


@router.put(
    "/dataset/entries/{entry_id}",
    response_model=QaDatasetEntryResponse,
    summary="Update QA dataset entry",
)
def put_dataset_entry(
    entry_id: int,
    body: QaDatasetEntryUpdateRequest,
    user_id: Annotated[str, Depends(get_request_user_id)],
    use_case: Annotated[Any, Depends(get_update_qa_dataset_entry_use_case)],
) -> QaDatasetEntryResponse:
    entry = use_case.execute(
        entry_id=entry_id,
        user_id=user_id,
        project_id=body.project_id,
        question=body.question,
        expected_answer=body.expected_answer,
        expected_doc_ids=body.expected_doc_ids or None,
        expected_sources=body.expected_sources or None,
    )
    return _entry_to_response(entry)


@router.delete(
    "/dataset/entries/{entry_id}",
    response_model=QaDatasetEntryDeleteResponse,
    summary="Delete QA dataset entry",
)
def delete_dataset_entry(
    entry_id: int,
    user_id: Annotated[str, Depends(get_request_user_id)],
    project_id: Annotated[str, Query(min_length=1)],
    use_case: Annotated[Any, Depends(get_delete_qa_dataset_entry_use_case)],
) -> QaDatasetEntryDeleteResponse:
    use_case.execute(entry_id=entry_id, user_id=user_id, project_id=project_id)
    return QaDatasetEntryDeleteResponse(deleted=True, entry_id=entry_id)


@router.post(
    "/dataset/generate",
    response_model=QaDatasetGenerateResponse,
    summary="Generate QA dataset rows via LLM",
    responses={
        502: {"description": "LLM failure"},
        400: {"description": "Invalid generation_mode or parameters"},
    },
)
def post_dataset_generate(
    body: QaDatasetGenerateRequest,
    user_id: Annotated[str, Depends(get_request_user_id)],
    use_case: Annotated[Any, Depends(get_generate_qa_dataset_use_case)],
) -> QaDatasetGenerateResponse:
    raw = use_case.execute(
        GenerateQaDatasetCommand(
            user_id=user_id,
            project_id=body.project_id,
            num_questions=body.num_questions,
            source_files=body.source_files,
            generation_mode=body.generation_mode,
        )
    )
    created = [_entry_to_response(e) for e in raw["created_entries"]]
    return QaDatasetGenerateResponse(
        generation_mode=raw["generation_mode"],
        deleted_existing_entries=int(raw["deleted_existing_entries"]),
        created_entries=created,
        skipped_duplicates=list(raw["skipped_duplicates"]),
        requested_questions=int(raw["requested_questions"]),
        raw_generated_count=int(raw["raw_generated_count"]),
    )


@router.get(
    "/retrieval/logs",
    response_model=RetrievalLogsResponse,
    summary="List query / retrieval logs",
)
def get_retrieval_logs(
    user_id: Annotated[str, Depends(get_request_user_id)],
    project_id: Annotated[str, Query(min_length=1)],
    use_case: Annotated[Any, Depends(get_list_retrieval_query_logs_use_case)],
    since: Annotated[str | None, Query(description="ISO-8601 lower bound (inclusive)")] = None,
    until: Annotated[str | None, Query(description="ISO-8601 upper bound (inclusive)")] = None,
    limit: Annotated[int | None, Query(ge=1, le=5000, description="Max rows")] = None,
) -> RetrievalLogsResponse:
    entries = use_case.execute(
        user_id=user_id,
        project_id=project_id,
        since_iso=since,
        until_iso=until,
        last_n=limit,
    )
    return RetrievalLogsResponse(entries=entries)


@router.get(
    "/export/benchmark",
    response_model=BenchmarkExportStubResponse,
    summary="Benchmark export (planned)",
)
def get_benchmark_export_stub() -> BenchmarkExportStubResponse:
    """Reserved for future POST that accepts a :class:`~src.domain.benchmark_result.BenchmarkResult` payload."""
    return BenchmarkExportStubResponse()


@router.post(
    "/export/benchmark",
    response_model=BenchmarkExportStubResponse,
    summary="Benchmark export (planned)",
)
def post_benchmark_export_stub() -> BenchmarkExportStubResponse:
    """Same contract as GET; full export will mirror ``BuildBenchmarkExportArtifactsUseCase``."""
    return BenchmarkExportStubResponse()
