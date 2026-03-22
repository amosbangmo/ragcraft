"""
Chat and retrieval-debug HTTP API.

Handlers delegate to application use cases only; serialization lives under ``apps.api.schemas``.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status

from apps.api.dependencies import (
    get_ask_question_use_case,
    get_inspect_pipeline_use_case,
    get_preview_summary_recall_use_case,
    get_project_service,
    get_retrieval_comparison_service,
    get_request_user_id,
)
from apps.api.schemas.chat import (
    ChatAskRequest,
    ChatAskResponse,
    PipelineInspectRequest,
    PipelineInspectResponse,
    PreviewSummaryRecallRequest,
    PreviewSummaryRecallResponse,
    RetrievalCompareRequest,
    RetrievalCompareResponse,
)
from src.application.http.wire import (
    PipelineSnapshotWirePayload,
    PreviewSummaryRecallWirePayload,
    RagAnswerWirePayload,
    RetrievalComparisonWirePayload,
)
from src.services.project_service import ProjectService

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post(
    "/ask",
    response_model=ChatAskResponse,
    summary="Ask a question (full RAG)",
    responses={
        502: {"description": "LLM or upstream model failure"},
        503: {"description": "Vector store, doc store, or infrastructure failure"},
    },
)
def post_chat_ask(
    body: ChatAskRequest,
    project_service: Annotated[ProjectService, Depends(get_project_service)],
    use_case: Annotated[Any, Depends(get_ask_question_use_case)],
) -> ChatAskResponse:
    """
    Run end-to-end RAG for one turn.

    Example body::

        {"user_id": "u1", "project_id": "demo", "question": "Summarize the main risks."}
    """
    project = project_service.get_project(body.user_id, body.project_id)
    filters = body.filters.to_domain() if body.filters else None
    result = use_case.execute(
        project,
        body.question,
        body.chat_history,
        filters=filters,
        retrieval_settings=body.retrieval_settings,
        enable_query_rewrite_override=body.enable_query_rewrite_override,
        enable_hybrid_retrieval_override=body.enable_hybrid_retrieval_override,
    )
    if result is None:
        return ChatAskResponse(
            status="no_pipeline",
            question=body.question,
            answer="",
            source_documents=[],
            raw_assets=[],
            prompt_sources=[],
            confidence=0.0,
            latency=None,
        )
    payload = RagAnswerWirePayload.from_rag_response(result)
    data = payload.as_json_dict()
    return ChatAskResponse(status="answered", **data)


@router.post(
    "/pipeline/inspect",
    response_model=PipelineInspectResponse,
    summary="Inspect full retrieval pipeline (no answer, no query log)",
    responses={
        502: {"description": "LLM or upstream model failure"},
        503: {"description": "Vector store, doc store, or infrastructure failure"},
    },
)
def post_pipeline_inspect(
    body: PipelineInspectRequest,
    project_service: Annotated[ProjectService, Depends(get_project_service)],
    use_case: Annotated[Any, Depends(get_inspect_pipeline_use_case)],
) -> PipelineInspectResponse:
    """
    Build the same pipeline as ``/chat/ask`` but stop before answer generation and do not write query logs.

    Example::

        {"user_id": "u1", "project_id": "demo", "question": "What tables mention revenue?"}
    """
    project = project_service.get_project(body.user_id, body.project_id)
    filters = body.filters.to_domain() if body.filters else None
    pipeline = use_case.execute(
        project,
        body.question,
        body.chat_history,
        filters=filters,
        retrieval_settings=body.retrieval_settings,
        enable_query_rewrite_override=body.enable_query_rewrite_override,
        enable_hybrid_retrieval_override=body.enable_hybrid_retrieval_override,
    )
    if pipeline is None:
        return PipelineInspectResponse(
            status="no_pipeline",
            question=body.question,
            pipeline=None,
        )
    snap = PipelineSnapshotWirePayload.from_build_result(pipeline)
    return PipelineInspectResponse(
        status="ok",
        question=body.question,
        pipeline=snap.pipeline,
    )


@router.post(
    "/pipeline/preview-summary-recall",
    response_model=PreviewSummaryRecallResponse,
    summary="Preview summary recall stage only",
    responses={
        502: {"description": "LLM or upstream model failure"},
        503: {"description": "Vector store, doc store, or infrastructure failure"},
    },
)
def post_preview_summary_recall(
    body: PreviewSummaryRecallRequest,
    project_service: Annotated[ProjectService, Depends(get_project_service)],
    use_case: Annotated[Any, Depends(get_preview_summary_recall_use_case)],
) -> PreviewSummaryRecallResponse:
    """
    Run vector (+ optional BM25) summary recall and return recalled chunks (Streamlit “preview” parity).

    Example::

        {"user_id": "u1", "project_id": "demo", "question": "Key dates in the contract?"}
    """
    project = project_service.get_project(body.user_id, body.project_id)
    filters = body.filters.to_domain() if body.filters else None
    raw = use_case.execute(
        project,
        body.question,
        body.chat_history,
        filters=filters,
        retrieval_settings=body.retrieval_settings,
        enable_query_rewrite_override=body.enable_query_rewrite_override,
        enable_hybrid_retrieval_override=body.enable_hybrid_retrieval_override,
    )
    preview = PreviewSummaryRecallWirePayload.from_preview_dict(raw).preview
    if preview is None:
        return PreviewSummaryRecallResponse(
            status="no_recall",
            question=body.question,
            preview=None,
        )
    return PreviewSummaryRecallResponse(
        status="ok",
        question=body.question,
        preview=preview,
    )


@router.post(
    "/retrieval/compare",
    response_model=RetrievalCompareResponse,
    summary="Compare FAISS-only vs hybrid retrieval across questions",
    responses={
        502: {"description": "LLM or upstream model failure"},
        503: {"description": "Vector store, doc store, or infrastructure failure"},
    },
)
def post_retrieval_compare(
    body: RetrievalCompareRequest,
    header_user_id: Annotated[str, Depends(get_request_user_id)],
    project_service: Annotated[Any, Depends(get_project_service)],
    comparison: Annotated[Any, Depends(get_retrieval_comparison_service)],
) -> RetrievalCompareResponse:
    if body.user_id.strip() != header_user_id.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Body user_id must match X-User-Id header.",
        )
    project = project_service.get_project(body.user_id, body.project_id)
    raw = comparison.compare(
        project=project,
        questions=list(body.questions),
        enable_query_rewrite=bool(body.enable_query_rewrite),
    )
    cmp_payload = RetrievalComparisonWirePayload.from_service_dict(raw)
    rd = cmp_payload.as_json_dict()
    return RetrievalCompareResponse(
        questions=rd["questions"],
        summary=rd["summary"],
        rows=rd["rows"],
    )
