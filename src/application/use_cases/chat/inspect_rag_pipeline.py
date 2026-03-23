from __future__ import annotations

from src.domain.pipeline_payloads import PipelineBuildResult
from src.domain.project import Project
from src.domain.retrieval_filters import RetrievalFilters
from src.domain.retrieval_settings_override_spec import RetrievalSettingsOverrideSpec
from src.domain.ports import RetrievalPort


class InspectRagPipelineUseCase:
    """
    Same pipeline build as the build use case but never writes query logs
    (inspector / debug flows).

    Delegates to :class:`~src.domain.ports.RetrievalPort` with ``emit_query_log=False``.
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
