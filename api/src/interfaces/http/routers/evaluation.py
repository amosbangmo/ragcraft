"""
Evaluation, QA dataset, and retrieval log HTTP API.

Handlers call application use cases only; bodies use explicit Pydantic models.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from starlette.responses import Response

from application.dto.benchmark_export import BuildBenchmarkExportCommand
from application.dto.evaluation import (
    CreateQaDatasetEntryCommand,
    DeleteQaDatasetEntryCommand,
    GenerateQaDatasetCommand,
    ListQaDatasetEntriesQuery,
    ListRetrievalQueryLogsQuery,
    RunGoldQaDatasetEvaluationCommand,
    RunManualEvaluationCommand,
    UpdateQaDatasetEntryCommand,
)
from application.http.wire import (
    BenchmarkExportBundleWirePayload,
    BenchmarkRunWirePayload,
    QaDatasetGenerateWirePayload,
)
from application.orchestration.evaluation.build_benchmark_export_artifacts import (
    BuildBenchmarkExportArtifactsUseCase,
)
from application.use_cases.evaluation.create_qa_dataset_entry import CreateQaDatasetEntryUseCase
from application.use_cases.evaluation.delete_qa_dataset_entry import DeleteQaDatasetEntryUseCase
from application.use_cases.evaluation.generate_qa_dataset import GenerateQaDatasetUseCase
from application.use_cases.evaluation.list_qa_dataset_entries import ListQaDatasetEntriesUseCase
from application.use_cases.evaluation.list_retrieval_query_logs import ListRetrievalQueryLogsUseCase
from application.use_cases.evaluation.run_gold_qa_dataset_evaluation import (
    RunGoldQaDatasetEvaluationUseCase,
)
from application.use_cases.evaluation.run_manual_evaluation import RunManualEvaluationUseCase
from application.use_cases.evaluation.update_qa_dataset_entry import UpdateQaDatasetEntryUseCase
from domain.auth.authenticated_principal import AuthenticatedPrincipal
from domain.evaluation.benchmark_result import coerce_benchmark_result
from interfaces.http.dependencies import (
    get_authenticated_principal,
    get_build_benchmark_export_artifacts_use_case,
    get_create_qa_dataset_entry_use_case,
    get_delete_qa_dataset_entry_use_case,
    get_generate_qa_dataset_use_case,
    get_list_qa_dataset_entries_use_case,
    get_list_retrieval_query_logs_use_case,
    get_run_gold_qa_dataset_evaluation_use_case,
    get_run_manual_evaluation_use_case,
    get_update_qa_dataset_entry_use_case,
)
from interfaces.http.schemas.evaluation import (
    BenchmarkExportApiInfoResponse,
    BenchmarkExportRequest,
    BenchmarkExportResponse,
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
from interfaces.http.schemas.mappers import (
    manual_evaluation_result_to_response,
    qa_dataset_entry_to_response,
    retrieval_query_log_record_to_entry,
)

router = APIRouter(prefix="/evaluation", tags=["evaluation"])


def _content_disposition_attachment(filename: str) -> str:
    safe = filename.replace("\\", "\\\\").replace('"', '\\"')
    return f'attachment; filename="{safe}"'


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
    principal: Annotated[AuthenticatedPrincipal, Depends(get_authenticated_principal)],
    use_case: Annotated[RunManualEvaluationUseCase, Depends(get_run_manual_evaluation_use_case)],
) -> ManualEvaluationResponse:
    """
    Evaluate a single question with optional gold fields via the manual evaluation use case.

    Example::

        {"project_id": "demo", "question": "What is the refund policy?"}
    """
    result = use_case.execute(
        RunManualEvaluationCommand(
            user_id=principal.user_id,
            project_id=body.project_id,
            question=body.question,
            expected_answer=body.expected_answer,
            expected_doc_ids=body.expected_doc_ids or None,
            expected_sources=body.expected_sources or None,
            enable_query_rewrite_override=body.enable_query_rewrite_override,
            enable_hybrid_retrieval_override=body.enable_hybrid_retrieval_override,
        )
    )
    return manual_evaluation_result_to_response(result)


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
    principal: Annotated[AuthenticatedPrincipal, Depends(get_authenticated_principal)],
    use_case: Annotated[
        RunGoldQaDatasetEvaluationUseCase, Depends(get_run_gold_qa_dataset_evaluation_use_case)
    ],
) -> BenchmarkResultResponse:
    """Runs the full saved QA dataset for the project with fixed retrieval flags per row."""
    result = use_case.execute(
        RunGoldQaDatasetEvaluationCommand(
            user_id=principal.user_id,
            project_id=body.project_id,
            enable_query_rewrite=body.enable_query_rewrite,
            enable_hybrid_retrieval=body.enable_hybrid_retrieval,
        )
    )
    bench = BenchmarkRunWirePayload.from_benchmark_result(result)
    return BenchmarkResultResponse.model_validate(bench.as_json_dict())


@router.get(
    "/dataset/entries",
    response_model=QaDatasetEntryListResponse,
    summary="List QA dataset entries",
)
def get_dataset_entries(
    principal: Annotated[AuthenticatedPrincipal, Depends(get_authenticated_principal)],
    project_id: Annotated[str, Query(min_length=1)],
    use_case: Annotated[ListQaDatasetEntriesUseCase, Depends(get_list_qa_dataset_entries_use_case)],
) -> QaDatasetEntryListResponse:
    rows = use_case.execute(
        ListQaDatasetEntriesQuery(user_id=principal.user_id, project_id=project_id)
    )
    return QaDatasetEntryListResponse(entries=[qa_dataset_entry_to_response(e) for e in rows])


@router.post(
    "/dataset/entries",
    response_model=QaDatasetEntryResponse,
    status_code=201,
    summary="Create QA dataset entry",
)
def post_dataset_entry(
    body: QaDatasetEntryCreateRequest,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_authenticated_principal)],
    use_case: Annotated[CreateQaDatasetEntryUseCase, Depends(get_create_qa_dataset_entry_use_case)],
) -> QaDatasetEntryResponse:
    entry = use_case.execute(
        CreateQaDatasetEntryCommand(
            user_id=principal.user_id,
            project_id=body.project_id,
            question=body.question,
            expected_answer=body.expected_answer,
            expected_doc_ids=body.expected_doc_ids or None,
            expected_sources=body.expected_sources or None,
        )
    )
    return qa_dataset_entry_to_response(entry)


@router.put(
    "/dataset/entries/{entry_id}",
    response_model=QaDatasetEntryResponse,
    summary="Update QA dataset entry",
)
def put_dataset_entry(
    entry_id: int,
    body: QaDatasetEntryUpdateRequest,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_authenticated_principal)],
    use_case: Annotated[UpdateQaDatasetEntryUseCase, Depends(get_update_qa_dataset_entry_use_case)],
) -> QaDatasetEntryResponse:
    entry = use_case.execute(
        UpdateQaDatasetEntryCommand(
            entry_id=entry_id,
            user_id=principal.user_id,
            project_id=body.project_id,
            question=body.question,
            expected_answer=body.expected_answer,
            expected_doc_ids=body.expected_doc_ids or None,
            expected_sources=body.expected_sources or None,
        )
    )
    return qa_dataset_entry_to_response(entry)


@router.delete(
    "/dataset/entries/{entry_id}",
    response_model=QaDatasetEntryDeleteResponse,
    summary="Delete QA dataset entry",
)
def delete_dataset_entry(
    entry_id: int,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_authenticated_principal)],
    project_id: Annotated[str, Query(min_length=1)],
    use_case: Annotated[DeleteQaDatasetEntryUseCase, Depends(get_delete_qa_dataset_entry_use_case)],
) -> QaDatasetEntryDeleteResponse:
    use_case.execute(
        DeleteQaDatasetEntryCommand(
            entry_id=entry_id, user_id=principal.user_id, project_id=project_id
        )
    )
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
    principal: Annotated[AuthenticatedPrincipal, Depends(get_authenticated_principal)],
    use_case: Annotated[GenerateQaDatasetUseCase, Depends(get_generate_qa_dataset_use_case)],
) -> QaDatasetGenerateResponse:
    result = use_case.execute(
        GenerateQaDatasetCommand(
            user_id=principal.user_id,
            project_id=body.project_id,
            num_questions=body.num_questions,
            source_files=body.source_files,
            generation_mode=body.generation_mode,
        )
    )
    wire = QaDatasetGenerateWirePayload.from_result(result)
    return QaDatasetGenerateResponse.model_validate(wire.as_json_dict())


@router.get(
    "/retrieval/logs",
    response_model=RetrievalLogsResponse,
    summary="List query / retrieval logs",
)
def get_retrieval_logs(
    principal: Annotated[AuthenticatedPrincipal, Depends(get_authenticated_principal)],
    project_id: Annotated[str, Query(min_length=1)],
    use_case: Annotated[
        ListRetrievalQueryLogsUseCase, Depends(get_list_retrieval_query_logs_use_case)
    ],
    since: Annotated[str | None, Query(description="ISO-8601 lower bound (inclusive)")] = None,
    until: Annotated[str | None, Query(description="ISO-8601 upper bound (inclusive)")] = None,
    limit: Annotated[int | None, Query(ge=1, le=5000, description="Max rows")] = None,
) -> RetrievalLogsResponse:
    entries = use_case.execute(
        ListRetrievalQueryLogsQuery(
            user_id=principal.user_id,
            project_id=project_id,
            since_iso=since,
            until_iso=until,
            last_n=limit,
        )
    )
    return RetrievalLogsResponse(
        entries=[retrieval_query_log_record_to_entry(e) for e in entries],
    )


@router.get(
    "/export/benchmark",
    response_model=BenchmarkExportApiInfoResponse,
    summary="Benchmark export (discovery)",
)
def get_benchmark_export_info() -> BenchmarkExportApiInfoResponse:
    """Describes how to POST a benchmark payload for JSON/CSV/Markdown exports."""
    return BenchmarkExportApiInfoResponse()


@router.post(
    "/export/benchmark",
    response_model=None,
    summary="Build benchmark export files (JSON, CSV, Markdown)",
    responses={
        200: {
            "description": (
                "If export_format is 'all', JSON object with metadata and base64-encoded artifacts. "
                "If export_format is json|csv|markdown, raw file bytes with Content-Disposition attachment."
            ),
            "content": {
                "application/json": {},
                "text/csv": {},
                "text/markdown": {},
            },
        },
        422: {
            "description": "Invalid export_format, or body.result is not a coercible BenchmarkResult payload",
        },
    },
)
def post_benchmark_export(
    body: BenchmarkExportRequest,
    use_case: Annotated[
        BuildBenchmarkExportArtifactsUseCase, Depends(get_build_benchmark_export_artifacts_use_case)
    ],
):
    coerced = coerce_benchmark_result(body.result)
    if coerced is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": "invalid_benchmark_payload",
                "message": (
                    "result must be a BenchmarkResult-compatible object (e.g. the JSON from "
                    "POST /evaluation/dataset/run). Check summary/rows shape and row entry_id types."
                ),
            },
        )
    artifacts = use_case.execute(
        BuildBenchmarkExportCommand(
            project_id=body.project_id,
            result=coerced,
            enable_query_rewrite=body.enable_query_rewrite,
            enable_hybrid_retrieval=body.enable_hybrid_retrieval,
            generated_at=body.generated_at,
        )
    )
    fmt = body.export_format
    if fmt == "all":
        bundle = BenchmarkExportBundleWirePayload.from_artifacts(artifacts)
        return BenchmarkExportResponse.model_validate(bundle.as_json_dict())
    if fmt == "json":
        return Response(
            content=artifacts.json_bytes,
            media_type="application/json; charset=utf-8",
            headers={
                "Content-Disposition": _content_disposition_attachment(artifacts.json_filename)
            },
        )
    if fmt == "csv":
        return Response(
            content=artifacts.csv_bytes,
            media_type="text/csv; charset=utf-8",
            headers={
                "Content-Disposition": _content_disposition_attachment(artifacts.csv_filename)
            },
        )
    # fmt == "markdown"
    return Response(
        content=artifacts.markdown_bytes,
        media_type="text/markdown; charset=utf-8",
        headers={
            "Content-Disposition": _content_disposition_attachment(artifacts.markdown_filename)
        },
    )
