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
from apps.api.schemas.serialization import (
    pipeline_build_result_to_api_dict,
    preview_summary_recall_to_api_dict,
    rag_response_to_api_dict,
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
    data = rag_response_to_api_dict(result)
    return ChatAskResponse(
        status="answered",
        question=data["question"],
        answer=data["answer"],
        source_documents=data["source_documents"],
        raw_assets=data["raw_assets"],
        prompt_sources=data["prompt_sources"],
        confidence=data["confidence"],
        latency=data["latency"],
    )


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
    return PipelineInspectResponse(
        status="ok",
        question=body.question,
        pipeline=pipeline_build_result_to_api_dict(pipeline),
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
    preview = preview_summary_recall_to_api_dict(raw)
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
    return RetrievalCompareResponse(
        questions=list(raw.get("questions") or []),
        summary=dict(raw.get("summary") or {}),
        rows=list(raw.get("rows") or []),
    )
