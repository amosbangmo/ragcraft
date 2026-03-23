"""
Chat and retrieval-debug HTTP API.

Handlers delegate to application use cases only; serialization lives under ``interfaces.http.schemas``.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from application.http.wire import (
    PipelineSnapshotWirePayload,
    PreviewSummaryRecallWirePayload,
    RagAnswerWirePayload,
    RetrievalComparisonWirePayload,
)
from application.use_cases.chat.ask_question import AskQuestionUseCase
from application.use_cases.chat.inspect_rag_pipeline import InspectRagPipelineUseCase
from application.use_cases.chat.preview_summary_recall import PreviewSummaryRecallUseCase
from application.use_cases.projects.resolve_project import ResolveProjectUseCase
from application.use_cases.retrieval.compare_retrieval_modes import CompareRetrievalModesUseCase
from domain.auth.authenticated_principal import AuthenticatedPrincipal
from domain.rag.retrieval_settings_override_spec import RetrievalSettingsOverrideSpec
from interfaces.http.dependencies import (
    get_ask_question_use_case,
    get_authenticated_principal,
    get_compare_retrieval_modes_use_case,
    get_inspect_pipeline_use_case,
    get_preview_summary_recall_use_case,
    get_resolve_project_use_case,
)
from interfaces.http.openapi_common import chat_route_responses
from interfaces.http.schemas.chat import (
    ChatAskRequest,
    ChatAskResponse,
    ChatPipelineRequestBase,
    PipelineInspectRequest,
    PipelineInspectResponse,
    PreviewSummaryRecallRequest,
    PreviewSummaryRecallResponse,
    RetrievalCompareRequest,
    RetrievalCompareResponse,
)

router = APIRouter(prefix="/chat", tags=["chat"])


def _retrieval_overrides_from_body(
    body: ChatPipelineRequestBase,
) -> RetrievalSettingsOverrideSpec | None:
    return RetrievalSettingsOverrideSpec.from_optional_mapping(body.retrieval_settings)


@router.post(
    "/ask",
    response_model=ChatAskResponse,
    summary="Ask a question (full RAG)",
    responses=chat_route_responses(),
)
def post_chat_ask(
    body: ChatAskRequest,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_authenticated_principal)],
    resolve_project: Annotated[ResolveProjectUseCase, Depends(get_resolve_project_use_case)],
    use_case: Annotated[AskQuestionUseCase, Depends(get_ask_question_use_case)],
) -> ChatAskResponse:
    """
    Run end-to-end RAG for one turn.

    Send ``Authorization: Bearer`` and a body with ``project_id`` and ``question`` (see schema example).
    """
    project = resolve_project.execute(principal.user_id, body.project_id)
    filters = body.filters.to_domain() if body.filters else None
    result = use_case.execute(
        project,
        body.question,
        body.chat_history,
        filters=filters,
        retrieval_overrides=_retrieval_overrides_from_body(body),
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
    responses=chat_route_responses(),
)
def post_pipeline_inspect(
    body: PipelineInspectRequest,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_authenticated_principal)],
    resolve_project: Annotated[ResolveProjectUseCase, Depends(get_resolve_project_use_case)],
    use_case: Annotated[InspectRagPipelineUseCase, Depends(get_inspect_pipeline_use_case)],
) -> PipelineInspectResponse:
    """
    Build the same pipeline as ``/chat/ask`` but stop before answer generation and do not write query logs.
    """
    project = resolve_project.execute(principal.user_id, body.project_id)
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
    responses=chat_route_responses(),
)
def post_preview_summary_recall(
    body: PreviewSummaryRecallRequest,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_authenticated_principal)],
    resolve_project: Annotated[ResolveProjectUseCase, Depends(get_resolve_project_use_case)],
    use_case: Annotated[PreviewSummaryRecallUseCase, Depends(get_preview_summary_recall_use_case)],
) -> PreviewSummaryRecallResponse:
    """
    Run vector (+ optional BM25) summary recall and return recalled chunks (preview stage only).
    """
    project = resolve_project.execute(principal.user_id, body.project_id)
    filters = body.filters.to_domain() if body.filters else None
    preview_dto = use_case.execute(
        project,
        body.question,
        body.chat_history,
        filters=filters,
        retrieval_overrides=_retrieval_overrides_from_body(body),
        enable_query_rewrite_override=body.enable_query_rewrite_override,
        enable_hybrid_retrieval_override=body.enable_hybrid_retrieval_override,
    )
    preview = PreviewSummaryRecallWirePayload.from_preview_dto(preview_dto).preview
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
    responses=chat_route_responses(),
)
def post_retrieval_compare(
    body: RetrievalCompareRequest,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_authenticated_principal)],
    use_case: Annotated[
        CompareRetrievalModesUseCase, Depends(get_compare_retrieval_modes_use_case)
    ],
) -> RetrievalCompareResponse:
    comparison = use_case.execute(
        user_id=principal.user_id,
        project_id=body.project_id,
        questions=list(body.questions),
        enable_query_rewrite=bool(body.enable_query_rewrite),
    )
    cmp_payload = RetrievalComparisonWirePayload.from_comparison_result(comparison)
    rd = cmp_payload.as_json_dict()
    return RetrievalCompareResponse(
        questions=rd["questions"],
        summary=rd["summary"],
        rows=rd["rows"],
    )
