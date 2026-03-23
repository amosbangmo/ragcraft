from __future__ import annotations

from domain.common.ports import RetrievalPort
from domain.projects.project import Project
from domain.rag.pipeline_payloads import PipelineBuildResult
from domain.rag.retrieval_filters import RetrievalFilters
from domain.rag.retrieval_settings_override_spec import RetrievalSettingsOverrideSpec


class InspectRagPipelineUseCase:
    """
    Same pipeline build as the build use case but never writes query logs
    (inspector / debug flows).

    Delegates to :class:`~domain.common.ports.RetrievalPort` with ``emit_query_log=False``.
    """

    def __init__(
        self,
        *,
        retrieval: RetrievalPort,
    ) -> None:
        self._retrieval = retrieval

    def execute(
        self,
        project: Project,
        question: str,
        chat_history: list[str] | None = None,
        *,
        filters: RetrievalFilters | None = None,
        retrieval_overrides: RetrievalSettingsOverrideSpec | None = None,
        enable_query_rewrite_override: bool | None = None,
        enable_hybrid_retrieval_override: bool | None = None,
    ) -> PipelineBuildResult | None:
        return self._retrieval.execute(
            project,
            question,
            chat_history,
            emit_query_log=False,
            filters=filters,
            retrieval_overrides=retrieval_overrides,
            enable_query_rewrite_override=enable_query_rewrite_override,
            enable_hybrid_retrieval_override=enable_hybrid_retrieval_override,
        )
